"""Stateful AWS emulation worker. Only server-generated files enter this process.

No Terraform apply, real IAM authorizer or managed-model inference is performed.
The OS/container boundary remains a hosting requirement, not a Python guarantee.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
from contextlib import contextmanager

ACCOUNT='123456789012'
REGION='ap-southeast-2'
LIMITATIONS=[
    'Terraform apply and real AWS account prerequisites are not emulated; run provider checks separately.',
    'IAM enforcement, API Gateway routing/signatures, Cognito sign-in/MFA and CloudFront delivery remain unverified.',
    'Generated Python handlers execute on this host, not the AWS Lambda ARM64 runtime; event polling is driven by the harness.',
    'Bedrock responses and authenticated request envelopes are deterministic fixtures, not model-quality or authentication evidence.',
    'Quotas, billing, latency, service outages and native SharePoint/Confluence APIs require separate qualification.',
]

class EmulationFailure(Exception):
    pass


def require(condition,message):
    if not condition:raise EmulationFailure(message)


@contextmanager
def deny_network():
    """Fail closed if an SDK call escapes Moto. No passthrough services or URLs."""
    old_connect,old_connect_ex,old_dns=socket.socket.connect,socket.socket.connect_ex,socket.getaddrinfo
    def denied(*args,**kwargs):raise EmulationFailure('Unexpected network access blocked')
    socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.getaddrinfo=denied
    try:yield
    finally:socket.socket.connect=old_connect;socket.socket.connect_ex=old_connect_ex;socket.getaddrinfo=old_dns


def load_module(name,file):
    spec=importlib.util.spec_from_file_location(name,file);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


class ScriptedBedrock:
    """An explicit model fixture with real SDK request-shape validation."""
    def __init__(self,mode='rag'):
        import botocore.session
        self.model=botocore.session.get_session().get_service_model('bedrock-runtime')
        self.mode=mode;self.calls=[];self.failure=None;self.after=None;self.result={}
    def converse(self,**kwargs):
        from botocore.validate import validate_parameters
        from botocore.exceptions import ClientError
        validate_parameters(kwargs,self.model.operation_model('Converse').input_shape)
        self.calls.append(copy.deepcopy(kwargs))
        if self.failure:raise ClientError({'Error':{'Code':self.failure,'Message':'Synthetic fault'}},'Converse')
        if self.mode=='rag':
            payload=json.loads(kwargs['messages'][0]['content'][0]['text']);evidence=payload['evidence']
            text=json.dumps({'answer':evidence[0]['text'],'citations':[evidence[0]['id']]})
        elif self.mode=='structured':text=json.dumps(self.result)
        else:text='Synthetic fixture summary.'
        if self.after:self.after()
        return {'output':{'message':{'role':'assistant','content':[{'text':text}]}},'stopReason':'end_turn'}


class Worker:
    def __init__(self,folder):
        self.root=Path(folder);self.tf=json.loads((self.root/'main.tf.json').read_text())
        self.plan=json.loads((self.root/'resource-schedule.json').read_text())
        self.resources=self.tf.get('resource',{});self.refs={};self.checks=[];self.modules={};self.capabilities=[]
        self.variables={k:v['default'] for k,v in self.tf.get('variable',{}).items() if 'default' in v}
        self.variables.update(aws_account_id=ACCOUNT,aws_region=REGION)
        for k in self.tf.get('variable',{}):
            if k.endswith('_model_id'):self.variables[k]='emulated-model'
        self.report={'version':1,'kind':'local-aws-emulation','backend':'moto','status':'running','cloudOperations':False,'terraformApply':'not_run','modelMode':'scripted-fixture','checks':self.checks,'capabilities':self.capabilities,'limitations':LIMITATIONS,'cleanup':'not_run'}
    def check(self,name,fn,evidence='stateful-emulation'):
        try:
            fn();self.checks.append({'name':name,'passed':True,'evidence':evidence})
        except Exception as exc:
            self.checks.append({'name':name,'passed':False,'evidence':evidence,'errorType':type(exc).__name__,'message':str(exc)[:400] if isinstance(exc,EmulationFailure) else 'Generated code or emulator API failed; inspect local diagnostic evidence.'})
            raise
    def resolve(self,value):
        if not isinstance(value,str):return value
        def replace(match):
            expr=match.group(1)
            if expr.startswith('tostring(') and expr.endswith(')'):expr=expr[9:-1]
            if expr.startswith('var.') and expr[4:] in self.variables:return str(self.variables[expr[4:]])
            if expr in self.refs:return str(self.refs[expr])
            raise EmulationFailure('Unsupported generated reference in emulation adapter: '+expr)
        return re.sub(r'\$\{([^{}]+)\}',replace,value)
    def name(self,address):return 'atmem-emu-'+hashlib.sha256(address.encode()).hexdigest()[:16]
    def setup(self):
        import boto3
        self.s3=boto3.client('s3',region_name=REGION);self.sqs=boto3.client('sqs',region_name=REGION);self.db=boto3.client('dynamodb',region_name=REGION)
        for address in self.resources.get('aws_s3_bucket',{}):
            name=self.name(address);self.s3.create_bucket(Bucket=name,CreateBucketConfiguration={'LocationConstraint':REGION})
            self.refs.update({f'aws_s3_bucket.{address}.id':name,f'aws_s3_bucket.{address}.arn':'arn:aws:s3:::'+name})
            if address in self.resources.get('aws_s3_bucket_versioning',{}):self.s3.put_bucket_versioning(Bucket=name,VersioningConfiguration={'Status':self.resources['aws_s3_bucket_versioning'][address]['versioning_configuration']['status']})
            if address in self.resources.get('aws_s3_bucket_server_side_encryption_configuration',{}):self.s3.put_bucket_encryption(Bucket=name,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':self.resources['aws_s3_bucket_server_side_encryption_configuration'][address]['rule']['apply_server_side_encryption_by_default']['sse_algorithm']}}]})
            if address in self.resources.get('aws_s3_bucket_public_access_block',{}):self.s3.put_public_access_block(Bucket=name,PublicAccessBlockConfiguration={camel:self.resources['aws_s3_bucket_public_access_block'][address][snake] for camel,snake in [('BlockPublicAcls','block_public_acls'),('IgnorePublicAcls','ignore_public_acls'),('BlockPublicPolicy','block_public_policy'),('RestrictPublicBuckets','restrict_public_buckets')]})
        for address,body in self.resources.get('aws_dynamodb_table',{}).items():
            name=self.name(address)
            self.db.create_table(TableName=name,KeySchema=[{'AttributeName':body['hash_key'],'KeyType':'HASH'}],AttributeDefinitions=[{'AttributeName':a['name'],'AttributeType':a['type']} for a in body['attribute']],BillingMode='PAY_PER_REQUEST')
            self.refs[f'aws_dynamodb_table.{address}.name']=name
        for address in self.resources.get('aws_sqs_queue',{}):
            url=self.sqs.create_queue(QueueName=self.name(address))['QueueUrl'];arn=self.sqs.get_queue_attributes(QueueUrl=url,AttributeNames=['QueueArn'])['Attributes']['QueueArn']
            self.refs.update({f'aws_sqs_queue.{address}.url':url,f'aws_sqs_queue.{address}.arn':arn})
        for type_,field in [('aws_apigatewayv2_api','id'),('aws_cognito_user_pool','id'),('aws_cognito_user_pool_client','id')]:
            for address in self.resources.get(type_,{}):self.refs[f'{type_}.{address}.{field}']=self.name(address)
        self.capabilities.extend([{'service':name,'mode':'stateful-service-API'} for name,present in [('S3',self.resources.get('aws_s3_bucket')),('SQS',self.resources.get('aws_sqs_queue')),('DynamoDB',self.resources.get('aws_dynamodb_table'))] if present])
    def module(self,address):
        if address not in self.modules:
            dependency=self.root/'handlers'/address
            if dependency.exists():sys.path.insert(0,str(dependency))
            self.modules[address]=load_module('emulated_'+address,self.root/'handlers'/f'{address}.py')
        fn=self.resources['aws_lambda_function'][address]
        for k in ['SOURCE_BUCKET','RESULTS_TABLE','QUEUE_ARN','EXPECTED_ACCOUNT_ID','EXPECTED_API_ID','CATALOG_TABLE','COGNITO_ISSUER','COGNITO_CLIENT_ID','MAX_OUTPUT_TOKENS']:os.environ.pop(k,None)
        os.environ.update({k:str(self.resolve(v)) for k,v in fn['environment']['variables'].items()})
        require(0<int(os.environ['MAX_INPUT_BYTES'])<=1_000_000,'Input size exceeds bounded emulator support')
        return self.modules[address]
    def storage(self,address):
        name=self.refs[f'aws_s3_bucket.{address}.id'];key='synthetic.txt'
        first=self.s3.put_object(Bucket=name,Key=key,Body=b'first')['VersionId'];second=self.s3.put_object(Bucket=name,Key=key,Body=b'second')['VersionId']
        require(first!=second,'Object versions must differ')
        require(self.s3.get_object(Bucket=name,Key=key,VersionId=first)['Body'].read()==b'first','Prior version recovery failed')
        require(self.s3.get_object(Bucket=name,Key=key)['Body'].read()==b'second','Latest version read failed')
        for version in [first,second]:self.s3.delete_object(Bucket=name,Key=key,VersionId=version)
    def statistics(self,address):
        module=self.module(address)
        result=module.handler({'text':'Hello Sydney\nAWS'},None)
        require(result.get('wordCount')==3 and result.get('characterCount')==16,'Generated counts do not match exact input')
        result=module.handler({'text':'Hi 👋'},None);require(result.get('characterCount')==4,'Unicode code-point count failed')
        for event in [{'text':123},{'text':'x'*(int(os.environ['MAX_INPUT_BYTES'])+1)}]:
            try:module.handler(event,None)
            except ValueError:continue
            raise EmulationFailure('Invalid input was accepted')
    def asynchronous(self,pipeline):
        address=pipeline['worker']['address'];module=self.module(address);module._clients=None
        bucket=os.environ['SOURCE_BUCKET'];table=os.environ['RESULTS_TABLE'];queue=self.refs[f"aws_sqs_queue.{pipeline['queue']['address']}.url"];dlq=self.refs[f"aws_sqs_queue.{pipeline['dlq']['address']}.url"]
        count=int(self.variables[address+'_max_receive_count']);require(1<=count<=20,'Retry count exceeds bounded emulator support')
        redrive=self.resources['aws_sqs_queue'][pipeline['queue']['address']].get('redrive_policy','')
        require(f"deadLetterTargetArn=aws_sqs_queue.{pipeline['dlq']['address']}.arn" in redrive and f'maxReceiveCount=var.{address}_max_receive_count' in redrive,'Generated redrive policy does not match the typed pipeline')
        self.sqs.set_queue_attributes(QueueUrl=queue,Attributes={'RedrivePolicy':json.dumps({'deadLetterTargetArn':self.refs[f"aws_sqs_queue.{pipeline['dlq']['address']}.arn"],'maxReceiveCount':count})})
        notification=self.resources.get('aws_s3_bucket_notification',{}).get(pipeline['bucket']['address'])
        require(notification is not None,'Generated S3 notification configuration is missing')
        mappings=self.resources.get('aws_lambda_event_source_mapping',{})
        require(any(self.resolve(m['event_source_arn'])==os.environ['QUEUE_ARN'] and m.get('function_response_types')==['ReportBatchItemFailures'] for m in mappings.values()),'Generated event source or partial-batch failure contract is missing')
        self.s3.put_bucket_notification_configuration(Bucket=bucket,NotificationConfiguration={'QueueConfigurations':[{'Id':q['id'],'QueueArn':self.resolve(q['queue_arn']),'Events':q['events']} for q in notification['queue']]})
        version=self.s3.put_object(Bucket=bucket,Key='sample.txt',Body=b'Hello Sydney\nAWS')['VersionId']
        bodies=[]
        def consume():
            messages=self.sqs.receive_message(QueueUrl=queue,MaxNumberOfMessages=10,WaitTimeSeconds=0).get('Messages',[])
            for msg in messages:
                try:body=json.loads(msg['Body'])
                except json.JSONDecodeError:body={}
                record={'messageId':msg['MessageId'],'eventSource':'aws:sqs','eventSourceARN':os.environ['QUEUE_ARN'],'body':msg['Body']}
                result=module.handler({'Records':[record]},None)
                if result['batchItemFailures']:self.sqs.change_message_visibility(QueueUrl=queue,ReceiptHandle=msg['ReceiptHandle'],VisibilityTimeout=0)
                else:
                    self.sqs.delete_message(QueueUrl=queue,ReceiptHandle=msg['ReceiptHandle'])
                    if body.get('Records'):bodies.append(msg['Body'])
            return messages
        consume();items=self.db.scan(TableName=table)['Items'];require(len(items)==1 and items[0]['wordCount']['N']=='3','S3 notification → SQS → generated worker → DynamoDB did not produce the expected result')
        require(items[0]['sourceVersion']['S']==version,'Exact S3 version was not processed')
        require(bool(bodies),'No actual emulated S3 notification was delivered')
        self.sqs.send_message(QueueUrl=queue,MessageBody=bodies[0]);consume();require(len(bodies)==2 and self.db.scan(TableName=table)['Count']==1,'Duplicate delivery was not successfully acknowledged without duplicate results')
        self.sqs.send_message(QueueUrl=queue,MessageBody='invalid json')
        for _ in range(count+2):consume()
        poison=self.sqs.receive_message(QueueUrl=dlq,MaxNumberOfMessages=10).get('Messages',[]);require(len(poison)==1,'Poison message did not reach emulated DLQ')
        self.sqs.send_message(QueueUrl=queue,MessageBody=bodies[0]);consume();require(len(bodies)==3 and self.db.scan(TableName=table)['Count']==1,'Valid replay after poison recovery failed')
        self.capabilities.append({'service':'S3 → SQS → worker','mode':'Moto notification and redrive; harness polls/invokes/acks; visibility advanced explicitly'})
    def summary(self,address):
        module=self.module(address);model=ScriptedBedrock('summary');module._client=model
        require(module.handler({'text':'Synthetic Sydney office.'},None).get('summary')=='Synthetic fixture summary.','Summary response contract failed')
        require(model.calls[-1]['inferenceConfig']['maxTokens']==int(os.environ['MAX_OUTPUT_TOKENS']),'Generated output token bound not used')
        for code,retryable in [('AccessDeniedException',False),('ThrottlingException',True)]:
            model.failure=code;require(module.handler({'text':'Synthetic text.'},None)=={'error':'model_unavailable','retryable':retryable},'Model fault classification failed')
        model.failure=None
        before=len(model.calls)
        try:module.handler({'text':'x'*(int(os.environ['MAX_INPUT_BYTES'])+1)},None)
        except ValueError:pass
        else:raise EmulationFailure('Oversized model input accepted')
        require(len(model.calls)==before,'Oversized input reached model boundary')
    def structured(self,address):
        from botocore.validate import validate_parameters
        import botocore.session
        class PolicyFixture:
            mode='none';logging={};failure=False
            def get_account_data_retention(self):
                if self.failure:raise RuntimeError('Synthetic read denial')
                return {'mode':self.mode}
            def get_model_invocation_logging_configuration(self):return {'loggingConfig':self.logging}
        class IdentityFixture:
            enabled=True
            def admin_get_user(self,**kwargs):
                shape=botocore.session.get_session().get_service_model('cognito-idp').operation_model('AdminGetUser').input_shape
                validate_parameters(kwargs,shape)
                return {'Enabled':self.enabled,'UserStatus':'CONFIRMED','UserAttributes':[{'Name':'sub','Value':'fixture-subject'}]}
        module=self.module(address);model=ScriptedBedrock('structured');policy=PolicyFixture();identity=IdentityFixture()
        module._client=model;module._retention=policy;module._identity=identity
        model.result={f['name']:False if f['type']=='boolean' else 0 if f['type']=='number' else f.get('values',['x'])[0] for f in module.OUTPUT_FIELDS}
        valid=copy.deepcopy(model.result)
        http='COGNITO_USER_POOL_ID' in self.resources['aws_lambda_function'][address]['environment']['variables']
        def event(text):
            if not http:return {'text':text}
            return {'version':'2.0','requestContext':{'apiId':os.environ['EXPECTED_API_ID'],'routeKey':'POST /api/ask','authorizer':{'jwt':{'claims':{'iss':os.environ['COGNITO_ISSUER'],'client_id':os.environ['COGNITO_CLIENT_ID'],'token_use':'access','scope':'atmem/ask','sub':'fixture-subject','username':'fixture-user'}}}},'isBase64Encoded':False,'body':json.dumps({'text':text})}
        def invoke(text):
            result=module.handler(event(text),None)
            return (result['statusCode'],json.loads(result['body'])) if http else (200,result)
        status,result=invoke('Synthetic bounded request')
        require(status==200 and result=={'result':valid,'requiresHumanReview':True},'Structured result failed its declared schema or review contract')
        model.result={'unexpected':'not a declared output'}
        require(invoke('Synthetic input')[1].get('error')=='invalid_model_output','Invalid structured model output was accepted')
        model.result=valid
        before=len(model.calls)
        for mode in ['default','inherit','aws_review',None]:
            policy.mode=mode;require(invoke('Synthetic input')[1].get('error')=='data_retention_unverified','Unverified model retention reached inference')
        policy.mode='none';policy.logging={'textDataDeliveryEnabled':True}
        require(invoke('Synthetic input')[1].get('error')=='data_retention_unverified','Enabled prompt logging reached inference')
        policy.logging={};policy.failure=True
        require(invoke('Synthetic input')[1].get('error')=='data_retention_unverified','Unavailable retention policy reached inference')
        require(len(model.calls)==before,'A failed data policy check sent input to the model')
        policy.failure=False
        if http:
            require(module.handler({},None)['statusCode']==403,'Unverified direct invocation accepted')
            identity.enabled=False;require(invoke('Synthetic input')[0]==403,'Disabled user accepted')
            require(len(model.calls)==before,'Disabled user reached inference')
            identity.enabled=True;model.after=lambda:setattr(identity,'enabled',False)
            require(invoke('Synthetic input')[0]==403,'Revoked user received an in-flight result')
            model.after=None;identity.enabled=True
        before=len(model.calls)
        try:status,result=invoke('x'*(int(os.environ['MAX_INPUT_BYTES'])+1))
        except ValueError:status=400
        require(status==400,'Oversized structured input accepted')
        require(len(model.calls)==before,'Oversized input reached inference')
        self.capabilities.append({'service':'Structured operation','mode':'emitted Python execution, SDK-validated Converse request, scripted model/identity/policy state; real account settings, JWT verification and model accuracy unverified'})

    def rag(self,address):
        from boto3.dynamodb.types import TypeSerializer
        from botocore.exceptions import ClientError
        module=self.module(address);model=ScriptedBedrock();module._clients=(self.db,model);table=os.environ['CATALOG_TABLE']
        admin=load_module('catalog_admin',self.root/'manage-catalog.py');serializer=TypeSerializer()
        def put(item):self.db.put_item(TableName=table,Item={k:serializer.serialize(v) for k,v in item.items()})
        principal='AROA1234567890123456'
        identity={'recordId':'IDENTITY#'+principal,'enabled':True,'subject':'alice','employeeRegion':'AU'};put(identity)
        event={'version':'2.0','requestContext':{'accountId':ACCOUNT,'apiId':os.environ['EXPECTED_API_ID'],'routeKey':'POST /ask','authorizer':{'iam':{'accountId':ACCOUNT,'callerId':principal+':test','userArn':f'arn:aws:sts::{ACCOUNT}:assumed-role/TestRole/test'}}},'body':json.dumps({'question':'retention policy'})}
        document={'id':'retention','title':'Retention policy','text':'Records retained for 30 days.','allowedSubjects':['alice'],'allowedRegions':['AU']}
        first=admin.put_document(self.db,table,document)
        admin.put_document(self.db,table,{**document,'id':'restricted','title':'RESTRICTED-MARKER','text':'Restricted retention policy SECRET-MARKER.','allowedSubjects':['bob']})
        admin.put_document(self.db,table,{**document,'id':'wrong-region','title':'WRONG-REGION-MARKER','allowedRegions':['US']})
        result=module.handler(event,None);body=json.loads(result['body']);require(result['statusCode']==200 and body['citations'][0]['id']=='retention','Cited retrieval failed')
        require('SECRET-MARKER' not in json.dumps(model.calls) and 'WRONG-REGION-MARKER' not in json.dumps(model.calls),'Unauthorized evidence reached the model boundary')
        updated=admin.put_document(self.db,table,{**document,'text':'Records retained for 45 days.'},first['revision'])
        require('45 days' in module.handler(event,None)['body'],'Updated document not reflected')
        try:admin.put_document(self.db,table,document,first['revision'])
        except ClientError as error:require(error.response['Error']['Code']=='ConditionalCheckFailedException','Unexpected service error during stale-revision test')
        else:raise EmulationFailure('Stale document revision overwrote current data')
        # Fault injection changes actual emulated state during the generated model call.
        model.after=lambda:put({**identity,'enabled':False})
        require(module.handler(event,None)['statusCode']==403,'Mid-generation identity revocation did not suppress delivery')
        model.after=None;put(identity)
        forged={**event,'body':json.dumps({'question':'retention','subject':'bob'})};require(module.handler(forged,None)['statusCode']==400,'Body identity spoof accepted')
        admin.delete_document(self.db,table,'retention',updated['revision']);before=len(model.calls)
        body=json.loads(module.handler(event,None)['body']);require(body.get('abstained') is True and len(model.calls)==before,'Deleted/restricted evidence caused model inference')
        put({**identity,'enabled':False});require(module.handler(event,None)['statusCode']==403,'Disabled identity accepted')
        put(identity)
        if 'COGNITO_ISSUER' in os.environ:
            subject='11111111-1111-1111-1111-111111111111';put({**identity,'recordId':'IDENTITY#COGNITO#'+subject})
            browser=copy.deepcopy(event);browser['requestContext']['routeKey']='POST /api/ask';browser['requestContext']['authorizer']={'jwt':{'claims':{'sub':subject,'iss':os.environ['COGNITO_ISSUER'],'client_id':os.environ['COGNITO_CLIENT_ID'],'token_use':'access','scope':'atmem/ask'}}}
            require(module.handler(browser,None)['statusCode']==200,'Browser claims-to-directory adapter failed')
            browser['requestContext']['authorizer']['jwt']['claims']['client_id']='wrong';require(module.handler(browser,None)['statusCode']==403,'Wrong browser client accepted')
            self.capabilities.append({'service':'Browser authorization adapter','mode':'synthetic claims only; no JWT signature, OAuth or MFA emulation'})
        self.rag_context=(module,event,model)
        return table,admin
    def connectors(self,table):
        sys.path.insert(0,str(self.root/'connectors'))
        sync=load_module('connector_sync',self.root/'connectors/connector_sync.py');cli=load_module('connector_cli',self.root/'connectors/connector_cli.py')
        store=cli.Store(self.db,table);checkpoint=cli.Checkpoint(self.root/'connector-checkpoint.json')
        doc={'sourceId':'one','sourceVersion':'1','title':'Source policy','text':'Synthetic source policy.','allowedSubjects':['alice'],'allowedRegions':['AU']}
        snapshot={'snapshotId':'1','complete':True,'permissionsComplete':True,'documents':[doc]}
        sync.synchronize(snapshot,'fixture',store,checkpoint);saved=checkpoint.load('fixture');key=next(iter(saved['documents']));require(store.get(key)['text']==doc['text'],'Connector did not write into emulated DynamoDB')
        module,event,model=self.rag_context
        event={**event,'body':json.dumps({'question':'source policy'})}
        require(key in module.handler(event,None)['body'],'Synchronized source did not reach generated retrieval')
        self.db.update_item(TableName=table,Key={'recordId':{'S':'DOCUMENT#'+key}},UpdateExpression='SET authorizationExpiresAt = :expired',ExpressionAttributeValues={':expired':{'N':str(int(time.time())-1)}})
        before=len(model.calls);require(json.loads(module.handler(event,None)['body']).get('abstained') is True and len(model.calls)==before,'Expired source permission lease reached model boundary')
        try:sync.synchronize({**snapshot,'permissionsComplete':False},'fixture',store,checkpoint)
        except ValueError:pass
        else:raise EmulationFailure('Incomplete source permissions accepted')
        # Fail after a write but before final checkpoint, then resume from the journal.
        original=store.put
        def interrupted(item,expected):original(item,expected);raise OSError('Synthetic interruption')
        store.put=interrupted
        try:sync.synchronize({**snapshot,'snapshotId':'2','documents':[{**doc,'sourceVersion':'2','text':'Updated policy.'}]},'fixture',store,checkpoint)
        except OSError:pass
        else:raise EmulationFailure('Connector fault injection did not interrupt')
        store.put=original
        sync.synchronize({**snapshot,'snapshotId':'2','documents':[{**doc,'sourceVersion':'2','text':'Updated policy.','allowedSubjects':['bob']}]},'fixture',store,checkpoint)
        require(store.get(key)['allowedSubjects']==['bob'],'Connector ACL recovery failed')
        require(not checkpoint.load('fixture').get('pending'),'Recovered connector journal retained pending writes')
        sync.synchronize({**snapshot,'snapshotId':'3','documents':[]},'fixture',store,checkpoint);require(store.get(key) is None,'Source deletion was not propagated')
        self.capabilities.append({'service':'Source connectors','mode':'normalized snapshot fixture + emitted sync/journal code + stateful DynamoDB; vendor HTTP APIs unverified'})
    def run(self):
        import moto
        from moto import mock_aws
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from emulation_adapters import s3_version_notifications, PATCH
        self.report['emulatorPatches']=[PATCH]
        self.report['backendVersion']=moto.__version__
        stateful={'aws_s3_bucket','aws_s3_bucket_versioning','aws_s3_bucket_server_side_encryption_configuration','aws_s3_bucket_public_access_block','aws_s3_bucket_notification','aws_sqs_queue','aws_dynamodb_table'}
        self.report['resourceCoverage']=[{'type':name,'count':len(items),'mode':'stateful-api-adapter' if name in stateful else 'host-executed-code' if name=='aws_lambda_function' else 'not-emulated'} for name,items in self.resources.items() if name!='terraform_data']
        require(not self.tf.get('locals',{}).get('unfinished_work'),'Incomplete architecture blocks emulation')
        require(len(self.plan['rows'])<=40,'Architecture exceeds local emulation limit')
        os.environ.update(AWS_ACCESS_KEY_ID='testing',AWS_SECRET_ACCESS_KEY='testing',AWS_DEFAULT_REGION=REGION,AWS_EC2_METADATA_DISABLED='true')
        with mock_aws(config={'core':{'mock_credentials':True,'service_whitelist':['s3','sqs','dynamodb'],'passthrough':{'urls':[],'services':[]}},'lambda':{'use_docker':False}}):
            with deny_network(), s3_version_notifications():
                self.check('Stateful emulator resource setup',self.setup)
                for row in self.plan['rows']:
                    if row.get('foundation'):self.check('Versioned storage and prior-version recovery: '+row['address'],lambda r=row:self.storage(r['address']))
                    if row.get('compute'):self.check('Generated statistics handler and input bounds: '+row['address'],lambda r=row:self.statistics(r['address']))
                for pipeline in self.plan['asyncPlan']['pipelines']:self.check('Generated async pipeline, duplicate safety, DLQ and replay',lambda p=pipeline:self.asynchronous(p))
                for address,fn in self.resources.get('aws_lambda_function',{}).items():
                    env=fn['environment']['variables']
                    if 'CATALOG_TABLE' in env:
                        self.check('Generated retrieval, conditional writes, ACLs, updates, deletion and revocation',lambda a=address:self.rag(a))
                        if self.plan['sourceContractPlan']['sources']:self.check('Generated source synchronization, interruption recovery, ACLs and deletes',lambda:self.connectors(os.environ['CATALOG_TABLE']))
                    elif any(r.get('address')==address and r.get('structured') for r in self.plan['rows']):self.check('Generated structured operation, authorization, revocation and fail-closed data policy',lambda a=address:self.structured(a),evidence='host-runtime-with-scripted-policy-identity-model-fixtures')
                    elif 'MODEL_ARN' in env:self.check('Generated summary handler, token bounds and simulated model faults',lambda a=address:self.summary(a))
                require(set(self.resources.get('aws_lambda_function',{}))==set(self.modules),'Some generated functions lack an emulator scenario')
                require(len(self.checks)>1,'No supported executable scenario in this design')
        self.report.update(status='passed',cleanup='passed',message='Supported local emulation checks passed. Review the unverified boundaries before deployment.')
        return self.report


def main():
    worker=Worker(sys.argv[1])
    try:result=worker.run()
    except Exception as exc:
        worker.report.update(status='failed',cleanup='process_exit',message='Emulation failed; no live cloud operations were attempted.',failureType=type(exc).__name__)
        if not worker.checks:worker.checks.append({'name':'Emulation eligibility','passed':False,'message':str(exc)[:400] if isinstance(exc,EmulationFailure) else 'Worker initialization failed.'})
        result=worker.report
    print(json.dumps(result))
    raise SystemExit(0 if result['status']=='passed' else 1)

if __name__=='__main__':main()
