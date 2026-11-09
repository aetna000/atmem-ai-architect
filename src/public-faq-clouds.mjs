import {azurePlanMocks} from './azure-plan-mocks.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';
export {awsPublicFaqTerraform} from './aws-public-faq.mjs';
import {builder,v,ref,UUID} from './public-faq-builder.mjs';

export function azurePublicFaqTerraform(project,plan,environment='staging'){
 const b=builder(project,plan,environment,'azure'),{input,add}=b;
 const subscription=input('subscription_id','Expected destination Azure subscription; operator credential chain only.','11111111-1111-1111-1111-111111111111',UUID);
 const tenant=input('tenant_id','Expected destination tenant. Existing editor identity is preserved.','22222222-2222-2222-2222-222222222222',UUID);
 const rg=input('resource_group_name','Existing reviewed resource group; not recreated or imported.','reviewed-applications','^[A-Za-z0-9_.()-]{1,90}$');
 const registry=input('registry_name','Existing RBAC-mode ACR that accepts the ARM audience for managed identity.','reviewedregistry','^[a-z0-9]{5,50}$');
 const registryRg=input('registry_resource_group_name','Existing registry resource group in this subscription.','reviewed-registry-rg','^[A-Za-z0-9_.()-]{1,90}$');
 b.data.azurerm_client_config={destination:{}};
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${data.azurerm_client_config.destination.subscription_id == var.subscription_id && data.azurerm_client_config.destination.tenant_id == var.tenant_id}',error_message:'Operator identity must match the reviewed tenant and subscription.'});
 const registryId='/subscriptions/'+subscription+'/resourceGroups/'+registryRg+'/providers/Microsoft.ContainerRegistry/registries/'+registry;
 for(const {row}of plan.publicFaqPlan.entries){
  const n=row.address,name=input(n+'_name','Unique public application name; internal managed services belong to this composition.','reviewed-public-help','^[a-z][a-z0-9-]{3,18}[a-z0-9]$');
  const region=input(n+'_region','Reviewed application, storage and Regional Standard model location. Verify actual model/version/quotas and processing geography.','australiaeast','^[a-z][a-z0-9]{2,39}$');
  if(/^[a-z][a-z0-9]{2,39}$/.test(row.region)){b.variable[n+'_region'].default=row.region;b.examples[n+'_region']=row.region;}
  const repository=input(n+'_repository','Build/publish path for this emitted application in the existing registry.','architect/public-help','^[a-z0-9]+(?:[._/-][a-z0-9]+)*$');
  const digest=input(n+'_image_digest','Exact built, scanned, tested and authorized-published image digest.','sha256:'+'0'.repeat(64),'^sha256:[0-9a-f]{64}$');
  const model=input(n+'_model_name','Reviewed regional model supporting strict JSON Schema output; no availability or price is invented.','REVIEW_MODEL');
  const version=input(n+'_model_version','Exact supported model version; verify lifecycle and Standard regional availability.','REVIEW_VERSION');
  const editor=input(n+'_editor_group_object_id','Existing Entra editor security-group object ID; no group/users are created. It receives only public-container data access.','33333333-3333-3333-3333-333333333333',UUID);
  const tags={ManagedBy:'AtMem AI Architect',Environment:environment,Component:n};
  add('azurerm_user_assigned_identity',n,{name:name+'-runtime',location:region,resource_group_name:rg,tags});
  add('azurerm_service_plan',n,{name:name+'-plan',location:region,resource_group_name:rg,os_type:'Linux',sku_name:'B1',worker_count:1,tags});
  add('azurerm_cognitive_account',n,{name:name+'-ai',location:region,resource_group_name:rg,kind:'OpenAI',sku_name:'S0',custom_subdomain_name:name+'-ai',local_auth_enabled:false,public_network_access_enabled:true,tags,lifecycle:{prevent_destroy:true}});
  add('azurerm_cognitive_deployment',n,{name:'public-faq',cognitive_account_id:ref('azurerm_cognitive_account',n,'id'),version_upgrade_option:'NoAutoUpgrade',model:{format:'OpenAI',name:model,version},sku:{name:'Standard',capacity:1}});
  const storage='${format("faq%s", substr(sha256(format("%s:%s", var.subscription_id, var.'+n+'_name)), 0, 20))}';
  add('azurerm_storage_account',n,{name:storage,location:region,resource_group_name:rg,account_tier:'Standard',account_replication_type:'LRS',https_traffic_only_enabled:true,min_tls_version:'TLS1_2',allow_nested_items_to_be_public:false,shared_access_key_enabled:false,default_to_oauth_authentication:true,public_network_access_enabled:true,blob_properties:{versioning_enabled:true,delete_retention_policy:{days:7},container_delete_retention_policy:{days:7}},tags,lifecycle:{prevent_destroy:true}});
  add('azurerm_storage_container',n,{name:'public-catalog',storage_account_id:ref('azurerm_storage_account',n,'id'),container_access_type:'private',lifecycle:{prevent_destroy:true}});
  const principal=ref('azurerm_user_assigned_identity',n,'principal_id');
  for(const [suffix,scope,role]of [['',ref('azurerm_cognitive_account',n,'id'),'Cognitive Services OpenAI User'],['_policy',ref('azurerm_cognitive_account',n,'id'),'Reader'],['_pull',registryId,'AcrPull'],['_catalog',ref('azurerm_storage_container',n,'id'),'Storage Blob Data Reader']])add('azurerm_role_assignment',n+suffix,{scope,role_definition_name:role,principal_id:principal,principal_type:'ServicePrincipal',skip_service_principal_aad_check:true});
  add('azurerm_role_assignment',n+'_editor',{scope:ref('azurerm_storage_container',n,'id'),role_definition_name:'Storage Blob Data Contributor',principal_id:editor,principal_type:'Group'});
  add('azurerm_linux_web_app',n,{name,location:region,resource_group_name:rg,service_plan_id:ref('azurerm_service_plan',n,'id'),https_only:true,ftp_publish_basic_authentication_enabled:false,webdeploy_publish_basic_authentication_enabled:false,identity:{type:'UserAssigned',identity_ids:[ref('azurerm_user_assigned_identity',n,'id')]},site_config:{always_on:true,minimum_tls_version:'1.2',scm_minimum_tls_version:'1.2',ftps_state:'Disabled',http2_enabled:true,remote_debugging_enabled:false,health_check_path:'/healthz',health_check_eviction_time_in_min:2,container_registry_use_managed_identity:true,container_registry_managed_identity_client_id:ref('azurerm_user_assigned_identity',n,'client_id'),application_stack:{docker_registry_url:'https://'+registry+'.azurecr.io',docker_image_name:repository+'@'+digest}},app_settings:{WEBSITES_PORT:'8080',MANAGED_IDENTITY_CLIENT_ID:ref('azurerm_user_assigned_identity',n,'client_id'),MODEL_RESOURCE_ID:ref('azurerm_cognitive_account',n,'id'),MODEL_ENDPOINT:ref('azurerm_cognitive_account',n,'endpoint'),MODEL_DEPLOYMENT:ref('azurerm_cognitive_deployment',n,'name'),MAX_OUTPUT_TOKENS:'1024',CATALOG_ACCOUNT:ref('azurerm_storage_account',n,'name'),CATALOG_CONTAINER:ref('azurerm_storage_container',n,'name')},tags,depends_on:['azurerm_role_assignment.'+n,'azurerm_role_assignment.'+n+'_policy','azurerm_role_assignment.'+n+'_pull','azurerm_role_assignment.'+n+'_catalog']});
  b.output[n+'_url']={value:'https://'+ref('azurerm_linux_web_app',n,'default_hostname')+'/'};
  b.output[n+'_catalog']={value:{storage_account:ref('azurerm_storage_account',n,'name'),container:ref('azurerm_storage_container',n,'name'),region}};
  b.source(row);
  b.assertions.push(`run "${n}_public_boundary" {\n command = plan\n assert {\n condition = azurerm_storage_container.${n}.container_access_type == "private" && !azurerm_storage_account.${n}.shared_access_key_enabled && !azurerm_storage_account.${n}.allow_nested_items_to_be_public\n error_message = "Public answers must not make the object store public or enable storage keys."\n }\n assert {\n condition = azurerm_role_assignment.${n}_catalog.role_definition_name == "Storage Blob Data Reader" && azurerm_role_assignment.${n}_editor.role_definition_name == "Storage Blob Data Contributor" && azurerm_role_assignment.${n}_catalog.principal_id != azurerm_role_assignment.${n}_editor.principal_id\n error_message = "Runtime read and authorized editor write identities must remain separate."\n }\n assert {\n condition = azurerm_linux_web_app.${n}.https_only && !azurerm_cognitive_account.${n}.local_auth_enabled\n error_message = "TLS and workload identity are required."\n }\n}\nrun "${n}_mutable_image_blocked" {\n command = plan\n variables { ${n}_image_digest = "latest" }\n expect_failures = [var.${n}_image_digest]\n}`);
 }
 const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{azurerm:{source:'hashicorp/azurerm',version:'4.81.0'}}},provider:{azurerm:{subscription_id:subscription,tenant_id:tenant,features:{},storage_use_azuread:true}}};
 return b.finish(config,CLOUD_PROVIDER_LOCKS.azure,azurePlanMocks({subscription:b.examples.subscription_id,tenant:b.examples.tenant_id,resourceGroup:b.examples.resource_group_name,addresses:plan.publicFaqPlan.entries.map(e=>e.row.address)}),AZURE_PUBLIC_FAQ_GUIDE);
}

