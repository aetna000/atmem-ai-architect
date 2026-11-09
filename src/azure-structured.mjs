import {pythonContainer} from './python-container.mjs';
import sources from './runtime/azure-sources.json' with {type:'json'};
import lock from './runtime/azure-python-lock.json' with {type:'json'};
import testLock from './runtime/azure-test-lock.json' with {type:'json'};
import base from './runtime/python-container-lock.json' with {type:'json'};
import {STRUCTURED_WEB_HTML,STRUCTURED_WEB_CSS,STRUCTURED_WEB_JS} from './structured-web.mjs';
import {structuredContract} from './structured-contract.mjs';
import {existingDeployment} from './deployment-ownership.mjs';
import {existingReferenceFiles} from './existing-references.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';

export function azureStructuredPlan(project,rows){
 const entries=[];
 for(const node of project.nodes){
  if(node.data.provider!=='azure'||node.data.implementation!=='azure-structured-app'||node.data.service!=='Azure App Service'||existingDeployment(node))continue;
  const contract=structuredContract(node.data.config?.outputContract);
  if(!contract)continue;
  const maxInput=node.data.config?.maxInputBytes??20000,maxTokens=node.data.config?.maxOutputTokens??1024;
  if(!Number.isInteger(maxInput)||maxInput<1||maxInput>20000||!Number.isInteger(maxTokens)||maxTokens<32||maxTokens>4096)throw Error('Azure structured application limits must be 1–20000 input bytes and 32–4096 output tokens.');
  entries.push({row:rows.find(r=>r.id===node.id),contract,maxInput,maxTokens});
 }
 const ids=new Set(entries.map(e=>e.row.id));
 const browsers=new Set(project.nodes.filter(n=>existingDeployment(n)&&n.data.provider==='tools'&&n.data.binding==='web-browser').map(n=>n.id));
 const edges=project.edges.filter(e=>e.integration==='browser-https'&&browsers.has(e.source)&&ids.has(e.target));
 return {entries,componentIds:[...ids],edgeIds:edges.map(e=>e.id)};
}

