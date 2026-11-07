import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"build/block_73756d6d6172792d666e"))
from botocore.exceptions import ClientError
spec=importlib.util.spec_from_file_location("summary",root/"build/block_73756d6d6172792d666e/block_73756d6d6172792d666e.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class SummaryTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(MODEL_ARN="arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-micro-v1:0",MAX_INPUT_BYTES="100",MAX_OUTPUT_TOKENS="128")
        self.client=MagicMock();module._client=self.client
        self.client.converse.return_value={"output":{"message":{"content":[{"text":"Synthetic summary"}]}},"stopReason":"end_turn"}
    def test_bounded_request_and_summary(self):
        self.assertEqual(module.handler({"text":"Synthetic input"},None),{"summary":"Synthetic summary","truncated":False})
        kwargs=self.client.converse.call_args.kwargs
        self.assertEqual(kwargs["modelId"],os.environ["MODEL_ARN"])
        self.assertEqual(kwargs["inferenceConfig"],{"maxTokens":128,"temperature":0})
    def test_rejects_bad_input_before_model_call(self):
        for event in [{},{"text":""},{"text":"x"*101},{"text":12},{"text":"ok","modelId":"other"}]:
            with self.assertRaises(ValueError):module.handler(event,None)
        self.client.converse.assert_not_called()
    def test_denial_and_throttle_are_sanitized(self):
        for code,retryable in [("AccessDeniedException",False),("ThrottlingException",True)]:
            self.client.converse.side_effect=ClientError({"Error":{"Code":code,"Message":"PRIVATE DOCUMENT"}},"Converse")
            with self.assertLogs(module.logger,level="WARNING") as logs:result=module.handler({"text":"PRIVATE DOCUMENT"},None)
            self.assertEqual(result,{"error":"model_unavailable","retryable":retryable})
            self.assertNotIn("PRIVATE DOCUMENT"," ".join(logs.output))
    def test_truncation_and_empty_output(self):
        self.client.converse.return_value["stopReason"]="max_tokens"
        self.assertTrue(module.handler({"text":"data"},None)["truncated"])
        self.client.converse.return_value={}
        self.assertEqual(module.handler({"text":"data"},None)["error"],"empty_model_response")