export const AZURE_PUBLIC_FAQ_GUIDE=`# Azure public-only FAQ composition

The generated Python browser/API is intentionally anonymous. Its dedicated managed
identity can read only this private public-article container and invoke/read policy
on its generated regional model account. A separate existing Entra editor group
receives container-scoped data contributor access. No application HTTP endpoint
edits articles. No users/groups, existing resource group or ACR are recreated.
This is not a private enterprise knowledge assistant or existing-SSO integration.

Shared storage keys and anonymous blob access are disabled; the Azure provider
uses Entra for storage access. App Service basic publishing/debug/FTP are disabled;
the application uses managed identity for image pulls. Verify the existing registry
uses standard RBAC and accepts the ARM audience. No registry credential or model
key is exported. Public TLS endpoints use IAM/RBAC; private networking is not
implemented. Review inherited permissions and current tenant/subscription context.

See applications/*/BUILD.md for exact source/test/build and conditional editor CLI
steps. Protect Terraform state and variables. Seed only genuinely public articles
with the authorized editor before admitting traffic; a missing/inaccessible source
does not become an empty catalog or a cached answer. Blob versions and seven-day
soft deletion are recovery features, not an immediate erasure guarantee. Review
recovery and costs. Anonymous access plus concurrency/instance/output limits is
not an invoice cap; approve and test destination abuse controls and budget policy.

Choose a compatible regional Standard structured-output model/version and verify
actual quotas, prices and geography. Runtime requires approved ContentLogging=false
before inference and never writes that account-wide setting. Provider/platform
logging and identity/control-plane processing require separate review. No app
question/answer persistence or content-bearing application logs are implemented.
Real model answer/citation/abstention and latency tests remain required.

Use Terraform 1.17.1+, terraform init -backend=false, terraform validate and
terraform test. These mock checks do not prove real Azure IAM, managed identity,
storage conditionals or model quality. Obtain explicit authorization for registry
publication, cloud access, a real account plan and deployment. Production state,
backup and operating review remain gated; no export proves deployment.
`;