const v=n=>'${var.'+n+'}',ref=(type,n,key)=>'${'+type+'.'+n+'.'+key+'}';
export function azureStructuredTerraform(project,plan,environment='staging'){
 const entries=plan.azureStructuredPlan.entries;
 if(!entries.length)throw Error('No Azure structured application composition.');
 const variable={review_approved:{type:'bool',default:false,description:'Approve only after reviewing the emitted code, destination, identity, policy, costs and plan.'}};
 const examples={review_approved:false},resource={},output={},files={},tests=[];
 const input=(name,description,example,pattern)=>{
  variable[name]={type:'string',nullable:false,description,validation:{condition:pattern?'${can(regex('+JSON.stringify(pattern)+', var.'+name+'))}':'${length(trimspace(var.'+name+')) > 0}',error_message:'Supply the reviewed '+name+' value.'}};
  examples[name]=example;return v(name);
 };
 const uuid='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';
 const subscription=input('subscription_id','Expected destination Azure subscription. Terraform uses the operator credential chain.','11111111-1111-1111-1111-111111111111',uuid);
 const tenant=input('tenant_id','Expected company Microsoft Entra tenant. Both providers are bound to this tenant.','22222222-2222-2222-2222-222222222222',uuid);
 const rg=input('resource_group_name','Existing reviewed destination resource group. This module does not import or recreate it.','reviewed-application-rg','^[A-Za-z0-9_.()-]{1,90}$');
 const registry=input('registry_name','Existing Azure Container Registry name, with standard RBAC registry permission mode. No registry is recreated.','reviewedregistry','^[a-z0-9]{5,50}$');
 const registryRg=input('registry_resource_group_name','Existing registry resource group in the selected subscription.','reviewed-registry-rg','^[A-Za-z0-9_.()-]{1,90}$');
 const registryId='/subscriptions/'+subscription+'/resourceGroups/'+registryRg+'/providers/Microsoft.ContainerRegistry/registries/'+registry;
 const registryUrl='https://'+registry+'.azurecr.io';
 const add=(type,name,body)=>((resource[type]||={})[name]={...body,depends_on:['terraform_data.review_gate',...(body.depends_on||[])]});
 const gaps=[...plan.gapDetails.map(g=>g.id),...(environment==='production'?['production-state-backup-and-operating-review-required']:[])];
 resource.terraform_data={review_gate:{input:{design_revision:project.revision,environment},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'Resolve required implementation work and review the exact destination and emitted package.'}]}}};
 for(const {row,contract,maxInput,maxTokens} of entries){
  const n=row.address;
  const name=input(n+'_name','Unique application name. This composition includes API, browser, Entra registrations and a regional Azure OpenAI deployment.','reviewed-app','^[a-z][a-z0-9-]{4,28}[a-z0-9]$');
  const location=input(n+'_location','Reviewed application/model region. Regional Standard model availability, version and quota must be verified.','australiaeast','^[a-z][a-z0-9]{2,39}$');
  if(/^[a-z][a-z0-9]{2,39}$/.test(row.region)){variable[n+'_location'].default=row.region;examples[n+'_location']=row.region;}
  const repository=input(n+'_repository','Existing registry repository to which the generated, tested application image will be pushed.','architect/app','^[a-z0-9]+(?:[._/-][a-z0-9]+)*$');
  const digest=input(n+'_image_digest','SHA-256 digest from building this emitted source, not a placeholder image. Use the documented two-phase build/push then Terraform plan.','sha256:'+'0'.repeat(64),'^sha256:[0-9a-f]{64}$');
  const modelName=input(n+'_model_name','Reviewed Azure OpenAI chat model; verify regional Standard availability and API compatibility. No model or price is invented.','REVIEW_MODEL');
  const modelVersion=input(n+'_model_version','Explicit supported model version. Review lifecycle and quota in the destination before planning.','REVIEW_VERSION');
  const group=input(n+'_access_group_object_id','Existing Entra security group allowed to use this API. Group assignment requires Entra P1/P2; no users or groups are created.','33333333-3333-3333-3333-333333333333',uuid);
  const tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:n};
  add('azurerm_user_assigned_identity',n,{name:name+'-runtime',location,resource_group_name:rg,tags});
  add('azurerm_service_plan',n,{name:name+'-plan',location,resource_group_name:rg,os_type:'Linux',sku_name:'B1',worker_count:1,tags});
  add('azurerm_cognitive_account',n,{name:name+'-ai',location,resource_group_name:rg,kind:'OpenAI',sku_name:'S0',custom_subdomain_name:name+'-ai',local_auth_enabled:false,public_network_access_enabled:true,tags,lifecycle:{prevent_destroy:true}});
  add('azurerm_cognitive_deployment',n,{name:'structured-operation',cognitive_account_id:ref('azurerm_cognitive_account',n,'id'),version_upgrade_option:'NoAutoUpgrade',model:{format:'OpenAI',name:modelName,version:modelVersion},sku:{name:'Standard',capacity:1}});
  const principal=ref('azurerm_user_assigned_identity',n,'principal_id');
  add('azurerm_role_assignment',n,{scope:ref('azurerm_cognitive_account',n,'id'),role_definition_name:'Cognitive Services OpenAI User',principal_id:principal});
  add('azurerm_role_assignment',n+'_policy',{scope:ref('azurerm_cognitive_account',n,'id'),role_definition_name:'Reader',principal_id:principal});
  add('azurerm_role_assignment',n+'_pull',{scope:registryId,role_definition_name:'AcrPull',principal_id:principal});
  const registration={display_name:name,sign_in_audience:'AzureADMyOrg',requested_access_token_version:2,implicit_access_token_issuance_enabled:false,implicit_id_token_issuance_enabled:false};
  add('azuread_application_registration',n,registration);
  add('azuread_application_registration',n+'_spa',{...registration,display_name:name+'-browser'});
  const apiId=ref('azuread_application_registration',n,'id'),apiClient=ref('azuread_application_registration',n,'client_id'),spaId=ref('azuread_application_registration',n+'_spa','id'),spaClient=ref('azuread_application_registration',n+'_spa','client_id');
  const role='${uuidv5("dns", format("%s:%s:workspace-user", var.tenant_id, var.'+n+'_name))}';
  const scope='${uuidv5("dns", format("%s:%s:access-as-user", var.tenant_id, var.'+n+'_name))}';
  add('azuread_application_identifier_uri',n,{application_id:apiId,identifier_uri:'api://'+apiClient});
  add('azuread_application_permission_scope',n,{application_id:apiId,scope_id:scope,value:'access_as_user',type:'Admin',admin_consent_display_name:'Use the structured AI workspace',admin_consent_description:'Submit input for a bounded AI operation as the signed-in user.'});
  add('azuread_application_app_role',n,{application_id:apiId,role_id:role,allowed_member_types:['User'],display_name:'Workspace user',description:'Use the structured AI operation.',value:'WorkspaceUser'});
  add('azuread_service_principal',n,{client_id:apiClient,app_role_assignment_required:true,depends_on:['azuread_application_app_role.'+n]});
  add('azuread_service_principal',n+'_spa',{client_id:spaClient,app_role_assignment_required:false});
  add('azuread_app_role_assignment',n,{app_role_id:role,principal_object_id:group,resource_object_id:ref('azuread_service_principal',n,'object_id')});
  add('azuread_application_api_access',n,{application_id:spaId,api_client_id:apiClient,scope_ids:[scope],depends_on:['azuread_application_permission_scope.'+n]});
  add('azuread_application_pre_authorized',n,{application_id:apiId,authorized_client_id:spaClient,permission_ids:[scope],depends_on:['azuread_application_permission_scope.'+n]});
  add('azurerm_linux_web_app',n,{name,location,resource_group_name:rg,service_plan_id:ref('azurerm_service_plan',n,'id'),https_only:true,ftp_publish_basic_authentication_enabled:false,webdeploy_publish_basic_authentication_enabled:false,identity:{type:'UserAssigned',identity_ids:[ref('azurerm_user_assigned_identity',n,'id')]},site_config:{always_on:true,minimum_tls_version:'1.2',scm_minimum_tls_version:'1.2',ftps_state:'Disabled',http2_enabled:true,remote_debugging_enabled:false,health_check_path:'/healthz',container_registry_use_managed_identity:true,container_registry_managed_identity_client_id:ref('azurerm_user_assigned_identity',n,'client_id'),application_stack:{docker_registry_url:registryUrl,docker_image_name:repository+'@'+digest}},app_settings:{WEBSITES_PORT:'8080',TENANT_ID:tenant,API_CLIENT_ID:apiClient,SPA_CLIENT_ID:spaClient,MANAGED_IDENTITY_CLIENT_ID:ref('azurerm_user_assigned_identity',n,'client_id'),MODEL_RESOURCE_ID:ref('azurerm_cognitive_account',n,'id'),MODEL_ENDPOINT:ref('azurerm_cognitive_account',n,'endpoint'),MODEL_DEPLOYMENT:ref('azurerm_cognitive_deployment',n,'name'),MAX_INPUT_BYTES:String(maxInput),MAX_OUTPUT_TOKENS:String(maxTokens),OUTPUT_CONTRACT_BASE64:btoa(unescape(encodeURIComponent(JSON.stringify(contract))))},tags,depends_on:['azurerm_role_assignment.'+n,'azurerm_role_assignment.'+n+'_policy','azurerm_role_assignment.'+n+'_pull','azuread_application_pre_authorized.'+n,'azuread_app_role_assignment.'+n]});
  add('azuread_application_redirect_uris',n,{application_id:spaId,type:'SPA',redirect_uris:['https://'+ref('azurerm_linux_web_app',n,'default_hostname')+'/']});
  output[n+'_url']={value:'https://'+ref('azurerm_linux_web_app',n,'default_hostname')+'/'};
  output[n+'_model_resource_id']={value:ref('azurerm_cognitive_account',n,'id')};
  const folder='applications/'+n+'/';
  for(const [path,body] of Object.entries(sources))files[folder+path]=body;
  files[folder+'web/index.html']=STRUCTURED_WEB_HTML;
  files[folder+'web/app.css']=STRUCTURED_WEB_CSS;
  files[folder+'web/app.js']=STRUCTURED_WEB_JS;
  files[folder+'output-contract.json']=JSON.stringify(contract,null,2);
  files[folder+'requirements.lock']=lock.requirements;
  files[folder+'test-requirements.lock']=testLock.requirements;
  files[folder+'test-dependency-sources.json']=JSON.stringify(testLock.sources,null,2);
  files[folder+'dependency-sources.json']=JSON.stringify(lock.sources,null,2);
  files[folder+'container-base.json']=JSON.stringify(base,null,2);
  files[folder+'Dockerfile']=pythonContainer('azure_structured',['azure_structured.py','structured_output.py','structured_http.py']);
  files[folder+'.dockerignore']='*\n!requirements.lock\n!output-contract.json\n!azure_structured.py\n!structured_output.py\n!structured_http.py\n!web/\n!web/*\n';
  files[folder+'BUILD.md']=`# Generated Azure application\n\nThis source implements the browser, delegated Entra API authorization and bounded model operation. It is not a supplied-image placeholder. From this directory, create an isolated environment with python3.13 -m venv .venv, run .venv/bin/python -m pip install --only-binary=:all: --require-hashes -r test-requirements.lock, then .venv/bin/python azure_acceptance.py -v. Test dependencies have a separate hash-locked file and source receipts. Tests use cryptographic keys and scripted network boundaries; they do not access Azure.\n\nBuild on a clean Docker host: docker build --platform linux/amd64 --pull -t REVIEWED_REGISTRY.azurecr.io/REVIEWED_REPOSITORY:REVIEWED_BUILD .\n\nInspect and scan the image, run container startup and acceptance checks, then, with authorization, authenticate to the existing ACR and push it. Record the registry digest and supply it as ${n}_image_digest. The Terraform configuration uses managed-identity pull and never builds/pushes images or executes a provisioner. Building and publishing an image is separate from running Terraform. The base image and all Python wheels are hash pinned; record exact source/image hashes. Update deliberately and rerun tests/scans.\n\nThe test-requirements.lock file adds pinned httpx/HTTP transport tooling for FastAPI TestClient; those development tools are not packaged into the image. Test fixture config lives in azure_acceptance.py; never use fixture values as deployment credentials or production configuration.\n`;
  tests.push(`run "${n}_security" {\n command = plan\n assert {\n condition = azurerm_linux_web_app.${n}.https_only && !azurerm_linux_web_app.${n}.ftp_publish_basic_authentication_enabled && !azurerm_linux_web_app.${n}.webdeploy_publish_basic_authentication_enabled && !azurerm_cognitive_account.${n}.local_auth_enabled\n error_message = "TLS and managed identity are required; basic publishing and model keys are disabled."\n }\n assert {\n condition = azurerm_cognitive_deployment.${n}.sku[0].name == "Standard" && azurerm_cognitive_deployment.${n}.version_upgrade_option == "NoAutoUpgrade"\n error_message = "Do not silently select a global deployment or model upgrade."\n }\n assert {\n condition = azuread_service_principal.${n}.app_role_assignment_required && azuread_application_registration.${n}.requested_access_token_version == 2\n error_message = "Tenant-specific v2 access and explicit group assignment are required."\n }\n}\nrun "${n}_reject_mutable_image" {\n command = plan\n variables { ${n}_image_digest = "latest" }\n expect_failures = [var.${n}_image_digest]\n}`);
 }
 const config={terraform:{required_version:'>= 1.7.0, < 2.0.0',required_providers:{azurerm:{source:'hashicorp/azurerm',version:'4.81.0'},azuread:{source:'hashicorp/azuread',version:'3.10.0'}}},provider:{azurerm:{features:{},subscription_id:subscription,tenant_id:tenant,resource_provider_registrations:'none'},azuread:{tenant_id:tenant}},variable,locals:{unfinished_work:gaps},resource,output};
 const values=Object.entries({...examples,review_approved:true}).map(([key,val])=>key+' = '+JSON.stringify(val)).join('\n');
 return {...files,...existingReferenceFiles(project),'.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS.azure+'\n'+CLOUD_PROVIDER_LOCKS.azuread,'.gitignore':'.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n!deployment.tfvars.json.example\n.venv/\n__pycache__/\n','main.tf.json':JSON.stringify(config,null,2),'resource-schedule.json':JSON.stringify(plan,null,2),'deployment.tfvars.json.example':JSON.stringify(examples,null,2),'tests/azure-structured.tftest.hcl':`mock_provider "azurerm" {}\nmock_provider "azuread" {}\nvariables {\n${values}\n}\n${tests.join('\n')}\nrun "unapproved_blocked" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n`,'README.md':AZURE_STRUCTURED_GUIDE};
}

