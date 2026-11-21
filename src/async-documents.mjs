import {compileTextStatistics} from './text-statistics.mjs';
export const ASYNC_INTEGRATIONS=['s3-object-created','sqs-lambda','lambda-s3-read','lambda-dynamodb-write','sqs-redrive'];
export function asyncPipelinePlan(project,rows){
 const byId=new Map(rows.map(r=>[r.id,r])),nodes=new Map(project.nodes.map(n=>[n.id,n]));
 const edges=(source,type)=>project.edges.filter(e=>e.source===source&&e.integration===type);
 const typed=(id,implementation,service)=>{const n=nodes.get(id),r=byId.get(id);return n?.data.implementation===implementation&&r?.provider==='aws'&&!r.existing&&r.service===service;};
 const candidates=[];
 for(const worker of rows){
  if(!typed(worker.id,'async-word-count','AWS Lambda'))continue;
  const trigger=project.edges.filter(e=>e.target===worker.id&&e.integration==='sqs-lambda');
  const reads=edges(worker.id,'lambda-s3-read'),writes=edges(worker.id,'lambda-dynamodb-write');
  if(trigger.length!==1||reads.length!==1||writes.length!==1)continue;
  const queue=byId.get(trigger[0].source),bucket=byId.get(reads[0].target),table=byId.get(writes[0].target);
  if(!queue||!bucket?.foundation||!table||!typed(queue.id,'sqs-standard','Amazon SQS')||!typed(table.id,'word-count-results','Amazon DynamoDB'))continue;
  const notifications=edges(bucket.id,'s3-object-created').filter(e=>e.target===queue.id),redrives=edges(queue.id,'sqs-redrive');
  if(notifications.length!==1||redrives.length!==1)continue;
  const dlq=byId.get(redrives[0].target);
  if(!dlq||dlq.id===queue.id||!typed(dlq.id,'sqs-dead-letter','Amazon SQS'))continue;
  candidates.push({worker,queue,bucket,table,dlq,edges:[trigger[0],reads[0],writes[0],notifications[0],redrives[0]]});
 }
 // Shared ownership and overlapping S3 notification filters require a separate fan-out contract.
 const counts=new Map();for(const p of candidates)for(const r of [p.worker,p.queue,p.table,p.dlq,p.bucket])counts.set(r.id,(counts.get(r.id)||0)+1);
 const pipelines=candidates.filter(p=>[p.worker,p.queue,p.table,p.dlq,p.bucket].every(r=>counts.get(r.id)===1));
 return {pipelines,componentIds:pipelines.flatMap(p=>[p.worker.id,p.queue.id,p.table.id,p.dlq.id]),edgeIds:pipelines.flatMap(p=>p.edges.map(e=>e.id))};
}
export const ASYNC_HANDLER=`"""Version-specific, bounded, idempotent S3 text processing with partial batch failures."""
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
`;

