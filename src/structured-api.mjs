import {STRUCTURED_OPERATION_POLICY as policy} from './structured-operation-policy.mjs';
import {storageTestFiles} from './storage-tests.mjs';
import {structuredHandler} from './bedrock-summary.mjs';
export function structuredApiPlan(project,rows,modelPlan){
 const byId=new Map(rows.map(r=>[r.id,r])),nodes=new Map(project.nodes.map(n=>[n.id,n]));
 const entries=[];
 for(const entry of modelPlan.entries.filter(e=>e.worker.structured)){
  const links=project.edges.filter(e=>e.target===entry.worker.id&&e.integration==='http-api-lambda');
  if(links.length!==1)continue;
  const api=byId.get(links[0].source);
  if(!api||api.existing||api.provider!=='aws'||api.service!=='Amazon API Gateway'||nodes.get(api.id)?.data.implementation!=='structured-api')continue;
  entries.push({...entry,api,structured:true,edges:[links[0]]});
 }
 const counts=new Map();for(const e of entries)counts.set(e.api.id,(counts.get(e.api.id)||0)+1);
 const complete=entries.filter(e=>counts.get(e.api.id)===1);
 return {entries:complete,componentIds:complete.flatMap(e=>[e.api.id,e.worker.id,e.model.id]),edgeIds:complete.flatMap(e=>e.edges.map(x=>x.id))};
}
export const STRUCTURED_HTTP_WRAPPER=`
# Only API Gateway's verified JWT route is admitted. No request-body identity.
_operation=handler
_identity=None

def client():
    global _client
    if _client is None:_client=boto3.client("bedrock-runtime",config=Config(connect_timeout=${policy.modelConnectSeconds},read_timeout=${policy.modelReadSeconds},retries={"total_max_attempts":${policy.sdkAttempts}}))
    return _client

def identity_client():
    global _identity
    if _identity is None:_identity=boto3.client("cognito-idp",config=Config(connect_timeout=${policy.identityConnectSeconds},read_timeout=${policy.identityReadSeconds},retries={"total_max_attempts":${policy.sdkAttempts}}))
    return _identity

def _authorized(event):
    rc=event.get("requestContext",{})
    if event.get("version")!="2.0" or rc.get("apiId")!=os.environ["EXPECTED_API_ID"] or rc.get("routeKey")!="POST /api/ask":return False
    claims=rc.get("authorizer",{}).get("jwt",{}).get("claims",{})
    if claims.get("iss")!=os.environ["COGNITO_ISSUER"] or claims.get("client_id")!=os.environ["COGNITO_CLIENT_ID"] or claims.get("token_use")!="access" or "atmem/ask" not in str(claims.get("scope","")).split():return False
    if not isinstance(claims.get("sub"),str) or not claims["sub"] or not isinstance(claims.get("username"),str) or not claims["username"]:return False
    user=identity_client().admin_get_user(UserPoolId=os.environ["COGNITO_USER_POOL_ID"],Username=claims["username"])
    attributes={a["Name"]:a["Value"] for a in user.get("UserAttributes",[])}
    return user.get("Enabled") is True and user.get("UserStatus")=="CONFIRMED" and attributes.get("sub")==claims["sub"]

def _http(status,body):
    return {"statusCode":status,"headers":{"content-type":"application/json","cache-control":"no-store","x-content-type-options":"nosniff"},"body":json.dumps(body,allow_nan=False)}

def handler(event,context):
    try:
        if not isinstance(event,dict) or not _authorized(event):return _http(403,{"error":"access_denied"})
        if event.get("isBase64Encoded") is not False:return _http(400,{"error":"invalid_request"})
        raw=event.get("body")
        if not isinstance(raw,str) or len(raw.encode("utf-8"))>int(os.environ["MAX_INPUT_BYTES"])*6+100:return _http(400,{"error":"invalid_request"})
        body=json.loads(raw,object_pairs_hook=_object)
        result=_operation(body,context)
        if not _authorized(event):return _http(403,{"error":"access_denied"})
        return _http(503 if "error" in result else 200,result)
    except (ValueError,UnicodeError,RecursionError):return _http(400,{"error":"invalid_request"})
    except Exception:
        logger.warning("structured_request_failed")
        return _http(503,{"error":"temporarily_unavailable"})
`;
export function compileStructuredApi(plan,environment){
 const resources={},files={},tests=[];
 const add=(type,name,body)=>(resources[type]||={})[name]={...body,depends_on:['terraform_data.review_gate',...(body.depends_on||[])]};
 const ref=(type,row,field)=>'${'+type+'.'+row.address+'.'+field+'}';
 for(const {worker,api} of plan.structuredApiPlan.entries){
  // A complete web/JWT composition is required; IAM-only routing is not silently substituted.
  if(!plan.webPlan.entries.some(e=>e.structured&&e.api.id===api.id))continue;
  const n=worker.address,a=api.address,tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:a};
  add('aws_apigatewayv2_api',a,{name:'atmem-'+a.slice(0,25),protocol_type:'HTTP',tags});
  add('aws_apigatewayv2_integration',a,{api_id:ref('aws_apigatewayv2_api',api,'id'),integration_type:'AWS_PROXY',integration_uri:ref('aws_lambda_alias',worker,'invoke_arn'),payload_format_version:'2.0',timeout_milliseconds:policy.gatewayDeadlineMs});
  add('aws_cloudwatch_log_group',a,{name:'/aws/apigateway/'+ref('aws_apigatewayv2_api',api,'id'),retention_in_days:'${var.'+n+'_log_retention_days}',tags});
  add('aws_apigatewayv2_stage',a,{api_id:ref('aws_apigatewayv2_api',api,'id'),name:'live',auto_deploy:true,default_route_settings:{throttling_burst_limit:2,throttling_rate_limit:1},access_log_settings:{destination_arn:ref('aws_cloudwatch_log_group',api,'arn'),format:JSON.stringify({requestId:'$context.requestId',status:'$context.status',routeKey:'$context.routeKey'})},tags});
  files['handlers/'+n+'.py']=structuredHandler(worker.settings.outputContract)+STRUCTURED_HTTP_WRAPPER;
  files['app-tests/'+n+'_test.py']=httpTests(n,worker.settings.outputContract);
  const web=plan.webPlan.entries.find(e=>e.structured&&e.api.id===api.id),w=web.web.address,i=web.identity.address;
  tests.push(`run "${a}_jwt_boundary" {
 command = plan
 assert {
  condition = aws_apigatewayv2_route.${w}.authorization_type == "JWT" && contains(aws_apigatewayv2_route.${w}.authorization_scopes,"atmem/ask")
  error_message = "Structured operation must require verified scoped JWT access."
 }
 assert {
  condition = aws_cognito_user_pool.${i}.mfa_configuration == "ON" && aws_cognito_user_pool.${i}.admin_create_user_config[0].allow_admin_create_user_only
  error_message = "Sign-in requires MFA and controlled user creation."
 }
 assert {
  condition = aws_s3_bucket_public_access_block.${w}.block_public_policy && aws_s3_bucket_public_access_block.${w}.restrict_public_buckets
  error_message = "Web assets must not expose a public S3 bucket."
 }
 assert {
  condition = aws_lambda_permission.${w}.principal == "apigateway.amazonaws.com" && aws_lambda_permission.${w}.source_account == var.aws_account_id
  error_message = "Only the account-bound API invocation contract may be generated."
 }
}`);

 }
 if(tests.length)files['tests/storage-access.tftest.hcl']=storageTestFiles(plan)['tests/storage-access.tftest.hcl']+'\n'+tests.join('\n');
 return {resources,files};
}

