"""Independent no-account Terraform assertions for the exposed primary package.

Assertions are evaluator overlays in a disposable sandbox copy. Client source and
the captured artifact are never repaired. Provider mocks do not prove AWS behavior.
"""
import argparse,asyncio,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
ASSERTIONS=[
 ('aws_lambda_function.web.runtime == "python3.12" && aws_lambda_function.web.architectures == tolist(["arm64"])','Declared production runtime and architecture'),
 ('aws_lambda_function.web.reserved_concurrent_executions == 5 && aws_lambda_function.web.memory_size == 256','Five-request starting footprint'),
 ('aws_lambda_function.web.timeout == 28 && aws_apigatewayv2_integration.web.timeout_milliseconds == 29000','Concrete bounded integration timeouts'),
 ('aws_lambda_function.web.environment[0].variables.INFERENCE_ENABLED == "false" && aws_lambda_function.web.environment[0].variables.RETENTION_VERIFIED_UNTIL == "0" && aws_lambda_function.web.environment[0].variables.ALLOWED_SUBS == "[]"','Unknown safety/access configuration disables inference'),
 ('aws_apigatewayv2_route.suggest.authorization_type == "JWT" && aws_apigatewayv2_route.suggest.route_key == "POST /suggest" && aws_apigatewayv2_route.suggest.authorization_scopes == toset(["ticket-review/suggest"])','Protected application route and exact custom scope'),
 ('sort(keys(aws_apigatewayv2_route.assets)) == tolist(["GET /", "GET /app.js", "GET /config.json", "GET /style.css"])','Only intended public static/config routes'),
 ('aws_cognito_user_pool.staff.admin_create_user_config[0].allow_admin_create_user_only && aws_cognito_user_pool.staff.mfa_configuration == "ON" && aws_cognito_user_pool.staff.software_token_mfa_configuration[0].enabled','Invited staff and mandatory TOTP'),
 ('!aws_cognito_user_pool_client.web.generate_secret && aws_cognito_user_pool_client.web.allowed_oauth_flows == toset(["code"]) && contains(aws_cognito_user_pool_client.web.allowed_oauth_scopes,"ticket-review/suggest")','Public authorization-code client and scope'),
 ('jsondecode(aws_iam_role_policy.model_only.policy).Statement[0].Action == "bedrock:InvokeModel" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[0].Resource == "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0"','Exact direct Sydney model permission'),
 ('length(jsondecode(aws_iam_role_policy.model_only.policy).Statement) == 3 && jsondecode(aws_iam_role_policy.model_only.policy).Statement[1].Action == "bedrock:GetModelInvocationLoggingConfiguration" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[2].Effect == "Deny" && jsondecode(aws_iam_role_policy.model_only.policy).Statement[2].Condition.StringNotEquals["aws:RequestedRegion"] == "ap-southeast-2"','Bounded logging read and no foreign-region Bedrock fallback'),
 ('aws_lambda_permission.gateway.principal == "apigateway.amazonaws.com" && aws_lambda_permission.gateway.action == "lambda:InvokeFunction"','API Gateway service invocation boundary')]
mock='''mock_provider "aws" {
 mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
 mock_data "aws_partition" { defaults = { partition = "aws" } }
 mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::123456789012:role/evaluator-runtime" } }
 mock_resource "aws_apigatewayv2_api" { defaults = { api_endpoint = "https://example.execute-api.ap-southeast-2.amazonaws.com" } }
}
'''
ORACLE=mock+'run "independent_boundaries" {\n command = plan\n'+''.join(' assert {\n  condition = '+condition+'\n  error_message = '+json.dumps(label)+'\n }\n'for condition,label in ASSERTIONS)+'}\n'
subs=[f'00000000-0000-0000-0000-{index:012d}' for index in range(1,12)]
ORACLE+='run "staff_count_is_not_a_business_quota" {\n command = plan\n variables { allowed_subs = '+json.dumps(subs)+' }\n assert {\n condition = length(jsondecode(aws_lambda_function.web.environment[0].variables.ALLOWED_SUBS)) == 11\n error_message = "Ten staff was a planning input; do not invent a hard roster quota"\n }\n}\n'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--output',type=Path);args=parser.parse_args()


