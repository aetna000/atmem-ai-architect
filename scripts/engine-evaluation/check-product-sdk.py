#!/usr/bin/env python3
"""Evaluate the observed package on its declared Lambda runtime/architecture/SDK.

Uses the AWS-maintained public base image already prepared by the operator. Boto3
operations are intercepted locally; no account credentials or AWS endpoint is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
ORACLE=r'''
import hashlib,json,os,pathlib,sys,time,zipfile
os.environ.update(AWS_ACCESS_KEY_ID='SYNTHETIC-ONLY-NOT-A-KEY',AWS_SECRET_ACCESS_KEY='SYNTHETIC-ONLY-NOT-A-SECRET',AWS_REGION='ap-southeast-2',MODEL_ID='amazon.nova-lite-v1:0',COGNITO_ISSUER='https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Independent',CLIENT_ID='independent-client',COGNITO_DOMAIN='https://independent.auth.ap-southeast-2.amazoncognito.com')
with zipfile.ZipFile('/work/source/build/support-review.zip') as archive:archive.extractall('/tmp/delivery')
sys.path.insert(0,'/tmp/delivery')
import handler,boto3,botocore,platform
from botocore.stub import Stubber
from botocore.exceptions import ReadTimeoutError
from urllib.parse import urlsplit
assert sys.version_info[:2]==(3,12)
assert platform.machine()=='aarch64'
client=handler._bedrock()
assert urlsplit(client.meta.endpoint_url).hostname=='bedrock-runtime.ap-southeast-2.amazonaws.com'
assert client.meta.config.retries['total_max_attempts']==1
assert client.meta.config.connect_timeout==2 and client.meta.config.read_timeout==20
assert 'Converse' in client.meta.service_model.operation_names
claims={'iss':os.environ['COGNITO_ISSUER'],'client_id':os.environ['CLIENT_ID'],'token_use':'access','sub':'synthetic-staff','exp':time.time()+60,'cognito:groups':['Reviewers']}
event={'rawPath':'/api/suggest','body':json.dumps({'ticket':'Synthetic SDK contract case'}),'headers':{'content-type':'application/json'},'requestContext':{'http':{'method':'POST'},'authorizer':{'jwt':{'claims':claims}}}}
good={'summary':'Synthetic SDK response.','topic':'other','urgency':'normal','uncertainty':{'level':'high','reason':'Local transport fixture, not model quality.'}}
stub=Stubber(client)
stub.add_response('converse',{'output':{'message':{'role':'assistant','content':[{'text':json.dumps(good)}]}},'stopReason':'end_turn','usage':{'inputTokens':10,'outputTokens':10,'totalTokens':20},'metrics':{'latencyMs':1}})
stub.add_client_error('converse',service_error_code='AccessDeniedException',service_message='PRIVATE-SYNTHETIC-SDK-DIAGNOSTIC',http_status_code=403)
handler._bedrock=lambda:client
with stub:
 result=handler.handler(event,None);assert result['statusCode']==200 and json.loads(result['body'])==good
 denied=handler.handler(event,None);assert denied['statusCode']==503 and 'PRIVATE-SYNTHETIC' not in denied['body']
 stub.assert_no_pending_responses()
sent=[]
def timeout(request):
 assert urlsplit(request.url).hostname=='bedrock-runtime.ap-southeast-2.amazonaws.com'
 sent.append(True)
 raise ReadTimeoutError(endpoint_url=request.url,error='SYNTHETIC-TIMEOUT-NO-NETWORK')
client._endpoint.http_session.send=timeout
result=handler.handler(event,None);assert result['statusCode']==503 and len(sent)==1
print('INDEPENDENT_LAMBDA_SDK_CONTRACT_PASSED')
print(json.dumps({'python':sys.version,'architecture':platform.machine(),'boto3':boto3.__version__,'botocore':botocore.__version__,'endpoint':client.meta.endpoint_url,'converseInputAndResponseShape':'validated by actual runtime botocore','providerDenial':'safe failure','transportTimeoutAttempts':len(sent),'networkCalls':0}))
'''
parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--image-receipt',type=Path,required=True);args=parser.parse_args()
run=args.run.resolve();image=json.loads(args.image_receipt.read_text());manifest=json.loads((run/'artifact.json').read_text());archive=(run/'artifact.zip').read_bytes()
assert hashlib.sha256(archive).hexdigest()==manifest['sha256']
worker=DockerValidationWorker('unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock'))
spec=ValidationSpec('independent-lambda-sdk',image['imageId'],('/var/lang/bin/python3.12','-c',ORACLE),platform='linux/arm64',bootstrap_python='/var/lang/bin/python3.12')
result=worker.run(archive,manifest['sha256'],spec)
result.update(oracleSha256=hashlib.sha256(ORACLE.encode()).hexdigest(),
    semanticBoundary='Actual declared Python 3.12/ARM64 AWS-maintained image and included boto3/botocore execute the captured deployment ZIP, validate Converse shapes and regional/no-retry configuration, and handle synthetic service denial and SDK transport timeout. No real credentials, socket request, account entitlement, cloud authorization, deployment or model quality proof.')
(run/'independent-sdk-oracle.py').write_text(ORACLE);(run/'independent-sdk.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],result['output'])
assert result['status']=='passed' and 'INDEPENDENT_LAMBDA_SDK_CONTRACT_PASSED' in result['output'],result
