"""Version-specific, bounded, idempotent S3 text processing with partial batch failures."""
import hashlib
import json
import logging
import os
from urllib.parse import unquote_plus
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

_clients = None
logger = logging.getLogger(__name__)

def clients():
    global _clients
    if _clients is None:
        config=Config(connect_timeout=3,read_timeout=5,retries={"max_attempts":2})
        _clients=(boto3.client("s3",config=config),boto3.client("dynamodb",config=config))
    return _clients

def process(body):
    if not isinstance(body,dict):raise ValueError("Invalid storage notification")
    if body.get("Event")=="s3:TestEvent":return
    records=body.get("Records")
    if not isinstance(records,list) or not 1 <= len(records) <= 10:raise ValueError("Invalid notification batch")
    s3,db=clients()
    for record in records:
        if record.get("eventSource")!="aws:s3" or not str(record.get("eventName","")).startswith("ObjectCreated:"):raise ValueError("Unsupported storage event")
        bucket=record["s3"]["bucket"]["name"]
        key=unquote_plus(record["s3"]["object"]["key"])
        version=record["s3"]["object"].get("versionId")
        if bucket!=os.environ["SOURCE_BUCKET"] or not isinstance(version,str) or not version or version=="null":raise ValueError("Wrong bucket or missing exact object version")
        limit=int(os.environ["MAX_INPUT_BYTES"])
        result=s3.get_object(Bucket=bucket,Key=key,VersionId=version,ExpectedBucketOwner=os.environ["EXPECTED_ACCOUNT_ID"])
        stream=result["Body"]
        try:
            if result.get("ContentLength",0)>limit:raise ValueError("Document too large")
            data=stream.read(limit+1)
        finally:stream.close()
        if len(data)>limit:raise ValueError("Document too large")
        text=data.decode("utf-8")
        object_id=hashlib.sha256(json.dumps([bucket,key,version],ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
        item={"objectId":{"S":object_id},"wordCount":{"N":str(len(text.split()))},"characterCount":{"N":str(len(text))},"sourceVersion":{"S":version},"contentSha256":{"S":hashlib.sha256(data).hexdigest()},"processorVersion":{"S":"1"}}
        try:db.put_item(TableName=os.environ["RESULTS_TABLE"],Item=item,ConditionExpression="attribute_not_exists(objectId)")
        except ClientError as error:
            if error.response.get("Error",{}).get("Code")!="ConditionalCheckFailedException":raise

def handler(event,context):
    records=event.get("Records") if isinstance(event,dict) else None
    if not isinstance(records,list) or len(records)>10:raise ValueError("Invalid queue batch")
    failures=[]
    for record in records:
        message_id=record.get("messageId")
        if not isinstance(message_id,str) or not message_id:raise ValueError("Queue message ID is missing")
        try:
            if record.get("eventSource")!="aws:sqs" or record.get("eventSourceARN")!=os.environ["QUEUE_ARN"]:raise ValueError("Wrong event source")
            process(json.loads(record["body"]))
        except Exception as error:
            logger.warning(json.dumps({"event":"record_failed","errorType":type(error).__name__}))
            failures.append({"itemIdentifier":message_id})
    return {"batchItemFailures":failures}
