"""Independent cached-provider schema/mock plans on unchanged generated Terraform."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];package=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();configuration=out/'configuration';configuration.mkdir()
files={p.name:p.read_bytes()for p in (package/'infra').iterdir()if p.is_file()};before={name:hashlib.sha256(value).hexdigest()for name,value in files.items()}
for name,value in files.items():(configuration/name).write_bytes(value)
(configuration/'tests').mkdir();mirror=(ROOT/'.local/provider-cache').resolve();cli=out/'mirror.tfrc';cli.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(mirror))+' } }\ndisable_checkpoint = true\n')
variables={'environment':'staging','aws_account_id':'123456789012','name':'lab-qualification','vpc_id':'vpc-0123456789abcdef0','private_subnet_ids':['subnet-0123456789abcdef1','subnet-0123456789abcdef2'],'public_subnet_ids':['subnet-0123456789abcdef3','subnet-0123456789abcdef4'],'operator_security_group_id':'sg-0123456789abcdef5','api_hostname':'equipment.example','certificate_arn':'arn:aws:acm:ap-southeast-2:123456789012:certificate/11111111-1111-4111-8111-111111111111','cognito_domain_prefix':'synthetic-lab-qualification','login_callback_urls':['https://equipment.example/'],'logout_urls':['https://equipment.example/'],'destination_endpoint':'https://fulfilment.example/actions','destination_scope':'reviewed-equipment','destination_secret_arn':'arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:synthetic-destination-123456','destination_kms_key_arn':'arn:aws:kms:ap-southeast-2:123456789012:key/11111111-1111-4111-8111-111111111111','operator_principal_arn':'arn:aws:iam::123456789012:role/QualificationOperator'}
text='mock_provider "aws" {\n override_during = plan\n'
mock={'aws_cloudwatch_log_group':{'arn':'arn:aws:logs:ap-southeast-2:123456789012:log-group:equipment'},'aws_db_instance':{'resource_id':'db-SYNTHETIC1234567890123456','address':'synthetic.ap-southeast-2.rds.amazonaws.com','master_user_secret':[{'secret_arn':'arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:synthetic-operator-123456','kms_key_id':'arn:aws:kms:ap-southeast-2:123456789012:key/11111111-1111-4111-8111-111111111111','secret_status':'active'}]},'aws_ecr_repository':{'repository_url':'123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/equipment','arn':'arn:aws:ecr:ap-southeast-2:123456789012:repository/equipment'},'aws_security_group':{'id':'sg-0123456789abcdef0'},'aws_lb':{'arn':'arn:aws:elasticloadbalancing:ap-southeast-2:123456789012:loadbalancer/app/lab/1234567890123456'},'aws_lb_target_group':{'arn':'arn:aws:elasticloadbalancing:ap-southeast-2:123456789012:targetgroup/lab/1234567890123456'},'aws_ecs_cluster':{'arn':'arn:aws:ecs:ap-southeast-2:123456789012:cluster/lab'},'aws_cognito_user_pool':{'id':'ap-southeast-2_SYNTHETIC'},'aws_cognito_user_pool_client':{'id':'syntheticclient'},'aws_ecs_task_definition':{'arn':'arn:aws:ecs:ap-southeast-2:123456789012:task-definition/lab:1'}}
for kind,defaults in mock.items():text+=' mock_resource '+json.dumps(kind)+' { defaults = '+json.dumps(defaults)+' }\n'
text+='}\nvariables {\n'+''.join(' '+key+' = '+json.dumps(value)+'\n'for key,value in variables.items())+'}\n'
for kind in ['task','execution']:
 for purpose in ['api','worker']:text+='override_resource {\n override_during = plan\n target = aws_iam_role.'+kind+'['+json.dumps(purpose)+']\n values = '+json.dumps({'arn':'arn:aws:iam::123456789012:role/'+purpose+'-'+kind})+'\n}\n'

def run(name,checks,values=None,failures=None):
 global text
 text+='run '+json.dumps(name)+' {\n command = plan\n'
 if values:text+=' variables {\n'+''.join(' '+key+' = '+json.dumps(value)+'\n'for key,value in values.items())+' }\n'
 if failures:text+=' expect_failures = ['+', '.join(failures)+']\n'
 for check,message in checks:text+=' assert {\n condition = '+check+'\n error_message = '+json.dumps(message)+'\n }\n'
 text+='}\n'

run('runtime_off_by_default',[
 ('length(aws_ecs_task_definition.app) == 0 && length(aws_ecs_service.api) == 0 && length(aws_ecs_service.worker) == 0','No runtime without explicit enablement'),
 ('aws_db_instance.app.storage_encrypted && !aws_db_instance.app.publicly_accessible && aws_db_instance.app.iam_database_authentication_enabled && aws_db_instance.app.deletion_protection && !aws_db_instance.app.skip_final_snapshot','Encrypted private protected IAM SQL'),
 ('output.public_bindings.api.publicOrigin == "https://equipment.example" && output.public_bindings.destination.endpointSha256 == sha256(var.destination_endpoint)','Public runtime inputs bind exact source/destination')])
api='jsondecode(aws_ecs_task_definition.app["api"].container_definitions)[0]';worker='jsondecode(aws_ecs_task_definition.app["worker"].container_definitions)[0]'
run('native_runtime_bindings',[
 ('length(aws_ecs_task_definition.app) == 2 && aws_ecs_task_definition.app["api"].task_role_arn != aws_ecs_task_definition.app["worker"].task_role_arn','Separate runtime roles'),
 ('aws_ecs_task_definition.app["api"].runtime_platform[0].cpu_architecture == "ARM64" && aws_ecs_task_definition.app["worker"].runtime_platform[0].cpu_architecture == "ARM64"','Preserve selected ARM64 images'),
 (api+'.image == "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/equipment@sha256:'+('1'*64)+'" && '+api+'.user == "10001:10001" && '+api+'.readonlyRootFilesystem','Exact image identity and nonroot/read-only boundary'),
 ('length('+api+'.secrets) == 0 && '+worker+'.secrets[0].name == "DESTINATION_BEARER" && '+worker+'.secrets[0].valueFrom == var.destination_secret_arn','Outbound secret stays worker-only'),
 (worker+'.command == ["python", "equipment_worker.py"] && '+worker+'.image == '+api+'.image','Actual worker source in same qualified image'),
 ('{for item in '+api+'.environment : item.name => item.value}.DATABASE_USER == "equipment_api" && {for item in '+worker+'.environment : item.name => item.value}.DATABASE_USER == "equipment_worker"','Exact role-specific database logins'),
 ('!strcontains(aws_iam_role_policy.execution["api"].policy,"secretsmanager:GetSecretValue") && strcontains(aws_iam_role_policy.execution["worker"].policy,var.destination_secret_arn)','Native execution IAM secret separation'),
 ('strcontains(aws_iam_role_policy.database["api"].policy,"/equipment_api") && !strcontains(aws_iam_role_policy.database["api"].policy,"/equipment_worker")','Database IAM is scoped to its own login')],{'runtime_enabled':True,'image_digest':'sha256:'+'1'*64})
run('reject_unknown_environment',[],{'environment':'other'},['var.environment'])
run('reject_credential_endpoint',[],{'destination_endpoint':'https://user:password@fulfilment.example/actions'},['var.destination_endpoint'])
run('reject_mutable_image',[],{'image_digest':'latest'},['var.image_digest'])
(configuration/'tests/independent.tftest.hcl').write_text(text)
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(cli),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
commands=[]
for command in [['init','-backend=false','-input=false','-lockfile=readonly','-no-color'],['validate','-json'],['test','-no-color']]:
 with(out/(command[0]+'.log')).open('wb')as log:result=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(configuration),*command],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 commands.append({'command':command,'exitCode':result.returncode})
 if result.returncode:break
assert all(hashlib.sha256((package/'infra'/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
assert all(hashlib.sha256((configuration/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
receipt={'passed':all(c['exitCode']==0 for c in commands),'commands':commands,'sourcesUnchanged':True,'sourceHashes':before,'oracleSha256':hashlib.sha256(text.encode()).hexdigest(),'cloudOperations':False,'boundary':'Actual cached AWS provider schema and independent mock-only Terraform plans, not account/state/apply, AWS behavior or complete resource acceptance.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'commands':commands}));raise SystemExit(0 if receipt['passed']else 1)
