import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"build/block_776f726b6572"))
from botocore.exceptions import ClientError
spec=importlib.util.spec_from_file_location("worker",root/"build/block_776f726b6572/block_776f726b6572.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class WorkerTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(SOURCE_BUCKET="test-bucket",RESULTS_TABLE="results",QUEUE_ARN="arn:aws:sqs:ap-southeast-2:123456789012:queue",EXPECTED_ACCOUNT_ID="123456789012",MAX_INPUT_BYTES="100")
        self.s3=MagicMock();self.db=MagicMock();module._clients=(self.s3,self.db)
        self.s3.get_object.side_effect=lambda **kwargs:{"Body":io.BytesIO(b"one two three"),"ContentLength":13}
    def message(self,version="v1",bucket="test-bucket",message_id="record-1"):
        body={"Records":[{"eventSource":"aws:s3","eventName":"ObjectCreated:Put","s3":{"bucket":{"name":bucket},"object":{"key":"synthetic+text.txt","versionId":version}}}]}
        return {"messageId":message_id,"eventSource":"aws:sqs","eventSourceARN":os.environ["QUEUE_ARN"],"body":json.dumps(body)}
    def test_exact_version_and_conditional_result(self):
        self.assertEqual(module.handler({"Records":[self.message()]},None),{"batchItemFailures":[]})
        self.s3.get_object.assert_called_once_with(Bucket="test-bucket",Key="synthetic text.txt",VersionId="v1",ExpectedBucketOwner="123456789012")
        call=self.db.put_item.call_args.kwargs
        self.assertEqual(call["ConditionExpression"],"attribute_not_exists(objectId)")
        self.assertEqual(call["Item"]["wordCount"],{"N":"3"})
        self.assertEqual(call["Item"]["sourceVersion"],{"S":"v1"})
    def test_duplicate_is_success_without_overwriting(self):
        self.db.put_item.side_effect=[{},ClientError({"Error":{"Code":"ConditionalCheckFailedException"}},"PutItem")]
        event={"Records":[self.message()]}
        self.assertEqual(module.handler(event,None),{"batchItemFailures":[]})
        self.assertEqual(module.handler(event,None),{"batchItemFailures":[]})
        calls=self.db.put_item.call_args_list
        self.assertEqual(calls[0].kwargs["Item"]["objectId"],calls[1].kwargs["Item"]["objectId"])
        self.assertTrue(all(c.kwargs["ConditionExpression"]=="attribute_not_exists(objectId)" for c in calls))
    def test_new_version_has_distinct_result(self):
        module.handler({"Records":[self.message("v1"),self.message("v2",message_id="record-2")]},None)
        calls=self.db.put_item.call_args_list
        self.assertNotEqual(calls[0].kwargs["Item"]["objectId"],calls[1].kwargs["Item"]["objectId"])
    def test_partial_failure_and_redacted_diagnostics(self):
        bad=self.message(bucket="private-secret-title",message_id="bad")
        with self.assertLogs(module.logger,level="WARNING") as logs:
            result=module.handler({"Records":[bad,self.message(message_id="good")]},None)
        self.assertEqual(result,{"batchItemFailures":[{"itemIdentifier":"bad"}]})
        self.assertNotIn("private-secret-title"," ".join(logs.output))
        self.assertEqual(self.db.put_item.call_count,1)
    def test_oversized_document_closes_stream_and_does_not_write(self):
        stream=io.BytesIO(b"x"*101);self.s3.get_object.side_effect=None;self.s3.get_object.return_value={"Body":stream,"ContentLength":101}
        with self.assertLogs(module.logger,level="WARNING"):
            result=module.handler({"Records":[self.message()]},None)
        self.assertEqual(len(result["batchItemFailures"]),1);self.assertTrue(stream.closed);self.db.put_item.assert_not_called()
    def test_storage_test_event_and_retryable_database_failure(self):
        test=self.message();test["body"]=json.dumps({"Event":"s3:TestEvent"})
        self.assertEqual(module.handler({"Records":[test]},None),{"batchItemFailures":[]});self.s3.get_object.assert_not_called()
        self.db.put_item.side_effect=ClientError({"Error":{"Code":"ProvisionedThroughputExceededException"}},"PutItem")
        with self.assertLogs(module.logger,level="WARNING"):
            self.assertEqual(module.handler({"Records":[self.message()]},None),{"batchItemFailures":[{"itemIdentifier":"record-1"}]})