export function compileAsyncDocuments(plan,environment='staging'){
 const resources={},variables={},outputs={},files={},preconditions=[],builds=[];
 const add=(type,name,body)=>(resources[type]||={})[name]={...body,depends_on:[...(body.depends_on||[]),'terraform_data.review_gate']};
 const ref=(type,row,field)=>`\u0024{${type}.${row.address}.${field}}`;
 const notifications=new Map();
 for(const pipeline of plan.asyncPlan.pipelines){
  const {worker,queue,bucket,table,dlq}=pipeline,n=worker.address,tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:n};
  const settings={memoryMb:256,functionTimeoutSeconds:30,concurrency:2,maxInputBytes:1000000,...worker.settings};
  const base=compileTextStatistics({...plan,rows:[{...worker,compute:true,settings}]},environment);
  for(const [type,items]of Object.entries(base.resources))resources[type]={...(resources[type]||{}),...items};
  Object.assign(variables,base.variables);Object.assign(outputs,base.outputs);Object.assign(files,base.files);
  files[`handlers/${n}.py`]=ASYNC_HANDLER;
  files[`app-tests/${n}_test.py`]=asyncHandlerTests(n);
  builds.push({address:n,sdk:true});
  const functionResource=resources.aws_lambda_function[n];
  functionResource.environment.variables={...functionResource.environment.variables,SOURCE_BUCKET:ref('aws_s3_bucket',bucket,'id'),RESULTS_TABLE:ref('aws_dynamodb_table',table,'name'),QUEUE_ARN:ref('aws_sqs_queue',queue,'arn'),EXPECTED_ACCOUNT_ID:'${var.aws_account_id}'};
  variables[`${n}_concurrency`].validation={condition:`\u0024{var.${n}_concurrency >= 2 && var.${n}_concurrency <= 1000 && floor(var.${n}_concurrency) == var.${n}_concurrency}`,error_message:'SQS event source maximum concurrency requires an integer from 2 to 1000.'};
  const window=`${n}_batch_window_seconds`,attempts=`${n}_max_receive_count`,alerts=`${n}_alert_topic_arns`;
  variables[window]={type:'number',default:0,validation:{condition:`\u0024{var.${window} >= 0 && var.${window} <= 300 && floor(var.${window}) == var.${window}}`,error_message:'Batch window must be an integer from 0 to 300 seconds.'}};
  variables[attempts]={type:'number',default:5,validation:{condition:`\u0024{var.${attempts} >= 1 && var.${attempts} <= 20 && floor(var.${attempts}) == var.${attempts}}`,error_message:'Choose 1–20 bounded delivery attempts.'}};
  variables[alerts]={type:'list(string)',default:[],description:'Reviewed existing standard SNS topics for DLQ alarms. Required for production; no notification destination is invented.',validation:{condition:`\u0024{alltrue([for arn in var.${alerts} : can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]{12}:[A-Za-z0-9_-]+$", arn))])}`,error_message:'Use existing standard SNS topic ARNs.'}};
  if(environment==='production')preconditions.push({condition:`\u0024{length(var.${alerts}) > 0}`,error_message:'Production queue processing requires a reviewed alarm notification topic.'});
  preconditions.push({condition:`\u0024{alltrue([for arn in var.${alerts} : startswith(arn, format("arn:aws:sns:%s:%s:", var.aws_region, var.aws_account_id))])}`,error_message:'Alarm topics must use the selected account and region.'});
  add('aws_sqs_queue',dlq.address,{name_prefix:`atmem-dlq-${dlq.address.slice(0,20)}-`,sqs_managed_sse_enabled:true,message_retention_seconds:1209600,tags});
  add('aws_sqs_queue',queue.address,{name_prefix:`atmem-work-${queue.address.slice(0,20)}-`,sqs_managed_sse_enabled:true,message_retention_seconds:345600,visibility_timeout_seconds:`\u0024{6 * var.${n}_timeout_seconds + var.${window}}`,redrive_policy:`\u0024{jsonencode({deadLetterTargetArn=aws_sqs_queue.${dlq.address}.arn,maxReceiveCount=var.${attempts}})}`,tags});
  add('aws_sqs_queue_policy',dlq.address,{queue_url:ref('aws_sqs_queue',dlq,'id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Deny',Principal:'*',Action:'sqs:*',Resource:ref('aws_sqs_queue',dlq,'arn'),Condition:{Bool:{'aws:SecureTransport':'false','aws:PrincipalIsAWSService':'false'}}}]})});
  add('aws_sqs_queue_redrive_allow_policy',dlq.address,{queue_url:ref('aws_sqs_queue',dlq,'id'),redrive_allow_policy:`\u0024{jsonencode({redrivePermission="byQueue",sourceQueueArns=[aws_sqs_queue.${queue.address}.arn]})}`});
  add('aws_sqs_queue_policy',queue.address,{queue_url:ref('aws_sqs_queue',queue,'id'),policy:JSON.stringify({Version:'2012-10-17',Statement:[{Effect:'Allow',Principal:{Service:'s3.amazonaws.com'},Action:'sqs:SendMessage',Resource:ref('aws_sqs_queue',queue,'arn'),Condition:{ArnEquals:{'aws:SourceArn':ref('aws_s3_bucket',bucket,'arn')},StringEquals:{'aws:SourceAccount':'${var.aws_account_id}'}}},{Effect:'Deny',Principal:'*',Action:'sqs:*',Resource:ref('aws_sqs_queue',queue,'arn'),Condition:{Bool:{'aws:SecureTransport':'false','aws:PrincipalIsAWSService':'false'}}}]})});
  add('aws_dynamodb_table',table.address,{name:`atmem-results-${ref('aws_iam_role',worker,'name')}`,billing_mode:'PAY_PER_REQUEST',hash_key:'objectId',attribute:[{name:'objectId',type:'S'}],point_in_time_recovery:{enabled:true},server_side_encryption:{enabled:true},deletion_protection_enabled:environment==='production',lifecycle:{prevent_destroy:environment==='production'},tags});
  const policy=JSON.parse(resources.aws_iam_role_policy[n].policy);
  policy.Statement.push({Effect:'Allow',Action:['s3:GetObjectVersion'],Resource:`${ref('aws_s3_bucket',bucket,'arn')}/*`},{Effect:'Allow',Action:['dynamodb:PutItem'],Resource:ref('aws_dynamodb_table',table,'arn')},{Effect:'Allow',Action:['sqs:ReceiveMessage','sqs:DeleteMessage','sqs:GetQueueAttributes'],Resource:ref('aws_sqs_queue',queue,'arn')});
  resources.aws_iam_role_policy[n].policy=JSON.stringify(policy);
  add('aws_lambda_event_source_mapping',n,{event_source_arn:ref('aws_sqs_queue',queue,'arn'),function_name:ref('aws_lambda_alias',worker,'arn'),batch_size:10,maximum_batching_window_in_seconds:`\u0024{var.${window}}`,function_response_types:['ReportBatchItemFailures'],scaling_config:{maximum_concurrency:`\u0024{var.${n}_concurrency}`},depends_on:[`aws_iam_role_policy.${n}`]});
  add('aws_cloudwatch_metric_alarm',dlq.address,{alarm_name:`atmem-dlq-${ref('aws_sqs_queue',dlq,'name')}`,namespace:'AWS/SQS',metric_name:'ApproximateNumberOfMessagesVisible',dimensions:{QueueName:ref('aws_sqs_queue',dlq,'name')},statistic:'Maximum',period:60,evaluation_periods:1,threshold:0,comparison_operator:'GreaterThanThreshold',treat_missing_data:'notBreaching',alarm_actions:`\u0024{var.${alerts}}`,tags});
  const notification=notifications.get(bucket.address)||{bucket,queue:[],policies:[]};notification.queue.push({id:n,queue_arn:ref('aws_sqs_queue',queue,'arn'),events:['s3:ObjectCreated:*']});notification.policies.push(`aws_sqs_queue_policy.${queue.address}`);notifications.set(bucket.address,notification);
  outputs[`${n}_pipeline`]={value:{source_bucket:ref('aws_s3_bucket',bucket,'id'),queue_url:ref('aws_sqs_queue',queue,'id'),dead_letter_queue_url:ref('aws_sqs_queue',dlq,'id'),results_table:ref('aws_dynamodb_table',table,'name')}};
 }
 for(const [address,entry]of notifications)add('aws_s3_bucket_notification',address,{bucket:ref('aws_s3_bucket',entry.bucket,'id'),queue:entry.queue,depends_on:[...entry.policies,`aws_s3_bucket_versioning.${address}`]});
 return {resources,variables,outputs,files,preconditions,builds};
}

function asyncHandlerTests(address){
 return `import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"build/${address}"))
from botocore.exceptions import ClientError
spec=importlib.util.spec_from_file_location("worker",root/"build/${address}/${address}.py")
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
`;
}
