"""Independent cached-provider schema/mock plans on unchanged generated Terraform."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];package=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();assert not out.exists();out.mkdir();configuration=out/'configuration';configuration.mkdir()
files={p.name:p.read_bytes()for p in (package/'infra').iterdir()if p.is_file()};before={name:hashlib.sha256(value).hexdigest()for name,value in files.items()}
for name,value in files.items():(configuration/name).write_bytes(value)
(configuration/'tests').mkdir();mirror=(ROOT/'.local/provider-cache').resolve();cli=out/'mirror.tfrc';cli.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(mirror))+' } }\ndisable_checkpoint = true\n')
variables={k:'30000000-0000-4000-8000-'+str(i+1).zfill(12) for i,k in enumerate(['subscription_id','tenant_id','api_application_id','authorized_client_id','museum_account_id','deployment_principal_id','database_admin_object_id'])}
variables.update(database_admin_name='Independent synthetic DBA',prefix='indepfixture',image_digest='sha256:'+'1'*64,catalogue_endpoint='https://catalogue.independent.invalid/labels',catalogue_scope='labels.publish',catalogue_token='synthetic-not-a-real-secret')
text='mock_provider "azurerm" { override_during = plan }\noverride_resource {\n target = azurerm_container_app_environment.main\n override_during = plan\n values = { id = "/subscriptions/30000000-0000-4000-8000-000000000001/resourceGroups/indepfixture/providers/Microsoft.App/managedEnvironments/indepfixture-apps", default_domain = "synthetic.internal", static_ip_address = "10.80.0.10" }\n}\nvariables {\n'+''.join(' '+k+' = '+json.dumps(v)+'\n'for k,v in variables.items())+'}\n'
def run(name,checks,values=None,failures=None):
 global text
 text+='run '+json.dumps(name)+' {\n command = plan\n'
 if values:text+=' variables {\n'+''.join(' '+k+' = '+json.dumps(v)+'\n'for k,v in values.items())+' }\n'
 if failures:text+=' expect_failures = ['+', '.join(failures)+']\n'
 for check,message in checks:text+=' assert {\n condition = '+check+'\n error_message = '+json.dumps(message)+'\n }\n'
 text+='}\n'
run('runtime_off_before_bootstrap',[
 ('length(azurerm_container_app.api) == 0 && length(azurerm_container_app.worker) == 0','Default must create no application before bootstrap'),
 ('azurerm_resource_group.main.location == "australiaeast" && azurerm_postgresql_flexible_server.main.version == "17"','Preserve provider region and SQL target'),
 ('!azurerm_postgresql_flexible_server.main.public_network_access_enabled && !azurerm_postgresql_flexible_server.main.authentication[0].password_auth_enabled && azurerm_postgresql_flexible_server.main.authentication[0].active_directory_auth_enabled','Private native workload SQL auth'),
 ('local.config.identitySettings.TENANT_ID == var.tenant_id && local.config.identitySettings.API_CLIENT_ID == var.api_application_id && local.config.identitySettings.SPA_CLIENT_ID == var.authorized_client_id','Existing Entra references unchanged'),
 ('azurerm_container_app_environment.main.internal_load_balancer_enabled && !azurerm_container_registry.main.public_network_access_enabled && !azurerm_key_vault.main.public_network_access_enabled','Private hosting/image/secrets'),
 ('azurerm_postgresql_flexible_server.main.backup_retention_days == 35 && azurerm_key_vault.main.purge_protection_enabled','Backup and secret retention')])
a='azurerm_container_app.api[0].template[0].container[0]';w='azurerm_container_app.worker[0].template[0].container[0]'
aenv='{for e in '+a+'.env : e.name => e.value}';wenv='{for e in '+w+'.env : e.name => e.value}'
run('explicit_runtime_composition',[
 ('length(azurerm_container_app.api) == 1 && length(azurerm_container_app.worker) == 1','Distinct deployable API and worker'),
 (w+'.command == tolist(["python", "worker.py"]) && '+a+'.command == tolist(["python", "-m", "uvicorn", "api:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080"])','Actual source entrypoints'),
 (aenv+'.DATABASE_USER == "labels_api" && '+wenv+'.DATABASE_USER == "labels_worker"','Separate SQL logins wired to application'),
 ('jsondecode('+aenv+'.LABEL_CONFIG_JSON).catalogueEndpoint == var.catalogue_endpoint && jsondecode('+wenv+'.LABEL_CONFIG_JSON).identitySettings.API_CLIENT_ID == var.api_application_id','Runtime config preserves destination and existing identity'),
 ('length(azurerm_container_app.api[0].secret) == 0 && length(azurerm_container_app.worker[0].secret) == 1','Only worker receives outbound secret'),
 ('one([for e in '+w+'.env : e if e.name == "CATALOGUE_TOKEN"]).secret_name == "catalogue-token" && alltrue([for e in '+a+'.env : e.name != "CATALOGUE_TOKEN"])','Worker-only secret environment reference'),
 ('length(azurerm_container_app.worker[0].ingress) == 0 && azurerm_container_app.worker[0].template[0].min_replicas == 1','Asynchronous private always-running worker'),
 (a+'.readiness_probe[0].path == "/readyz" && '+a+'.liveness_probe[0].path == "/healthz"','Separate actual readiness and health paths'),
 ('azurerm_subnet.database.address_prefixes[0] == "10.80.2.0/24" && azurerm_subnet.apps.address_prefixes[0] == "10.80.0.0/23" && azurerm_subnet.endpoints.address_prefixes[0] == "10.80.3.0/24"','Disjoint default application/database/endpoint subnets')],{'enable_apps':True})
run('deny_mutable_image',[],{'image_digest':'latest'},['var.image_digest'])
run('deny_http_destination',[],{'catalogue_endpoint':'http://catalogue.independent.invalid'},['var.catalogue_endpoint'])
run('deny_foreign_environment',[],{'environment':'other'},['var.environment'])
(configuration/'tests/independent.tftest.hcl').write_text(text)
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(cli),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
commands=[]
for command in [['init','-backend=false','-input=false','-lockfile=readonly','-no-color'],['validate','-json'],['test','-no-color']]:
 with(out/(command[0]+'.log')).open('wb')as log:result=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(configuration),*command],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 commands.append({'command':command,'exitCode':result.returncode})
 if result.returncode:break
assert all(hashlib.sha256((package/'infra'/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
assert all(hashlib.sha256((configuration/name).read_bytes()).hexdigest()==digest for name,digest in before.items())
receipt={'passed':all(c['exitCode']==0 for c in commands),'commands':commands,'sourcesUnchanged':True,'sourceHashes':before,'oracleSha256':hashlib.sha256(text.encode()).hexdigest(),'cloudOperations':False,'boundary':'Actual cached AzureRM schema and independent mock plans on unchanged source; no account/state/apply, managed identity/network behavior or whole-project acceptance.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':receipt['passed'],'commands':commands}));raise SystemExit(0 if receipt['passed']else 1)