export function gcpPublicFaqTerraform(project,plan,environment='staging'){
 const b=builder(project,plan,environment,'gcp'),{input,add}=b;
 const projectId=input('project_id','Existing reviewed Google project with billing; no project is recreated.','reviewed-project','^[a-z][a-z0-9-]{4,28}[a-z0-9]$');
 const registryLocation=input('registry_location','Location of the existing Artifact Registry Docker repository.','australia-southeast1','^[a-z]+(?:-[a-z]+[0-9])?$');
 const registry=input('registry_repository','Existing Docker repository in this project; preserved.','reviewed-images','^[a-z][a-z0-9-]{1,61}[a-z0-9]$');
 b.data.google_project={destination:{project_id:projectId}};
 for(const [name,service]of Object.entries({run:'run.googleapis.com',model:'aiplatform.googleapis.com',storage:'storage.googleapis.com',registry:'artifactregistry.googleapis.com'}))add('google_project_service','required_'+name,{project:projectId,service,disable_on_destroy:false});
 add('google_project_service_identity','run',{provider:'google-beta',project:projectId,service:'run.googleapis.com',depends_on:['google_project_service.required_run']});
 add('google_artifact_registry_repository_iam_member','image_pull',{project:projectId,location:registryLocation,repository:registry,role:'roles/artifactregistry.reader',member:ref('google_project_service_identity','run','member'),depends_on:['google_project_service.required_registry']});
 const number='${data.google_project.destination.number}';
 for(const {row}of plan.publicFaqPlan.entries){
  const n=row.address,name=input(n+'_name','Unique short Cloud Run/runtime name. The generated deterministic URL is used for this public browser.','reviewed-public-help','^[a-z][a-z0-9-]{3,18}[a-z0-9]$');
  const region=input(n+'_region','Reviewed single-region application, catalog and model location; no global model fallback.','australia-southeast1','^[a-z]+-[a-z]+[0-9]$');
  if(/^[a-z]+-[a-z]+[0-9]$/.test(row.region)){b.variable[n+'_region'].default=row.region;b.examples[n+'_region']=row.region;}
  const repository=input(n+'_image_repository','Path for the emitted image in the existing registry.','architect/public-help','^[a-z0-9]+(?:[._/-][a-z0-9]+)*$');
  const digest=input(n+'_image_digest','Built, scanned, tested and authorized-published emitted image digest.','sha256:'+'0'.repeat(64),'^sha256:[0-9a-f]{64}$');
  const model=input(n+'_model_id','Compatible reviewed regional Gemini model/version with structured JSON output; verify lifecycle, quota, context size and prices.','gemini-reviewed-version','^gemini-[a-z0-9.-]{1,80}$');
  const editor=input(n+'_editor_group','Existing authorized Google editor group email. No users/groups are created.','help-editors@example.test','^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$');
  const review=n+'_policy_review';b.variable[review]={type:'object({ projectId = string, region = string, model = string, abuseLogging = string, approvedBy = string, evidenceSha256 = string, expiresAt = string })',nullable:false,description:'Scoped expiring destination-owner review of actual abuse-monitoring terms/exemption. Operator attestation, not a fabricated approval API; runtime separately reads caching/model logging/sharing settings.'};b.examples[review]={projectId:'reviewed-project',region:b.examples[n+'_region'],model:'gemini-reviewed-version',abuseLogging:'REVIEW_REQUIRED',approvedBy:'REVIEW_REQUIRED',evidenceSha256:'0'.repeat(64),expiresAt:'REPLACE_AFTER_REVIEW'};
  add('google_service_account',n,{project:projectId,account_id:name,display_name:'Public FAQ runtime; no catalog edit permission'});
  const member='serviceAccount:'+ref('google_service_account',n,'email');
  add('google_project_iam_custom_role',n,{project:projectId,role_id:'${replace(var.'+n+'_name, "-", "_")}_model',title:'FAQ model invocation and read-only policy',permissions:['aiplatform.endpoints.predict','aiplatform.cacheConfigs.get','aiplatform.endpoints.fetchPublisherModelConfig'],stage:'GA'});
  add('google_project_iam_member',n,{project:projectId,role:ref('google_project_iam_custom_role',n,'name'),member,depends_on:['google_project_service.required_model']});
  add('google_storage_bucket',n,{project:projectId,name:projectId+'-'+name+'-public',location:region,storage_class:'STANDARD',uniform_bucket_level_access:true,public_access_prevention:'enforced',force_destroy:false,versioning:{enabled:true},soft_delete_policy:{retention_duration_seconds:604800},lifecycle_rule:{action:{type:'Delete'},condition:{days_since_noncurrent_time:7}},lifecycle:{prevent_destroy:true},depends_on:['google_project_service.required_storage']});
  for(const [suffix,permissions]of [['_catalog',['storage.objects.get']],['_editor',['storage.objects.get','storage.objects.create','storage.objects.delete']]])add('google_project_iam_custom_role',n+suffix,{project:projectId,role_id:'${replace(var.'+n+'_name, "-", "_")}'+suffix,title:suffix==='_catalog'?'FAQ current catalog reader':'FAQ conditional catalog editor',permissions,stage:'GA'});
  add('google_storage_bucket_iam_member',n,{bucket:ref('google_storage_bucket',n,'name'),role:ref('google_project_iam_custom_role',n+'_catalog','name'),member});
  add('google_storage_bucket_iam_member',n+'_editor',{bucket:ref('google_storage_bucket',n,'name'),role:ref('google_project_iam_custom_role',n+'_editor','name'),member:'group:'+editor});
  const origin='https://'+name+'-'+number+'.'+region+'.run.app',settings={PROJECT_ID:projectId,REGION:region,MODEL_ID:model,PUBLIC_ORIGIN:origin,MAX_OUTPUT_TOKENS:'1024',CATALOG_BUCKET:ref('google_storage_bucket',n,'name'),POLICY_REVIEW_BASE64:'${base64encode(jsonencode(var.'+review+'))}'};
  add('google_cloud_run_v2_service',n,{project:projectId,name,location:region,deletion_protection:true,ingress:'INGRESS_TRAFFIC_ALL',invoker_iam_disabled:false,iap_enabled:false,labels:{managed_by:'atmem-ai-architect',environment},template:{service_account:ref('google_service_account',n,'email'),timeout:'30s',max_instance_request_concurrency:5,scaling:{min_instance_count:0,max_instance_count:2},containers:{name:'application',image:registryLocation+'-docker.pkg.dev/'+projectId+'/'+registry+'/'+repository+'@'+digest,ports:{container_port:8080},resources:{limits:{cpu:'1',memory:'512Mi'},cpu_idle:true,startup_cpu_boost:true},env:Object.entries(settings).map(([name,value])=>({name,value})),startup_probe:{http_get:{path:'/healthz',port:8080},initial_delay_seconds:0,period_seconds:5,timeout_seconds:2,failure_threshold:12}}},depends_on:['google_project_service.required_run','google_project_service_identity.run','google_artifact_registry_repository_iam_member.image_pull','google_project_iam_member.'+n,'google_storage_bucket_iam_member.'+n]});
  // Anonymous invocation is intentional for this public-only application, never
  // applied to a private module or the bucket itself. Org policy must allow it.
  add('google_cloud_run_v2_service_iam_member',n,{project:projectId,location:region,name:ref('google_cloud_run_v2_service',n,'name'),role:'roles/run.invoker',member:'allUsers'});
  b.output[n+'_url']={value:origin};b.output[n+'_catalog']={value:{bucket:ref('google_storage_bucket',n,'name'),region}};b.source(row);
  b.assertions.push(`run "${n}_public_boundary" {\n command = plan\n assert {\n condition = google_storage_bucket.${n}.public_access_prevention == "enforced" && google_storage_bucket.${n}.uniform_bucket_level_access && !google_storage_bucket.${n}.force_destroy\n error_message = "Only the app is public; the catalog bucket stays private and protected."\n }\n assert {\n condition = google_cloud_run_v2_service_iam_member.${n}.member == "allUsers" && google_cloud_run_v2_service_iam_member.${n}.role == "roles/run.invoker" && !google_cloud_run_v2_service.${n}.iap_enabled\n error_message = "This explicit public-only application has anonymous invocation, not an invented end-user identity."\n }\n assert {\n condition = toset(google_project_iam_custom_role.${n}_catalog.permissions) == toset(["storage.objects.get"]) && google_storage_bucket_iam_member.${n}_editor.member == "group:\${var.${n}_editor_group}"\n error_message = "Runtime read and native editor write authority must remain separate."\n }\n}\nrun "${n}_mutable_image_blocked" {\n command = plan\n variables { ${n}_image_digest = "latest" }\n expect_failures = [var.${n}_image_digest]\n}`);
 }
 const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{google:{source:'hashicorp/google',version:'7.46.2'},'google-beta':{source:'hashicorp/google-beta',version:'7.46.2'}}},provider:{google:{project:projectId},'google-beta':{project:projectId}}};
 return b.finish(config,CLOUD_PROVIDER_LOCKS.gcp+'\n'+CLOUD_PROVIDER_LOCKS.gcpBeta,'mock_provider "google" {\n override_during = plan\n mock_data "google_project" { defaults = { number = "123456789012" } }\n mock_resource "google_service_account" { defaults = { email = "runtime@reviewed-project.iam.gserviceaccount.com" } }\n}\nmock_provider "google-beta" {\n override_during = plan\n mock_resource "google_project_service_identity" { defaults = { email = "service-123456789012@serverless-robot-prod.iam.gserviceaccount.com", member = "serviceAccount:service-123456789012@serverless-robot-prod.iam.gserviceaccount.com" } }\n}\n',GCP_PUBLIC_FAQ_GUIDE);
}