export const AZURE_STRUCTURED_GUIDE=`# Azure structured AI application

Each explicitly selected azure-structured-app block is a composed application module: Linux App Service, browser, API, user-assigned runtime identity, regional Azure OpenAI account/deployment, two Entra app registrations, an API scope/role, and an assignment of an existing company group. It does not create users/groups, import existing applications or implement arbitrary other blocks. See resource-schedule.json for unresolved scope. Public TLS endpoints use identity enforcement; private networking is not implemented by this module.

The emitted Python 3.13 application verifies signed RS256 Entra v2 access tokens for the exact tenant, API audience, browser client, delegated scope and assigned WorkspaceUser role. ID tokens, app-only tokens and forwarded identity headers grant no API access. Keys are fetched from the fixed tenant endpoint with bounded retrieval and rotation caching. Bearer tokens authorize until expiry: group removal, disabling a user and logout do not immediately revoke an already issued token. Tenant Conditional Access/MFA and any continuous-revocation requirement require destination policy/engineering and real tests. Entra P1/P2 is needed for group assignments. Provisioning Entra registrations/role assignments needs separately reviewed administrator/Graph permissions; the runtime receives none of those permissions.

Runtime identity receives model inference access and account-scoped Reader for policy checks, plus AcrPull on the exact existing registry. These are not subscription-wide Owner grants. Registry mode must support AcrPull and accept ARM audience tokens for managed-identity pulls; an ABAC-enabled or network-protected registry needs a different reviewed assignment/network integration. No static credential, model key or client secret is emitted. Protect Terraform state: providers may retain sensitive service attributes even when no output exposes a key.

Input/results are not persisted by the app. Before inference, a read-only ARM check requires the exact model account and ContentLogging=false capability. This capability requires approved modified abuse monitoring; the app cannot self-approve it. Missing approval, policy outage or unknown state blocks inference with a clear setup error, without sending the user input to the model. It never modifies account-wide policy. Review provider processing, monitoring, residency and account terms separately; Standard regional model deployment alone does not prove whole-system residency. Model/account availability, compatible model/version, quotas, prices and this policy approval need authorized destination checks. No availability or privacy approval is invented.

Build/test the emitted applications first using each applications/*/BUILD.md. Build and push to an existing reviewed ACR, retain exact source/image digests, then supply deployment inputs. No Terraform provisioners or bootstrap cloud actions run automatically. Register Microsoft.Web, Microsoft.CognitiveServices and Microsoft.ManagedIdentity separately under authorized subscription control; automatic registration is disabled. Both providers are pinned to the expected tenant/subscription and use the operator credential chain.

The API requests strict JSON Schema output with the documented response_format contract and independently validates the returned JSON. Select a regional deployment/version that supports structured outputs; unsupported model/configuration errors fail closed, without silently switching model or removing the schema. String length limits remain enforced by the application because the provider schema subset does not support maxLength.

Use terraform init -backend=false, terraform validate and terraform test for provider schemas and mock configuration checks. Review actual destination inputs and an authorized plan separately. Production is blocked until state, backup and operations are reviewed. App Service B1 and a single process are an initial bounded deployment, not a high-availability SLA. Per-process concurrency/output limits and model quota bound traffic; they are not an invoice cap. No request bodies, tokens or model text are logged by the application; review platform-level logging separately.

The model returns flat schema-checked fields with a human-review marker. No tool/action is executed. Output validation does not prove factual or classification accuracy. Run representative model-quality tests, real sign-in/role/expiry tests, image startup/scan, policy checks and an authorized account plan before deployment. This export itself proves no deployment.

References:
- https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps
- https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/abuse-monitoring
- https://learn.microsoft.com/en-us/rest/api/aifoundry/azureopenai/chat
- https://registry.terraform.io/providers/hashicorp/azurerm/4.81.0/docs/resources/linux_web_app
- https://registry.terraform.io/providers/hashicorp/azuread/3.10.0/docs
`;
