"""Independent offline native schema/mock-plan assertions on the unchanged Google export."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[4];package=ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked';out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'.local/external-artifacts/native-amd64-runtime/v1/terraform-independent-v5';out.mkdir();cfg=out/'configuration';shutil.copytree(package/'infra',cfg)
before={str(p.relative_to(package/'infra')):hashlib.sha256(p.read_bytes()).hexdigest()for p in (package/'infra').rglob('*')if p.is_file()}
variables={'project_id':'independent-local-project','project_number':'987654321098','workforce_group_email':'receivers@independent.example.test','account_id':'70000000-0000-4000-8000-000000000001','name':'independent-samples','application_image':'offline.invalid/review/app@sha256:'+'3'*64,'sql_proxy_image':'offline.invalid/review/proxy@sha256:'+'4'*64,'worker_os_image':'projects/cos-cloud/global/images/cos-independent-review','destination_url':'https://independent.example.test/route','destination_scope':'independent-review','destination_ca_pem':'-----BEGIN CERTIFICATE-----\nINDEPENDENT-MOCK-NOT-A-REAL-CERTIFICATE\n-----END CERTIFICATE-----','destination_token_version':'7','migration_password':'synthetic-independent-write-only-password-0000'}
def hcl(value):
 if isinstance(value,dict):return '{'+','.join(json.dumps(k)+'='+hcl(v) for k,v in value.items())+'}'
 if isinstance(value,list):return '['+','.join(hcl(v)for v in value)+']'
 return json.dumps(value)
text='mock_provider "google" {\n override_during = plan\n}\nmock_provider "google-beta" {\n override_during = plan\n}\n'
def override(target,values,data=False):
 global text
 text+=('override_data' if data else 'override_resource')+' {\n target = '+target+'\n override_during = plan\n values = '+hcl(values)+'\n}\n'
project=variables['project_id'];name=variables['name'];base=f'projects/{project}/secrets/'
override('data.google_project.existing',{'number':variables['project_number']},True)
override('google_sql_database_instance.owned',{'connection_name':project+':australia-southeast1:'+name+'-pg17'})
for role in ['api','worker']:override('google_service_account.runtime['+json.dumps(role)+']',{'email':f'{name}-{role}@{project}.iam.gserviceaccount.com'})
override('google_project_service_identity.iap',{'email':f'service-{variables["project_number"]}@gcp-sa-iap.iam.gserviceaccount.com'})
for key,suffix in [('configuration','config'),('trust','trust'),('destination_token','destination-token')]:override('google_secret_manager_secret.'+key,{'id':base+name+'-'+suffix})
for key,suffix in [('configuration','config'),('trust','trust')]:override('google_secret_manager_secret_version.'+key,{'name':base+name+'-'+suffix+'/versions/1','version':'1'})
def variable_block(values):return 'variables {\n'+''.join(key+' = '+hcl(value)+'\n'for key,value in values.items())+'}\n'
text+=variable_block(variables)
api='google_cloud_run_v2_service.api';template=api+'.template[0]';app='one([for c in '+template+'.containers : c if c.name == "api"])';proxy='one([for c in '+template+'.containers : c if c.name == "sql-proxy"])';api_sa='google_service_account.runtime["api"]';worker_sa='google_service_account.runtime["worker"]';worker='google_compute_instance_template.worker';db='google_sql_database_instance.owned'
assertions=[
 (api+'.location == "australia-southeast1" && '+db+'.region == "australia-southeast1" && '+worker+'.region == "australia-southeast1"','Sydney placement across actual delivery units'),
 (api+'.iap_enabled && !'+api+'.invoker_iam_disabled && google_cloud_run_v2_service_iam_member.iap_invoker.role == "roles/run.invoker" && google_cloud_run_v2_service_iam_member.iap_invoker.member == "serviceAccount:${google_project_service_identity.iap.email}"','Native IAP service identity owns invoker grant'),
 ('google_iap_web_cloud_run_service_iam_member.workforce.member == "group:${var.workforce_group_email}" && google_iap_web_cloud_run_service_iam_member.workforce.cloud_run_service_name == '+api+'.name','Existing workforce group resource-scoped access'),
 (template+'.service_account == '+api_sa+'.email && '+worker+'.service_account[0].email == '+worker_sa+'.email && '+api_sa+'.email != '+worker_sa+'.email','Separate API/worker identities wired to actual units'),
 ('google_sql_user.runtime["api"].name == trimsuffix('+api_sa+'.email,".gserviceaccount.com") && google_sql_user.runtime["worker"].type == "CLOUD_IAM_SERVICE_ACCOUNT"','Workload SQL IAM user mapping'),
 (db+'.database_version == "POSTGRES_17" && !'+db+'.settings[0].ip_configuration[0].ipv4_enabled && '+db+'.settings[0].ip_configuration[0].ssl_mode == "ENCRYPTED_ONLY"','Private encrypted PostgreSQL17'),
 (db+'.settings[0].backup_configuration[0].point_in_time_recovery_enabled && '+db+'.settings[0].backup_configuration[0].enabled && '+db+'.deletion_protection && '+db+'.settings[0].deletion_protection_enabled','Recovery and deletion protections retained'),
 ('google_secret_manager_secret_iam_member.worker_token.secret_id == google_secret_manager_secret.destination_token.id && google_secret_manager_secret_iam_member.worker_token.member == "serviceAccount:${'+worker_sa+'.email}" && google_secret_manager_secret_iam_member.worker_token.member != "serviceAccount:${'+api_sa+'.email}"','Destination token access belongs to worker'),
 ('alltrue([for key, grant in google_secret_manager_secret_iam_member.config_access : grant.secret_id == google_secret_manager_secret.configuration.id && grant.member == "serviceAccount:${google_service_account.runtime[key].email}"]) && google_secret_manager_secret_iam_member.worker_trust.member == "serviceAccount:${'+worker_sa+'.email}"','Exact configuration/trust identity wiring'),
 ('jsondecode(google_secret_manager_secret_version.configuration.secret_data).accountId == var.account_id && jsondecode(google_secret_manager_secret_version.configuration.secret_data).destination == var.destination_url && jsondecode(google_secret_manager_secret_version.configuration.secret_data).destinationCaSha256 == sha256(var.destination_ca_pem)','Runtime account destination and CA hash preserve operator values'),
 (app+'.command == tolist(["/usr/local/bin/python3","-I","/app/sample_entry.py"]) && '+app+'.image == var.application_image && contains('+app+'.depends_on,"sql-proxy")','Actual application entrypoint and dependency ordering'),
 (proxy+'.image == var.sql_proxy_image && contains('+proxy+'.args,"--auto-iam-authn") && contains('+proxy+'.args,"--private-ip") && contains('+proxy+'.args,google_sql_database_instance.owned.connection_name)','SQL proxy native identity/private target wiring'),
 ('one([for e in '+app+'.env : e if e.name == "DATABASE_SERVICE_ACCOUNT"]).value == '+api_sa+'.email && one([for e in '+app+'.env : e if e.name == "DATABASE_NAME"]).value == google_sql_database.application.name','Actual API database identity/name configuration'),
 ('length('+worker+'.network_interface[0].access_config) == 0 && '+worker+'.shielded_instance_config[0].enable_secure_boot && '+worker+'.disk[0].source_image == var.worker_os_image','Private worker and exact reviewed OS input'),
 ('strcontains('+worker+'.metadata_startup_script,"--user 10001:10001 --cap-drop ALL --security-opt no-new-privileges") && strcontains('+worker+'.metadata_startup_script,"TOKEN_VERSION=${google_secret_manager_secret.destination_token.id}/versions/${var.destination_token_version}") && strcontains('+worker+'.metadata_startup_script,"DATABASE_SERVICE_ACCOUNT=${'+worker_sa+'.email}")','Rendered worker preserves user/capabilities/scoped credential version and SQL identity'),
 ('google_compute_region_instance_group_manager.worker.target_size == 0 && '+app+'.args[0] == "provisioning"','Admission is required before worker/application activation'),
]
def run(name,checks=(),change=None,expected=(),extra=''):
 global text
 text+='run '+json.dumps(name)+' {\n command = plan\n'
 if change:text+=variable_block(change)
 if expected:text+=' expect_failures = ['+','.join(expected)+']\n'
 text+=extra
 for condition,message in checks:text+=' assert {\n condition = '+condition+'\n error_message = '+json.dumps(message)+'\n}\n'
 text+='}\n'
run('independent_provisioning_contract',assertions)
run('independent_activation_contract',[( 'google_compute_region_instance_group_manager.worker.target_size == 1 && '+app+'.args[0] == "api"','Activation starts API and exactly one worker'),('output.iap_audience == "/projects/${var.project_number}/locations/australia-southeast1/services/${'+api+'.name}"','Audience binds existing project and actual service')],{'enable_application':True,'public_origin':'https://independent-native.run.app'})
run('deny_project_number_mismatch',expected=['check.existing_project_number',api],extra=' override_data {\n target = data.google_project.existing\n values = { number = "111111111111" }\n}\n')
run('deny_activation_without_origin',change={'enable_application':True},expected=[api])
run('deny_mutable_application_image',change={'application_image':'offline.invalid/review/app:latest'},expected=['var.application_image'])
run('deny_mutable_proxy_image',change={'sql_proxy_image':'offline.invalid/review/proxy:latest'},expected=['var.sql_proxy_image'])
run('deny_latest_token_version',change={'destination_token_version':'latest'},expected=['var.destination_token_version'])
run('deny_non_https_destination',change={'destination_url':'http://independent.example.test/route'},expected=['var.destination_url'])
run('deny_image_family',change={'worker_os_image':'projects/cos-cloud/global/images/family/cos-stable'},expected=['var.worker_os_image'])
test=cfg/'tests/independent.tftest.hcl';test.write_text(text)
subprocess.run([str(ROOT/'.venv/bin/terraform'),'fmt',str(test)],check=True,stdout=subprocess.DEVNULL)
cli=out/'mirror.tfrc';cli.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str((ROOT/'.local/provider-cache').resolve()))+' } }\ndisable_checkpoint = true\n')
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(cli),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
commands=[]
for command in [['init','-backend=false','-input=false','-lockfile=readonly','-no-color'],['fmt','-check','-recursive'],['validate','-json'],['providers','schema','-json'],['test','-no-color']]:
 with(out/(command[0]+'.log')).open('wb')as log:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),*command],env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append({'command':command,'exitCode':r.returncode})
 if r.returncode:break
ownership=None
if all(c['exitCode']==0 for c in commands):
 review=cfg/'plan-review';review.mkdir();(review/'ownership.tftest.hcl').write_text(test.read_text().split('run "independent_activation_contract"')[0])
 command=['test','-json','-verbose','-test-directory=plan-review','-no-color']
 with (out/'ownership-plan-v1.jsonl').open('wb') as log:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),*command],env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append({'command':command,'exitCode':r.returncode});assert r.returncode==0
 events=[json.loads(line)for line in(out/'ownership-plan-v1.jsonl').read_text().splitlines()];plan=next(item['test_plan']for item in events if item.get('type')=='test_plan')
 changes=plan['resource_changes'];managed=[item for item in changes if item['mode']=='managed']
 forbidden={'google_project','google_folder','google_organization','google_cloud_identity_group','google_service_account_key'}
 assert not forbidden.intersection(item['type']for item in managed)
 assert sum(item['type']=='google_cloud_run_v2_service'for item in managed)==1
 assert sum(item['type']=='google_sql_database_instance'for item in managed)==1
 assert sum(item['type']=='google_service_account'for item in managed)==2
 assert all(item['change']['actions']==['create']for item in managed)
 values={item['address']:item['change']['after']for item in managed}
 token=values['google_secret_manager_secret.destination_token']['id']
 versions=[item['change']['after']['secret']for item in managed if item['type']=='google_secret_manager_secret_version']
 assert len(versions)==2 and token not in versions
 grants=[value for address,value in values.items()if '_iam_member.'in address]
 assert all(value['member']not in {'allUsers','allAuthenticatedUsers'}for value in grants)
 token_grants=[value for address,value in values.items()if address.startswith('google_secret_manager_secret_iam_member.')and value['secret_id']==token]
 assert len(token_grants)==1 and token_grants[0]['member']=='serviceAccount:'+values['google_service_account.runtime["worker"]']['email']
 migration=values['google_sql_user.migration'];assert migration['password']is None and migration['password_wo']is None
 assert variables['migration_password']not in json.dumps(changes)
 schemas=json.loads((out/'providers.log').read_text());attribute=schemas['provider_schemas']['registry.terraform.io/hashicorp/google']['resource_schemas']['google_sql_user']['block']['attributes']['password_wo'];assert attribute['write_only']is True
 ownership={'passed':True,'plannedManagedResources':len(managed),'plannedResources':[{'address':item['address'],'type':item['type'],'actions':item['change']['actions']}for item in managed],'noProjectDirectoryGroupOrServiceAccountKeyCreation':True,'onlyOneOwnedApiAndDatabase':True,'onlyWorkerTokenGrant':True,'destinationTokenVersionAbsent':True,'migrationPasswordWriteOnlySchema':True,'migrationPasswordAbsentFromPlannedValues':True,'noPublicIamMembers':True,'rawPlanSha256':hashlib.sha256((out/'ownership-plan-v1.jsonl').read_bytes()).hexdigest(),'providerSchemasSha256':hashlib.sha256((out/'providers.log').read_bytes()).hexdigest(),'cloudOperations':False,'scope':'Synthetic mocked planned values; no actual applied state/account/policy/secret check'}
 (out/'ownership-v1.json').write_text(json.dumps(ownership,indent=2)+'\n')
assert all(hashlib.sha256((package/'infra'/name).read_bytes()).hexdigest()==sha for name,sha in before.items())
assert all(hashlib.sha256((cfg/name).read_bytes()).hexdigest()==sha for name,sha in before.items())
receipt={'passed':all(c['exitCode']==0 for c in commands),'commands':commands,'sourceUnchanged':True,'sourceHashes':before,'oracleSha256':hashlib.sha256(test.read_bytes()).hexdigest(),'independentRuns':9,'generatedRuns':2,'inventoryPlanRuns':1 if ownership else 0,'ownershipInventoryPassed':bool(ownership),'cloudOperations':False,'scope':'Native Terraform1.17.1/DarwinARM64 Google and GoogleBeta7.46.2 schemas and independent mock plans; no account, apply, state migration, native IAP login or deployment acceptance'}
(out/'receipt-v1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(0 if receipt['passed'] else 1)