function httpTests(n,contract){const result=Object.fromEntries(contract.fields.map(f=>[f.name,f.type==='boolean'?false:f.type==='number'?0:f.values?.[0]||'x']));return `import json
import importlib.util
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"build/${n}"))
spec=importlib.util.spec_from_file_location("http_operation",Path(__file__).resolve().parents[1]/"build/${n}/${n}.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        os.environ.update(EXPECTED_API_ID="api",COGNITO_ISSUER="issuer",COGNITO_CLIENT_ID="client",COGNITO_USER_POOL_ID="pool",MAX_INPUT_BYTES="20000",MODEL_ARN="synthetic",MAX_OUTPUT_TOKENS="512")
        module._identity=MagicMock();module._client=MagicMock();module._retention=MagicMock();module._retention.get_account_data_retention.return_value={"mode":"none"};module._retention.get_model_invocation_logging_configuration.return_value={}
        module._identity.admin_get_user.return_value={"Enabled":True,"UserStatus":"CONFIRMED","UserAttributes":[{"Name":"sub","Value":"subject"}]}
        self.event={"version":"2.0","requestContext":{"apiId":"api","routeKey":"POST /api/ask","authorizer":{"jwt":{"claims":{"iss":"issuer","client_id":"client","token_use":"access","scope":"atmem/ask","sub":"subject","username":"user"}}}},"isBase64Encoded":False,"body":json.dumps({"text":"input"})}
    def test_valid_response_and_revocation(self):
        text=${JSON.stringify(JSON.stringify(result))}
        module._client.converse.return_value={"output":{"message":{"content":[{"text":text}]}},"stopReason":"end_turn"}
        self.assertEqual(module.handler(self.event,None)["statusCode"],200)
        user=module._identity.admin_get_user.return_value
        module._identity.admin_get_user.side_effect=[user,{**user,"Enabled":False}]
        self.assertEqual(module.handler(self.event,None)["statusCode"],403)
    def test_denies_unsigned_or_disabled_requests_without_model_call(self):
        self.assertEqual(module.handler({},None)["statusCode"],403)
        module._identity.admin_get_user.return_value["Enabled"]=False
        self.assertEqual(module.handler(self.event,None)["statusCode"],403)
        module._client.converse.assert_not_called()
    def test_identity_outage_fails_closed(self):
        module._identity.admin_get_user.side_effect=RuntimeError("private provider detail")
        self.assertEqual(module.handler(self.event,None)["statusCode"],503)
        module._client.converse.assert_not_called()
`;}