export const GCP_PUBLIC_FAQ_GUIDE=`# Google public-only FAQ composition

Only this explicitly selected public Cloud Run browser/API receives anonymous
run.invoker access. Its catalog bucket remains private with public access
prevention and uniform IAM. The dedicated runtime has a bucket-scoped custom
object-reader role; a separate existing company editor group has get/create/delete
only on that public catalog bucket. There is no HTTP editing route. No private
source, arbitrary URL fetch, user identity or enterprise authorization is implied.

Existing project, registry and editor group are preserved. Required APIs are never
disabled on destroy. The Cloud Run platform agent, not the application, receives
reader access on the exact existing image repository. The runtime has narrow
project-level prediction and read-only cache/model-policy access; no policy writes
or user-managed key is emitted. Google-beta is used only for the documented service
identity resource. Reconcile inherited IAM and organization restrictions on public
invocation; do not disable organization policy to bypass a failure.

See applications/*/BUILD.md. Seed genuinely public articles using the authorized
editor and native generation preconditions; updates/deletes never fall back to
stale or inaccessible evidence. Versioning, noncurrent-version expiry and seven-day
soft deletion support recovery and are not an immediate erasure guarantee. Runtime
never retrieves a historical generation selected by a visitor. No question/answer
persistence or content-bearing app logs are implemented; review platform logging.

The owner policy review is scoped/expiring operator-attested evidence, not an IBM,
Google or other fabricated provider approval API. Runtime separately requires
disabled project caching and disabled model request/response logging/sharing.
The documented global cache-control read sends no question text; review that
control-plane processing and actual model geography/terms against residency needs.
Model availability/context/quotas, prices, anonymous abuse controls, budgets and
real answer/citation/abstention/latency tests remain destination checks. Concurrency,
token and instance bounds are not an invoice cap or SLA.

Use Terraform 1.17.1+; run init -backend=false, validate and test. These native schema
and mock plans do not establish actual IAM, model or deployed behavior. Build, scan
and test the exact source/image; obtain authorization before publishing, cloud
access, real account plan or deployment. Production state/operations remain gated.
`;

