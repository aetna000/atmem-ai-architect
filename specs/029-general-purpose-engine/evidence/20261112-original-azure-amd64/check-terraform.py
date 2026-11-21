"""Independent cached-provider schema/mock plans on unchanged generated Terraform."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];package=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();configuration=out/'configuration';configuration.mkdir()
files={p.name:p.read_bytes()for p in (package/'infra').iterdir()if p.is_file()};before={name:hashlib.sha256(value).hexdigest()for name,value in files.items()}
for name,value in files.items():(configuration/name).write_bytes(value)
(configuration/'tests').mkdir();mirror=(ROOT/'.local/provider-cache').resolve();cli=out/'mirror.tfrc';cli.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(mirror))+' } }\ndisable_checkpoint = true\n')
variables={'subscription_id':'50000000-0000-4000-8000-000000000001','tenant_id':'50000000-0000-4000-8000-000000000002','registry_name':'independentreview','openai_name':'independent-review','owner_ids':['50000000-0000-4000-8000-000000000003'],'reviewer_ids':['50000000-0000-4000-8000-'+str(i).zfill(12) for i in range(10,20)],'secret_expiry':'2027-05-01T00:00:00Z'}
arm='/subscriptions/'+variables['subscription_id']+'/resourceGroups/staff-ticket-review/providers/'
mocks={'azurerm_container_app_environment':{'id':arm+'Microsoft.App/managedEnvironments/review','default_domain':'synthetic.australiaeast.azurecontainerapps.io'},'azurerm_cognitive_account':{'id':arm+'Microsoft.CognitiveServices/accounts/review','endpoint':'https://independent-review.openai.azure.com/'},'azurerm_container_registry':{'id':arm+'Microsoft.ContainerRegistry/registries/independentreview','login_server':'independentreview.azurecr.io'},'azurerm_user_assigned_identity':{'id':arm+'Microsoft.ManagedIdentity/userAssignedIdentities/review','principal_id':'50000000-0000-4000-8000-000000000030','client_id':'50000000-0000-4000-8000-000000000031'}}
text='mock_provider "azurerm" {\n override_during = plan\n'
for kind,defaults in mocks.items():text+=' mock_resource '+json.dumps(kind)+' { defaults = '+json.dumps(defaults)+' }\n'
text+='}\nmock_provider "azuread" {\n override_during = plan\n mock_resource "azuread_application" { defaults = { id = "/applications/50000000-0000-4000-8000-000000000040", client_id = "50000000-0000-4000-8000-000000000041", object_id = "50000000-0000-4000-8000-000000000040" } }\n mock_resource "azuread_service_principal" { defaults = { id = "/servicePrincipals/50000000-0000-4000-8000-000000000042", object_id = "50000000-0000-4000-8000-000000000042" } }\n}\nvariables {\n'+''.join(' '+k+' = '+json.dumps(v)+'\n'for k,v in variables.items())+'}\n'
def run(name,checks,values=None,failures=None):
 global text
 text+='run '+json.dumps(name)+' {\n command = plan\n'
 if values:text+=' variables {\n'+''.join(' '+k+' = '+json.dumps(v)+'\n'for k,v in values.items())+' }\n'
 if failures:text+=' expect_failures = ['+', '.join(failures)+']\n'
 for check,message in checks:text+=' assert {\n condition = '+check+'\n error_message = '+json.dumps(message)+'\n }\n'
 text+='}\n'
run('bootstrap_without_inference',[
 ('length(azurerm_container_app.review) == 0','No running app before supplied build digest'),
 ('azurerm_cognitive_account.model.location == "australiaeast" && azurerm_cognitive_deployment.review.sku[0].name == "Standard"','Australian regional target, not global fallback'),
 ('!azurerm_cognitive_account.model.local_auth_enabled && azurerm_container_app_environment.review.logs_destination == ""','Key access/log forwarding disabled'),
 ('length(azuread_app_role_assignment.reviewer) == 10 && azuread_service_principal.review.app_role_assignment_required && one(azuread_application.review.app_role).value == "Reviewer"','Actual staff role matches native identity contract'),
 ('azurerm_role_assignment.model.role_definition_name == "Cognitive Services OpenAI User" && azurerm_role_assignment.policy_read.role_definition_name == "Reader" && azurerm_role_assignment.registry.role_definition_name == "AcrPull"','Actual workload inference/policy/image access'),
 ('azurerm_role_assignment.model.scope == azurerm_cognitive_account.model.id && azurerm_role_assignment.policy_read.scope == azurerm_cognitive_account.model.id && azurerm_role_assignment.registry.scope == azurerm_container_registry.review.id','No helpdesk or broad subscription permissions')])
a='azurerm_container_app.review[0].template[0].container[0]';env='{for e in '+a+'.env : e.name => e.value}'
run('exact_application_bindings',[
 ('azurerm_container_app.review[0].template[0].min_replicas == 1 && azurerm_container_app.review[0].template[0].max_replicas == 1 && '+a+'.cpu == 0.5 && '+a+'.memory == "1Gi"','Single justified session/slot footprint'),
 (a+'.image == "independentreview.azurecr.io/ticket-review@sha256:'+('1'*64)+'"','Exact receiving image identity'),
 (env+'.PUBLIC_ORIGIN == "https://staff-ticket-review.synthetic.australiaeast.azurecontainerapps.io" && tolist(azuread_application.review.web[0].redirect_uris) == tolist([format("%s/auth/callback",local.origin)])','Browser/callback/origin coherence'),
 (env+'.TENANT_ID == var.tenant_id && '+env+'.CLIENT_ID == azuread_application.review.client_id && '+env+'.REVIEWER_IDS == join(",",sort(tolist(var.reviewer_ids)))','Actual identity/assignment allowlist matches runtime'),
 (env+'.AZURE_ACCOUNT_ID == azurerm_cognitive_account.model.id && '+env+'.AZURE_MODEL == var.model && '+env+'.AZURE_MODEL_VERSION == var.model_version && '+env+'.AZURE_DEPLOYMENT == azurerm_cognitive_deployment.review.name','Actual account/model/version/deployment match runtime readiness'),
 (env+'.MANAGED_IDENTITY_CLIENT_ID == azurerm_user_assigned_identity.review.client_id && one([for e in '+a+'.env : e if e.name == "CLIENT_SECRET"]).secret_name == "oidc-secret"','Workload identity/client secret wiring'),
 ('!azurerm_container_app.review[0].ingress[0].allow_insecure_connections && azurerm_container_app.review[0].ingress[0].target_port == 8080','HTTPS ingress to actual HTTP entrypoint')],{'deploy_application':True,'image_digest':'sha256:'+'1'*64})
run('deny_start_without_image',[],{'deploy_application':True,'image_digest':''},['azurerm_container_app.review'])
run('deny_mutable_image',[],{'image_digest':'latest'},['var.image_digest'])
(configuration/'tests/independent.tftest.hcl').write_text(text)
subprocess.run([str(ROOT/'.venv/bin/terraform'),'fmt',str(configuration/'tests/independent.tftest.hcl')],check=True,stdout=subprocess.DEVNULL)
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(cli),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
commands=[]
for command in [['init','-backend=false','-input=false','-lockfile=readonly','-no-color'],['fmt','-check','-recursive'],['validate','-json'],['providers','schema','-json'],['test','-no-color']]:
 with(out/(command[0]+'.log')).open('wb')as log:result=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(configuration),*command],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 commands.append({'command':command,'exitCode':result.returncode})
 if result.returncode:break
assert all(hashlib.sha256((package/'infra'/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
assert all(hashlib.sha256((configuration/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
receipt={'passed':all(c['exitCode']==0 for c in commands),'commands':commands,'sourcesUnchanged':True,'sourceHashes':before,'oracleSha256':hashlib.sha256((configuration/'tests/independent.tftest.hcl').read_bytes()).hexdigest(),'cloudOperations':False,'boundary':'Actual cached AzureRM/AzureAD schemas and independent mock plans on unchanged original Azure ticket source; no account/state/apply or managed-service/deployment acceptance.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'commands':commands}));raise SystemExit(0 if receipt['passed']else 1)