async def main():
 run=args.run.resolve();manifest=json.loads((run/'artifact.json').read_text());content=(run/'artifact.zip').read_bytes();assert hashlib.sha256(content).hexdigest()==manifest['sha256']
 output=args.output.resolve() if args.output else run/'independent-infrastructure';output.mkdir(exist_ok=False)
 config=json.loads(args.tools.read_text());tools=config['tools'];results=[]
 with tempfile.TemporaryDirectory(prefix='ati-',dir='/tmp') as temp:
  workspace=Path(temp).resolve()/'work';workspace.mkdir()
  with zipfile.ZipFile(run/'artifact.zip') as archive:
   assert all(not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts for item in archive.infolist());archive.extractall(workspace)
  hashes={str(file.relative_to(workspace)):hashlib.sha256(file.read_bytes()).hexdigest() for file in workspace.rglob('*') if file.is_file()}
  overlay=workspace/'infra/tests/independent.tftest.hcl';assert not overlay.exists()
  worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
  try:
   await worker.start();await worker.verify_worker_tools()
   commands=[('public-offline-setup',[tools['python'],'atmem-tools/prepare.py',*sum(([('--provider-mirror' if key=='providerMirror' else '--'+key),tools[key]]for key in ['python','node','terraform','providerMirror']),[]),'--require','python','--require','terraform','--require','providerMirror']),('rebuild-runtime-package',[tools['python'],'scripts/build.py']),('terraform-format',[tools['terraform'],'-chdir=infra','fmt','-check','-recursive']),('offline-init',[tools['terraform'],'-chdir=infra','init','-backend=false','-input=false','-lockfile=readonly','-no-color']),('provider-schema',[tools['terraform'],'-chdir=infra','validate','-no-color']),('independent-mock-plans',[tools['terraform'],'-chdir=infra','test','-filter=tests/independent.tftest.hcl','-no-color'])]
   for name,command in commands:
    # Assess the exported files' format before adding the evaluator's own HCL.
    # An unformatted oracle must not become a fabricated client-format failure.
    if name=='independent-mock-plans':overlay.write_text(ORACLE)
    result=await worker.request('command/exec',{'command':command,'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TF_CLI_CONFIG_FILE':str(workspace/'.worker-tmp/terraform.rc'),'OPENSSL_CONF':str(workspace/'.worker-tmp/openssl.cnf'),'TMPDIR':str(workspace/'.worker-tmp'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'},'timeoutMs':60000,'outputBytesCap':100000},timeout=70)
    results.append({'name':name,**result});print(name,result['exitCode'],result.get('stdout','')[-1500:],result.get('stderr','')[-1500:],flush=True)
    if result['exitCode']!=0:break
   changed=[name for name,digest in hashes.items() if not (workspace/name).is_file() or hashlib.sha256((workspace/name).read_bytes()).hexdigest()!=digest]
  finally:await worker.close()
 receipt={'passed':len(results)==6 and all(result['exitCode']==0 for result in results) and not changed,'artifactSha256':manifest['sha256'],'oracleSha256':hashlib.sha256(ORACLE.encode()).hexdigest(),'assertions':12,'sourceChanged':changed,'checks':results,'inferenceTurns':0,'cloudOperations':False,'boundary':'Clean receiving copy/public offline setup/deterministic runtime rebuild/format/real provider schema plus independent evaluator overlay: twelve assertions in two offline-provider mock plans. Original captured client files remain byte-identical. No account plan/apply, effective cloud IAM, service capacity or deployed-system claim.'}
 (output/'oracle.tftest.hcl').write_text(ORACLE);(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'],receipt


asyncio.run(main())