export function ibmPublicFaqTerraform(project,plan,environment='staging'){
 const b=builder(project,plan,environment,'ibm'),{input,add}=b;
 const account=input('account_id','Existing destination IBM account; no account is created.','a'.repeat(32),'^[0-9a-f]{32}$');
 const region=input('region','Reviewed regional Code Engine, COS and watsonx model destination.','au-syd','^[a-z]{2}-[a-z]+$');
 const entries=plan.publicFaqPlan.entries;
 if(entries.every(e=>e.row.region===entries[0].row.region)&&/^[a-z]{2}-[a-z]+$/.test(entries[0].row.region)){b.variable.region.default=entries[0].row.region;b.examples.region=entries[0].row.region;}
 const ceProject=input('code_engine_project_id','Existing reviewed Code Engine project; never recreate or import it.','11111111-1111-1111-1111-111111111111',UUID);
 const registry=input('registry_namespace','Existing regional IBM Container Registry namespace.','reviewed-namespace','^[a-z0-9]+(?:[-_][a-z0-9]+)*$');
 const pullSecret=input('registry_pull_secret','Existing registry-pull secret NAME in that project; no credential value is exported.','reviewed-registry-pull','^[a-z][a-z0-9-]{1,61}[a-z0-9]$');
 b.data.ibm_code_engine_project={destination:{project_id:ceProject}};
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${data.ibm_code_engine_project.destination.account_id == var.account_id && data.ibm_code_engine_project.destination.region == var.region}',error_message:'Existing Code Engine project must match the reviewed account and region.'});
 for(const {row}of entries){
  const n=row.address,name=input(n+'_name','Unique application and trusted-profile name.','reviewed-public-help','^[a-z][a-z0-9-]{2,38}[a-z0-9]$');
  const repository=input(n+'_image_repository','Path for this emitted image in the existing namespace.','architect/public-help','^[a-z0-9]+(?:[._/-][a-z0-9]+)*$');
  const digest=input(n+'_image_digest','Built, scanned, tested and authorized-published image digest.','sha256:'+'0'.repeat(64),'^sha256:[0-9a-f]{64}$');
  const wxProject=input(n+'_watsonx_project_id','Existing watsonx data-platform project. Add the trusted profile as an authorized collaborator and associate the runtime instance.','22222222-2222-2222-2222-222222222222',UUID);
  const instance=input(n+'_runtime_instance_id','Existing associated watsonx Runtime instance GUID.','33333333-3333-3333-3333-333333333333',UUID);
  const model=input(n+'_model_id','Reviewed regional Text Chat JSON-object model; verify lifecycle, quotas and geography.','ibm/reviewed-model','^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,99}$');
  const editor=input(n+'_editor_access_group_id','Existing authorized company editor access-group ID. No group or user is created.','AccessGroup-44444444-4444-4444-4444-444444444444','^AccessGroup-[0-9a-fA-F-]{36}$');
  const bucket=input(n+'_catalog_bucket','Globally unique regional bucket dedicated to genuinely public article content; the bucket itself remains private.','reviewed-public-catalog-unique','^[a-z][a-z0-9-]{1,61}[a-z0-9]$');
  const review=n+'_policy_review';b.variable[review]={type:'object({ accountId = string, projectId = string, runtimeInstanceId = string, region = string, model = string, retentionReview = string, approvedBy = string, evidenceSha256 = string, expiresAt = string })',nullable:false,description:'Scoped expiring destination-owner review of actual model/provider retention and processing terms. Operator-attested evidence, not a provider approval API.'};b.examples[review]={accountId:b.examples.account_id,projectId:b.examples[n+'_watsonx_project_id'],runtimeInstanceId:b.examples[n+'_runtime_instance_id'],region:b.examples.region,model:b.examples[n+'_model_id'],retentionReview:'REVIEW_REQUIRED',approvedBy:'REVIEW_REQUIRED',evidenceSha256:'0'.repeat(64),expiresAt:'REPLACE_AFTER_REVIEW'};
  add('ibm_resource_instance',n+'_catalog',{name:name+'-public-catalog',service:'cloud-object-storage',plan:'standard',location:'global',resource_group_id:'${data.ibm_code_engine_project.destination.resource_group_id}',lifecycle:{prevent_destroy:true,postcondition:[{condition:'${self.account_id == var.account_id}',error_message:'Catalog instance must belong to the reviewed account.'}]}});
  add('ibm_cos_bucket',n,{bucket_name:bucket,resource_instance_id:ref('ibm_resource_instance',n+'_catalog','id'),region_location:region,storage_class:'standard',endpoint_type:'public',force_delete:false,object_versioning:{enable:true},noncurrent_version_expiration:{enable:true,noncurrent_days:7,prefix:'',rule_id:'expire-old-catalog-versions'},lifecycle:{prevent_destroy:true}});
  add('ibm_iam_trusted_profile',n,{name,description:'Public FAQ compute identity; no catalog write or end-user authority'});
  add('ibm_iam_trusted_profile_link',n,{profile_id:ref('ibm_iam_trusted_profile',n,'profile_id'),cr_type:'CE',link:{crn:'${data.ibm_code_engine_project.destination.crn}',component_name:ref('ibm_code_engine_app',n,'name'),component_type:'app'}});
  add('ibm_iam_trusted_profile_policy',n,{iam_id:ref('ibm_iam_trusted_profile',n,'iam_id'),roles:['Writer'],resources:{service:'pm-20',resource_instance_id:instance,region},description:'Existing watsonx runtime-instance scope. Writer is broader than prediction-only; project membership remains separate.'});
  const catalogScope={service:'cloud-object-storage',resource_instance_id:ref('ibm_resource_instance',n+'_catalog','guid'),resource_type:'bucket',resource:ref('ibm_cos_bucket',n,'bucket_name')};
  add('ibm_iam_trusted_profile_policy',n+'_catalog',{iam_id:ref('ibm_iam_trusted_profile',n,'iam_id'),roles:['Object Reader'],resources:catalogScope});
  // Article deletion rewrites catalog.json; object DELETE is intentionally absent.
  // Object Writer includes object metadata/retention writes; it is not a custom
  // put-only role. It cannot administer this bucket or grant public access.
  add('ibm_iam_access_group_policy',n+'_editor',{access_group_id:editor,roles:['Object Reader','Object Writer'],resources:catalogScope});
  const settings={ACCOUNT_ID:account,WATSONX_PROJECT_ID:wxProject,RUNTIME_INSTANCE_ID:instance,MODEL_REGION:region,MODEL_ID:model,IAM_PROFILE_ID:ref('ibm_iam_trusted_profile',n,'profile_id'),MAX_OUTPUT_TOKENS:'1024',CATALOG_BUCKET:ref('ibm_cos_bucket',n,'bucket_name'),POLICY_REVIEW_BASE64:'${base64encode(jsonencode(var.'+review+'))}'};
  add('ibm_code_engine_app',n,{project_id:ceProject,name,image_reference:region+'.icr.io/'+registry+'/'+repository+'@'+digest,image_secret:pullSecret,image_port:8080,managed_domain_mappings:'local_public',run_as_user:10001,run_compute_resource_token_enabled:true,scale_cpu_limit:'0.5',scale_memory_limit:'1G',scale_min_instances:0,scale_max_instances:2,scale_concurrency:5,scale_concurrency_target:5,scale_request_timeout:30,run_env_variables:Object.entries(settings).map(([name,value])=>({name,value,type:'literal'})),probe_readiness:{type:'http',path:'/healthz',port:8080,initial_delay:2,interval:5,timeout:2,failure_threshold:12},depends_on:['ibm_iam_trusted_profile_policy.'+n,'ibm_iam_trusted_profile_policy.'+n+'_catalog']});
  b.output[n+'_url']={value:ref('ibm_code_engine_app',n,'endpoint')};b.output[n+'_catalog']={value:{bucket,region}};b.output[n+'_trusted_profile_iam_id']={value:ref('ibm_iam_trusted_profile',n,'iam_id')};b.source(row);
  b.assertions.push(`run "${n}_public_boundary" {\n command = plan\n assert {\n condition = ibm_iam_trusted_profile_policy.${n}_catalog.roles == tolist(["Object Reader"]) && ibm_iam_trusted_profile_policy.${n}_catalog.resources[0].resource_type == "bucket" && ibm_iam_trusted_profile_policy.${n}_catalog.resources[0].resource == var.${n}_catalog_bucket\n error_message = "Runtime may read only the dedicated catalog bucket; no write or public-access grant."\n }\n assert {\n condition = toset(ibm_iam_access_group_policy.${n}_editor.roles) == toset(["Object Reader", "Object Writer"]) && ibm_iam_access_group_policy.${n}_editor.resources[0].resource_type == "bucket" && ibm_iam_access_group_policy.${n}_editor.access_group_id == var.${n}_editor_access_group_id\n error_message = "Separate existing editors have bucket-scoped object access, never Manager or bucket Writer."\n }\n assert {\n condition = !ibm_cos_bucket.${n}.force_delete && ibm_cos_bucket.${n}.object_versioning[0].enable && ibm_code_engine_app.${n}.run_compute_resource_token_enabled && ibm_code_engine_app.${n}.run_as_user == 10001\n error_message = "Protect catalog recovery and use nonroot keyless compute identity."\n }\n}\nrun "${n}_mutable_image_blocked" {\n command = plan\n variables { ${n}_image_digest = "latest" }\n expect_failures = [var.${n}_image_digest]\n}`);
 }
 const config={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{ibm:{source:'IBM-Cloud/ibm',version:'1.89.0'}}},provider:{ibm:{region}}};
 const mocks=`mock_provider "ibm" {\n override_during = plan\n mock_data "ibm_code_engine_project" { defaults = { account_id = "${b.examples.account_id}", region = "${b.examples.region}", resource_group_id = "${'b'.repeat(32)}", crn = "crn:v1:bluemix:public:codeengine:${b.examples.region}:a/${b.examples.account_id}:11111111-1111-1111-1111-111111111111::" } }\n mock_resource "ibm_resource_instance" { defaults = { account_id = "${b.examples.account_id}", id = "crn:v1:bluemix:public:cloud-object-storage:global:a/${b.examples.account_id}:55555555-5555-5555-5555-555555555555::", guid = "55555555-5555-5555-5555-555555555555" } }\n}\n`;
 b.assertions.push(`run "wrong_account_blocked" {\n command = plan\n variables { account_id = "${'c'.repeat(32)}" }\n expect_failures = [terraform_data.review_gate]\n}`);
 return b.finish(config,CLOUD_PROVIDER_LOCKS.ibm,mocks,IBM_PUBLIC_FAQ_GUIDE);
}

