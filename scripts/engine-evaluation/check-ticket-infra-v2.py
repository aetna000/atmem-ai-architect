"""Independent no-account Terraform assertions for the SDK-enabled primary package.

Assertions are evaluator overlays in a disposable sandbox copy. Client source and
the captured artifact are never repaired. Provider mocks do not prove AWS behavior.
"""
import argparse,asyncio,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
ASSERTIONS=[('aws_lambda_function.app.runtime == "python3.12" && aws_lambda_function.app.architectures == tolist(["arm64"])',
  'Declared and locally checked production runtime'),
 ('aws_lambda_function.app.reserved_concurrent_executions >= 5 && aws_lambda_function.app.memory_size == 256',
  'Capacity supports five and matches documented256MB footprint'),
 ('aws_lambda_function.app.timeout > 0 && aws_apigatewayv2_integration.app.timeout_milliseconds >= 1000 * '
  'aws_lambda_function.app.timeout && aws_apigatewayv2_integration.app.timeout_milliseconds <= 30000',
  'Finite coherent integration timeout, no invented customer SLA'),
 ('aws_lambda_function.app.environment[0].variables.CLIENT_ID == aws_cognito_user_pool_client.browser.id && '
  'aws_lambda_function.app.environment[0].variables.REDIRECT_URI == "${aws_apigatewayv2_api.app.api_endpoint}/"',
  'Client/config callback wiring'),
 ('aws_apigatewayv2_route.suggest.authorization_type == "JWT" && aws_apigatewayv2_route.suggest.route_key == '
  '"POST /suggest" && aws_apigatewayv2_route.suggest.authorization_scopes == toset(["review/suggest"])',
  'JWT-protected API and implementation scope'),
 ('sort(keys(aws_apigatewayv2_route.public)) == tolist(["GET /", "GET /app.js", "GET /config", "GET /style.css"])',
  'Only intended public asset/config routes'),
 ('aws_cognito_user_pool.staff.admin_create_user_config[0].allow_admin_create_user_only && '
  'aws_cognito_user_pool.staff.mfa_configuration == "ON" && '
  'aws_cognito_user_pool.staff.software_token_mfa_configuration[0].enabled',
  'Invited staff and declared TOTP policy'),
 ('!aws_cognito_user_pool_client.browser.generate_secret && '
  'aws_cognito_user_pool_client.browser.allowed_oauth_flows == toset(["code"]) && '
  'contains(aws_cognito_user_pool_client.browser.allowed_oauth_scopes,"review/suggest")',
  'Public authorization-code client and scope'),
 ('aws_cognito_user_group.reviewers.name == "reviewers" && aws_cognito_user_group.reviewers.user_pool_id == '
  'aws_cognito_user_pool.staff.id',
  'Staff group agrees with handler authorization'),
 ('jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Action == ["bedrock:InvokeModel"] && '
  'jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Resource == '
  '"arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.nova-lite-v1:0"',
  'Direct Sydney model grant only'),
 ('length(jsondecode(aws_iam_role_policy.runtime.policy).Statement) == 3 && '
  'jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Action == ["bedrock:GetAccountDataRetention", '
  '"bedrock:GetModelInvocationLoggingConfiguration"] && '
  'jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Condition.StringEquals["aws:RequestedRegion"] == '
  '"ap-southeast-2"',
  'Read-only regional safety checks; no account-policy mutation'),
 ('aws_lambda_permission.gateway.principal == "apigateway.amazonaws.com" && aws_lambda_permission.gateway.action '
  '== "lambda:InvokeFunction"',
  'API Gateway invocation boundary')]
mock='''mock_provider "aws" {
 mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
 mock_data "aws_partition" { defaults = { partition = "aws" } }
 mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::123456789012:role/evaluator-runtime" } }
 mock_resource "aws_apigatewayv2_api" { defaults = {
 api_endpoint = "https://example.execute-api.ap-southeast-2.amazonaws.com"
 execution_arn = "arn:aws:execute-api:ap-southeast-2:123456789012:independent"
 } }
 mock_resource "aws_cognito_user_pool" { defaults = { id = "ap-southeast-2_Independent" } }
 mock_resource "aws_cognito_user_pool_client" { defaults = { id = "independentclient" } }
 mock_resource "aws_cloudwatch_log_group" { defaults = { arn = "arn:aws:logs:ap-southeast-2:123456789012:log-group:/aws/lambda/independent" } }
}
'''
ORACLE=mock+'variables { cognito_domain_prefix = "independent-evaluator" }\n'+'run "independent_boundaries" {\n command = apply\n'+''.join(' assert {\n  condition = '+condition+'\n  error_message = '+json.dumps(label)+'\n }\n'for condition,label in ASSERTIONS)+'}\n'
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--tools',type=Path,required=True);parser.add_argument('--output',type=Path);args=parser.parse_args()