export const IBM_PUBLIC_FAQ_GUIDE=`# IBM public-only FAQ composition

The anonymous browser/API uses a dedicated Code Engine trusted profile linked only
to this existing project and this new app. The runtime receives Object Reader on
the exact private COS bucket; a separate existing company access group receives
Object Reader and Object Writer on that bucket. Object Writer includes object
metadata and retention operations, not merely PUT; it does not administer buckets
or make them public. Article deletion conditionally replaces catalog.json; no
object DELETE grant or application HTTP editing route is needed. No public-access
group policy is emitted. Reconcile inherited account/group policies, which can
override narrower grants. Public endpoint routing does not mean anonymous storage.

COS uses a global service instance with a single regional data bucket, encryption
at rest managed by IBM and TLS. Control-plane geography requires separate review.
Versioning and seven-day noncurrent expiry aid recovery, not immediate erasure.
The runtime reads only the current catalog, checks it again before returning an
answer and withholds stale/unsupported evidence. Questions/answers are not persisted
or written to application logs. Private networking/customer-managed keys are not
implemented. This public-only application is not a private knowledge assistant.

Existing Code Engine project, namespace/pull-secret, watsonx project and associated
runtime instance remain intact. The profile gets Writer on that exact pm-20
instance; this is broader than prediction-only. Add the generated profile as a
minimum supported project collaborator and verify the association/model separately.
App creation precedes its compute link to avoid a Terraform cycle; health is
liveness, not model readiness. No app API key or end-user identity is invented.

See applications/*/BUILD.md for editor/build/testing commands. Supply a scoped,
expiring destination-owner policy review and test real IAM, compute token exchange,
conditional storage edits, source updates/deletions, model citations/abstention and
latency. The policy review is operator evidence, not a fabricated provider API.
Review current model availability, quotas, processing terms, prices, anonymous
abuse controls and budget policy. Instance/concurrency/token limits are not an
invoice cap. Protect state/variables. Native schema/mocks and local runtime tests
do not establish account-plan or deployed behavior. Obtain authorization before
image publication, cloud access, real plans or deployment; production operating
and state/backup review remain gated.

References:
- https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-iam-bucket-permissions
- https://cloud.ibm.com/docs/iam?topic=iam-iam-service-roles-actions
- https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-upload
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles-authentication-file
`;