async def main():
 run=args.run.resolve();manifest=json.loads((run/'artifact.json').read_text());content=(run/'artifact.zip').read_bytes();assert hashlib.sha256(content).hexdigest()==manifest['sha256']
 output=args.output.resolve() if args.output else run/'independent-infrastructure-v2';output.mkdir(exist_ok=False)
 config=json.loads(args.tools.read_text());tools=config['tools'];results=[]
 with tempfile.TemporaryDirectory(prefix='ati-',dir='/tmp') as temp:
  workspace=Path(temp).resolve()/'work';workspace.mkdir()
  with zipfile.ZipFile(run/'artifact.zip') as archive:
   assert all(not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts for item in archive.infolist());archive.extractall(workspace)
  runtime_hashes={}
  catalog=json.loads((workspace/'atmem-tools/dependencies.json').read_text())
  for item in catalog['artifacts']:
   wheel=workspace/'deps'/item['file'];assert hashlib.sha256(wheel.read_bytes()).hexdigest()==item['sha256']
   with zipfile.ZipFile(wheel) as dependency:
    for member in dependency.infolist():
     if not member.is_dir():runtime_hashes[member.filename]=hashlib.sha256(dependency.read(member.filename)).hexdigest()
  for folder in ['app','web']:
   for file in (workspace/folder).iterdir():
    if file.is_file() and (folder=='web' or file.suffix=='.py'):runtime_hashes[('web/' if folder=='web' else '')+file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
  hashes={str(file.relative_to(workspace)):hashlib.sha256(file.read_bytes()).hexdigest() for file in workspace.rglob('*') if file.is_file() and file != workspace/'dist/function.zip'}
  overlay=workspace/'infra/tests/independent.tftest.hcl';assert not overlay.exists()
  worker=CodexWorkerClient(workspace,read_roots=config['readRoots'])
  try:
   await worker.start();await worker.verify_worker_tools()
   commands=[('public-offline-setup',[tools['python'],'atmem-tools/prepare.py',*sum(([('--provider-mirror' if key=='providerMirror' else '--'+key),tools[key]]for key in ['python','node','terraform','providerMirror']),[]),'--require','python','--require','terraform','--require','providerMirror']),('rebuild-runtime-package',[tools['python'],'scripts/build.py']),('terraform-format',[tools['terraform'],'-chdir=infra','fmt','-check','-recursive']),('offline-init',[tools['terraform'],'-chdir=infra','init','-backend=false','-input=false','-lockfile=readonly','-no-color']),('provider-schema',[tools['terraform'],'-chdir=infra','validate','-no-color']),('independent-mocked-apply',[tools['terraform'],'-chdir=infra','test','-filter=tests/independent.tftest.hcl','-no-color'])]
   for name,command in commands:
    # Assess the exported files' format before adding the evaluator's own HCL.
    # An unformatted oracle must not become a fabricated client-format failure.
    if name=='independent-mocked-apply':overlay.write_text(ORACLE)
    result=await worker.request('command/exec',{'command':command,'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TF_CLI_CONFIG_FILE':str(workspace/'.worker-tmp/terraform.rc'),'OPENSSL_CONF':str(workspace/'.worker-tmp/openssl.cnf'),'TMPDIR':str(workspace/'.worker-tmp'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'},'timeoutMs':60000,'outputBytesCap':100000},timeout=70)
    results.append({'name':name,**result});print(name,result['exitCode'],result.get('stdout','')[-1500:],result.get('stderr','')[-1500:],flush=True)
    if result['exitCode']!=0:break
   with zipfile.ZipFile(workspace/'dist/function.zip') as rebuilt:runtime_matches=runtime_hashes=={n:hashlib.sha256(rebuilt.read(n)).hexdigest() for n in rebuilt.namelist() if not n.endswith('/')}
   changed=[name for name,digest in hashes.items() if not (workspace/name).is_file() or hashlib.sha256((workspace/name).read_bytes()).hexdigest()!=digest]
  finally:await worker.close()
 receipt={'passed':len(results)==6 and all(result['exitCode']==0 for result in results) and not changed and runtime_matches,'runtimeFilesByteIdentical':runtime_matches,'artifactSha256':manifest['sha256'],'oracleSha256':hashlib.sha256(ORACLE.encode()).hexdigest(),'assertions':len(ASSERTIONS),'sourceChanged':changed,'checks':results,'inferenceTurns':0,'cloudOperations':False,'boundary':'Clean receiving copy/public offline setup/runtime-content reproducible rebuild/format/real provider schema plus independent evaluator overlay: independent assertions in an offline-provider mocked apply. Original captured source/dependencies and built runtime file contents match independently enumerated included source and wheel member bytes; ZIP timestamps may differ. No requirement for byte-identical archive metadata is invented. No account plan/apply, effective cloud IAM, service capacity or deployed-system claim.'}
 (output/'oracle.tftest.hcl').write_text(ORACLE);(output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert receipt['passed'],receipt


asyncio.run(main())
