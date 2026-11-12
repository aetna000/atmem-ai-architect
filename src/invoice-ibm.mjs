import {invoiceBuilder,v,r,l,UUID}from'./invoice-builder.mjs';
import {ibmRegistryHostExpression,ibmRegistryRegionValidation}from'./ibm-registry.mjs';
import {ibmInvoiceOperations}from'./invoice-ibm-operations.mjs';
import providerLock from'./runtime/invoice-ibm-provider-lock.json'with{type:'json'};

// Native composition under qualification; no cloud operation is performed here.
export function ibmInvoiceTerraform(project,row,environment='staging'){
 if(row.provider!=='ibm')throw Error('IBM invoice compilation cannot substitute another cloud');
 const b=invoiceBuilder(project,row,environment),{input,add,region}=b,n=row.address;
 const account=input('account_id','Expected existing IBM Cloud account. No account is created.','a'.repeat(32),'^[0-9a-f]{32}$');
 const group=input('resource_group_name','Existing reviewed destination resource group; never recreated.','reviewed-applications','^[A-Za-z0-9 _.-]{1,128}$');
 const model=input('model_id','Reviewed regional watsonx JSON-object model; verify lifecycle, regional availability and processing terms.','ibm/reviewed-model','^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,99}$');
 const wxProject=input('watsonx_project_id','Existing watsonx project; authorize only the worker trusted profile and associate its runtime instance.','22222222-2222-2222-2222-222222222222',UUID);
 const instance=input('runtime_instance_id','Existing associated watsonx.ai Runtime instance GUID, not a deployment ID.','33333333-3333-3333-3333-333333333333',UUID);
 const endpoint=input('accounting_endpoint','Existing reviewed accounting HTTPS adapter; never provision a replacement.','https://accounting.example.test/actions','^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[^?#@ ]*)?$');
 const scope=input('accounting_scope','Reviewed accounting scope bound to each approval.','owned-team','^[A-Za-z0-9_.:/-]{1,200}$');
 const pull=input('registry_pull_secret','Name of the separately populated registry-pull secret in the new owned Code Engine project. No credential in Terraform.','registry-pull','^[a-z][a-z0-9-]{1,61}[a-z0-9]$');
 if(!row.region)b.variable.region.validation=ibmRegistryRegionValidation();
 for(const purpose of ['runtime','parser']){
  input(purpose+'_image','Reviewed immutable image in this package-owned regional registry namespace. Empty during foundation.','au.icr.io/reviewed-namespace/'+purpose+'@sha256:'+'a'.repeat(64));b.variable[purpose+'_image'].default='';
  b.variable[purpose+'_image'].validation={condition:'${!(var.applications_enabled'+(purpose==='runtime'?' || var.operations_enabled':'')+') || can(regex("@sha256:[0-9a-f]{64}$",var.'+purpose+'_image))}',error_message:'Use the reviewed immutable image digest before releasing applications.'};
  b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${!(var.applications_enabled'+(purpose==='runtime'?' || var.operations_enabled':'')+') || startswith(var.'+purpose+'_image,format("%s/%s/'+purpose+'@sha256:",'+ibmRegistryHostExpression().slice(2,-1)+',local.name))}',error_message:'Images must use the exact owned regional registry namespace, not an invented hostname or foreign repository.'});
  b.testExpressions[purpose+'_image']='format("au.icr.io/invoice-%s/'+purpose+'@sha256:'+'a'.repeat(64)+'",substr(sha256('+JSON.stringify(b.seed)+'),0,12))';
 }
 b.variable.staff_subjects={type:'set(string)',default:[],description:'Explicit existing admin-enrolled App ID subjects. Application membership/reviewer grants are separately admitted in SQL.',validation:{condition:'${alltrue([for subject in var.staff_subjects : can(regex("^[A-Za-z0-9_.:@-]{1,200}$",subject))])}',error_message:'Use exact verified staff subjects, never public signup or display-name guesses.'}};b.examples.staff_subjects=['44444444-4444-4444-4444-444444444444'];
 b.variable.policy_review_base64={type:'string',default:'',description:'Scoped expiring model privacy/processing-terms review. Empty blocks inference; no approval is fabricated.'};b.examples.policy_review_base64='';
 b.variable.replay_review_base64={type:'string',default:'',description:'Scoped expiring acceptance of actual accounting idempotency. Empty disables automatic uncertain replay.'};b.examples.replay_review_base64='';
 b.data.ibm_resource_group={destination:{name:group}};
 b.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${data.ibm_resource_group.destination.account_id == var.account_id && (!var.applications_enabled || length(var.staff_subjects)>0)}',error_message:'Verify the destination account and explicit staff admission before release.'});
 const rg=r('data.ibm_resource_group','destination','id'),projectId=r('ibm_code_engine_project',n,'project_id');
 Object.assign(b.locals,{destination_contract:{id:'normalized-action-v1',endpointSha256:'${sha256(var.accounting_endpoint)}',scope,mappingVersion:1},destination_contract_base64:'${base64encode(jsonencode(local.destination_contract))}',database_config_name:l('name')+'-database',parser_secret_name:l('name')+'-parser',api_secret_name:l('name')+'-api-sql',worker_secret_name:l('name')+'-worker',bucket_name:'${format("%s-%s",local.name,substr(var.account_id,0,8))}'});
 add('ibm_code_engine_project',n,{name:l('name'),resource_group_id:rg,lifecycle:{prevent_destroy:true}});
 add('ibm_cr_namespace',n,{name:l('name'),resource_group_id:rg,lifecycle:{prevent_destroy:true}});
 // Use the maintained Classic private-service endpoint contract, not an assumed
 // direct Code Engine -> VPC/Gen2 route. There is no public SQL fallback.
 add('ibm_database',n,{name:l('name'),service:'databases-for-postgresql',plan:'standard',location:region,resource_group_id:rg,version:'18',service_endpoints:'private',deletion_protection:true,group:{group_id:'member',memory:{allocation_mb:2048},disk:{allocation_mb:20480},members:{allocation_count:2}},configuration:JSON.stringify({log_statement:'none',log_min_error_statement:'panic',log_parameter_max_length_on_error:0}),lifecycle:{prevent_destroy:true}});
 add('ibm_resource_instance',n+'_documents',{name:l('name')+'-documents',service:'cloud-object-storage',plan:'standard',location:'global',resource_group_id:rg,lifecycle:{prevent_destroy:true}});
 add('ibm_cos_bucket',n,{bucket_name:l('bucket_name'),resource_instance_id:r('ibm_resource_instance',n+'_documents','id'),region_location:region,storage_class:'standard',endpoint_type:'public',force_delete:false,object_versioning:{enable:true},lifecycle:{prevent_destroy:true}});
 add('ibm_cos_bucket_lifecycle_configuration',n,{bucket_crn:r('ibm_cos_bucket',n,'crn'),bucket_location:region,endpoint_type:'public',lifecycle_rule:[{rule_id:'invoice-originals-90-days',status:'enable',filter:{prefix:'accounts/'},expiration:{days:90},noncurrent_version_expiration:{noncurrent_days:1}},{rule_id:'unfinished-upload-cleanup',status:'enable',filter:{prefix:'accounts/'},abort_incomplete_multipart_upload:{days_after_initiation:1}}]});
 for(const purpose of ['api','worker']){
  add('ibm_iam_trusted_profile',n+'_'+purpose,{name:l('name')+'-'+purpose,description:'Dedicated invoice '+purpose+'; SQL login and business membership are independent.'});
  add('ibm_iam_trusted_profile_link',n+'_'+purpose,{count:'${var.applications_enabled ? 1 : 0}',profile_id:r('ibm_iam_trusted_profile',n+'_'+purpose,'profile_id'),cr_type:'CE',link:{crn:r('ibm_code_engine_project',n,'crn'),component_name:l('name')+'-'+purpose,component_type:'app'},depends_on:['ibm_code_engine_app.'+n+'_'+purpose]});
  add('ibm_iam_trusted_profile_policy',n+'_'+purpose+'_documents',{iam_id:r('ibm_iam_trusted_profile',n+'_'+purpose,'iam_id'),roles:purpose==='api'?['Object Reader','Object Writer']:['Object Reader'],resources:{service:'cloud-object-storage',resource_instance_id:r('ibm_resource_instance',n+'_documents','guid'),resource_type:'bucket',resource:l('bucket_name')}});
 }
 add('ibm_iam_trusted_profile_policy',n+'_model',{iam_id:r('ibm_iam_trusted_profile',n+'_worker','iam_id'),roles:['Writer'],resources:{service:'pm-20',resource_instance_id:instance,region},description:'Instance-scoped native watsonx role. Writer is broader than prediction-only; separate project collaborator admission remains required.'});
 add('ibm_resource_instance',n+'_identity',{name:l('name')+'-staff',service:'appid',plan:'graduated-tier',location:region,resource_group_id:rg,lifecycle:{prevent_destroy:true}});
 const tenant=r('ibm_resource_instance',n+'_identity','guid'),client=r('ibm_appid_application',n,'client_id');
 add('ibm_appid_application',n,{tenant_id:tenant,name:l('name'),type:'singlepageapp'});
 add('ibm_appid_application_scopes',n,{tenant_id:tenant,client_id:client,scopes:['process']});
 add('ibm_appid_role',n,{tenant_id:tenant,name:'InvoiceStaff',access:[{application_id:client,scopes:['process']}],depends_on:['ibm_appid_application_scopes.'+n]});
 add('ibm_appid_user_roles',n,{for_each:'${var.applications_enabled ? var.staff_subjects : toset([])}',tenant_id:tenant,subject:'${each.value}',role_ids:[r('ibm_appid_role',n,'role_id')]});
 add('ibm_appid_idp_cloud_directory',n,{tenant_id:tenant,is_active:true,signup_enabled:false,self_service_enabled:false,welcome_enabled:false,reset_password_enabled:true,reset_password_notification_enabled:true,identity_field:'email',identity_confirm_access_mode:'FULL',identity_confirm_methods:['email']});
 for(const idp of ['google','facebook','saml'])add('ibm_appid_idp_'+idp,n,{tenant_id:tenant,is_active:false});
 const literal=(name,value)=>({name,value,type:'literal'}),reference=(name,type,key,ref)=>({name,type,key,reference:ref});
 const common={ACCOUNT_ID:l('account_uuid'),REGION:region,WORKFLOW_NAMESPACE:'invoice',DATABASE_NAME:'ibmclouddb',DOCUMENT_BUCKET:l('bucket_name'),DESTINATION_CONTRACT_BASE64:l('destination_contract_base64')};
 for(const purpose of ['api','worker','parser']){
  const settings=purpose==='parser'?{PARSER_AUTH_MODE:'shared-token'}:purpose==='api'?{...common,SERVICE_NAME:l('name')+'-api',PUBLIC_ORIGIN_MODE:'code-engine-default',DATABASE_USER:l('api_db_user'),IAM_PROFILE_ID:r('ibm_iam_trusted_profile',n+'_api','profile_id'),APPID_TENANT_ID:tenant,APPID_CLIENT_ID:client,APPID_ISSUER:r('ibm_appid_application',n,'oauth_server_url'),AUTH_SCOPE:l('name')+'/process'}:{...common,DATABASE_USER:l('worker_db_user'),IAM_PROFILE_ID:r('ibm_iam_trusted_profile',n+'_worker','profile_id'),IBM_ACCOUNT_ID:account,WATSONX_PROJECT_ID:wxProject,RUNTIME_INSTANCE_ID:instance,MODEL_REGION:region,MODEL_ID:model,MAX_OUTPUT_TOKENS:'2048',POLICY_REVIEW_BASE64:v('policy_review_base64'),PARSER_ENDPOINT:r('ibm_code_engine_app',n+'_parser[0]','endpoint')+'/extract',DESTINATION_ENDPOINT:endpoint,DESTINATION_SCOPE:scope,DESTINATION_REPLAY_REVIEW_BASE64:v('replay_review_base64')};
  const env=Object.entries(settings).map(([name,value])=>literal(name,value));
  if(purpose!=='parser')env.push(...[['DATABASE_HOST','host'],['DATABASE_PORT','port'],['DATABASE_CA_PEM','ca_pem']].map(([name,key])=>reference(name,'config_map_key_reference',key,l('database_config_name'))),reference('DATABASE_PASSWORD','secret_key_reference','password',l(purpose==='api'?'api_secret_name':'worker_secret_name')));
  if(purpose==='worker')env.push(reference('DESTINATION_TOKEN','secret_key_reference','accounting_token',l('worker_secret_name')));
  if(purpose!=='api')env.push(reference('PARSER_SHARED_TOKEN','secret_key_reference','token',l('parser_secret_name')));
  add('ibm_code_engine_app',n+'_'+purpose,{count:'${var.applications_enabled ? 1 : 0}',project_id:projectId,name:l('name')+'-'+purpose,image_reference:v(purpose==='parser'?'parser_image':'runtime_image'),image_secret:pull,image_port:8080,managed_domain_mappings:purpose==='api'?'local_public':purpose==='parser'?'local_private':'local',run_as_user:10001,run_service_account:'none',run_compute_resource_token_enabled:purpose!=='parser',scale_cpu_limit:'1',scale_memory_limit:purpose==='parser'?'2G':'1G',scale_min_instances:1,scale_max_instances:1,scale_concurrency:purpose==='api'?32:1,scale_concurrency_target:purpose==='api'?16:1,scale_request_timeout:purpose==='parser'?150:300,run_env_variables:env,...(purpose==='api'?{}:{run_commands:['python','-I','/app/'+(purpose==='worker'?'invoice_worker.py':'invoice_parser_service.py')]}),probe_readiness:{type:'http',path:'/healthz',port:8080,initial_delay:2,interval:5,timeout:2,failure_threshold:12},depends_on:purpose==='parser'?[]:['ibm_iam_trusted_profile_policy.'+n+'_'+purpose+'_documents',...(purpose==='worker'?['ibm_iam_trusted_profile_policy.'+n+'_model']:[])]});
 }
 add('ibm_appid_redirect_urls',n,{count:'${var.applications_enabled ? 1 : 0}',tenant_id:tenant,urls:[r('ibm_code_engine_app',n+'_api[0]','endpoint')+'/']});
 b.output.application_url={value:'${var.applications_enabled ? ibm_code_engine_app.'+n+'_api[0].endpoint : null}'};
 b.output.code_engine_project={value:projectId};b.output.registry={value:ibmRegistryHostExpression()+'/'+l('name')};
 b.output.operator_deployment={value:{provider:'ibm',deploymentId:l('account_uuid'),accountId:l('account_uuid'),namespace:'invoice',tenantId:null,bindings:Object.fromEntries(['api','worker'].map(purpose=>[purpose,{name:l(purpose+'_db_user'),principal:'${uuidv5("url",'+JSON.stringify(b.seed+'/'+purpose+'-sql-credential')+')}'}]))}};
 b.output.database_bootstrap={value:{deploymentCrn:r('ibm_database',n,'id'),database:'ibmclouddb',projectId,databaseConfig:l('database_config_name'),apiSecret:l('api_secret_name'),workerSecret:l('worker_secret_name'),parserSecret:l('parser_secret_name'),registryPullSecret:pull}};
 ibmInvoiceOperations(b,n,{projectId,pull});
 b.files['CODE_ENGINE_INPUTS.md']=IBM_INPUTS;
 b.assertions.push(`run "private_database_and_parser" {\n command = plan\n assert {\n condition = ibm_database.${n}.service_endpoints == "private" && ibm_database.${n}.version == "18" && ibm_database.${n}.deletion_protection\n error_message = "Retain private native PostgreSQL and recovery protection."\n }\n assert {\n condition = ibm_code_engine_app.${n}_parser[0].managed_domain_mappings == "local_private" && !ibm_code_engine_app.${n}_parser[0].run_compute_resource_token_enabled && ibm_code_engine_app.${n}_parser[0].run_service_account == "none"\n error_message = "Untrusted PDF parser has private TLS and no cloud compute/API identity."\n }\n assert {\n condition = startswith(ibm_code_engine_app.${n}_api[0].image_reference,"au.icr.io/") && ibm_code_engine_app.${n}_worker[0].scale_min_instances == 1\n error_message = "Use the actual Sydney registry hostname and retain the background worker."\n }\n}\nrun "foundation_only" {\n command = plan\n variables {\n applications_enabled = false\n operations_enabled = false\n maintenance_enabled = false\n }\n assert {\n condition = length(ibm_code_engine_app.${n}_api) == 0 && length(ibm_code_engine_app.${n}_worker) == 0 && length(ibm_code_engine_app.${n}_parser) == 0 && length(ibm_code_engine_job.${n}_operator_initialize) == 0\n error_message = "Bootstrap and publication precede application release."\n }\n}\nrun "mutable_image_rejected" {\n command = plan\n variables { runtime_image = "unreviewed:latest" }\n expect_failures = [var.runtime_image]\n}\nrun "foreign_registry_rejected" {\n command = plan\n variables { runtime_image = "foreign.test/runtime@sha256:${'a'.repeat(64)}" }\n expect_failures = [terraform_data.review_gate]\n}\nrun "empty_staff_rejected" {\n command = plan\n variables { staff_subjects = [] }\n expect_failures = [terraform_data.review_gate]\n}\nrun "wrong_account_rejected" {\n command = plan\n variables { account_id = "${'c'.repeat(32)}" }\n expect_failures = [terraform_data.review_gate]\n}`);
 let mock='mock_provider "ibm" {\n override_during = plan\n mock_data "ibm_resource_group" { defaults = { id="'+ 'b'.repeat(32)+'",account_id="'+'a'.repeat(32)+'" } }\n mock_resource "ibm_code_engine_project" { defaults = { project_id="11111111-1111-4111-8111-111111111111",crn="crn:v1:bluemix:public:codeengine:au-syd:a/'+ 'a'.repeat(32)+':11111111-1111-4111-8111-111111111111::" } }\n mock_resource "ibm_resource_instance" { defaults = { guid="55555555-5555-4555-8555-555555555555",id="crn:v1:bluemix:public:cloud-object-storage:global:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:55555555-5555-4555-8555-555555555555::" } }\n mock_resource "ibm_iam_trusted_profile" { defaults = { profile_id="Profile-66666666-6666-4666-8666-666666666666",iam_id="iam-Profile-66666666-6666-4666-8666-666666666666" } }\n mock_resource "ibm_appid_application" { defaults = { client_id="77777777-7777-4777-8777-777777777777",oauth_server_url="https://au-syd.appid.cloud.ibm.com/oauth/v4/55555555-5555-4555-8555-555555555555" } }\n}\n';
 mock+='override_resource {\n override_during = plan\n target = ibm_cos_bucket.'+n+'\n values = { crn = "crn:v1:bluemix:public:cloud-object-storage:global:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:55555555-5555-4555-8555-555555555555:bucket:fixture-invoices" }\n}\n';
 for(const [purpose,digit]of [['api','6'],['worker','8']])mock+='override_resource {\n override_during = plan\n target = ibm_iam_trusted_profile.'+n+'_'+purpose+'\n values = '+JSON.stringify({profile_id:'Profile-'+digit.repeat(8)+'-'+digit.repeat(4)+'-4'+digit.repeat(3)+'-8'+digit.repeat(3)+'-'+digit.repeat(12),iam_id:'iam-Profile-'+digit.repeat(8)+'-'+digit.repeat(4)+'-4'+digit.repeat(3)+'-8'+digit.repeat(3)+'-'+digit.repeat(12)})+'\n}\n';
 for(const purpose of ['api','parser'])mock+='override_resource {\n override_during = plan\n target = ibm_code_engine_app.'+n+'_'+purpose+'[0]\n values = { endpoint = format("https://invoice-%s-'+purpose+'.project-fixture.'+(purpose==='parser'?'private.':'')+'au-syd.codeengine.appdomain.cloud",substr(sha256('+JSON.stringify(b.seed)+'),0,12)) }\n}\n';
 return b.finish({ibm:{region}},{ibm:{source:'IBM-Cloud/ibm',version:providerLock.version}},providerLock.lock,mock,IBM_GUIDE);
}
const IBM_GUIDE=`# IBM invoice workflow (under qualification)

A new owned Code Engine project hosts the public App ID/PKCE staff API, a minimum-one
background queue worker and a separate private-TLS parser. Only worker/parser hold
the parser-only 256-bit admission token; it grants no cloud/document/SQL/action
permission. The parser has neither a compute resource token nor Code Engine API
service-account authority. API and worker use separate native trusted profiles,
SQL logins and secret references. Staff authentication is separate from live SQL
membership and reviewer authority; public self-registration is disabled.

The dedicated PostgreSQL 18 Classic instance uses private IBM service endpoints;
no unimplemented direct VPC/Gen2 route or public SQL fallback is asserted. Exact
regional service availability, private connectivity, CA verification and inherited
permissions require authorized destination checks. Documents are private, versioned
and stored regionally with a 90-day current / one-day noncurrent lifecycle. The
regional S3 API uses authenticated TLS. Cloud control-plane/log/backup behavior and
account policy need separate review; no exact erasure deadline is promised.

Sydney Container Registry uses au.icr.io, not au-syd.icr.io. The namespace is owned
by this package. Foundation creates resources with applications_enabled=false.
CODE_ENGINE_INPUTS.md specifies separately populated config/secret references.
Publish immutable reviewed images only when authorized, initialize SQL and staff
membership through the separate operator, then review application release. The
worker's instance-scoped watsonx Writer role is broader than prediction-only;
separate project collaborator admission and the scoped model policy review remain
required. An empty policy review blocks inference and never fabricates approval.

Native schemas/mocks and local images do not prove the real account, IBM private
network, model processing, restore or deployment. Full managed operator/scheduled
retention delivery, monitoring, state strategy, registry/Spec Kit admission and the
complete conversation/export checks remain qualification work. No cloud operation
is performed by generating this package. Preserve the external accounting system.
`;
const IBM_INPUTS=`# Code Engine foundation inputs and ownership

Use the database_bootstrap and operator_deployment outputs, not guessed identifiers.
The new database's built-in application database is ibmclouddb; the separate operator
owns the new workflow schema. Application SQL passwords are distinct strong random
values created outside Terraform. Native trusted profiles authorize COS/model
access, not database login: operator bindings use stable owned credential UUIDs,
not a false claim of native IAM-to-SQL authentication.

In the new Code Engine project, an authorized operator creates these references
from private mode-0600 inputs, without placing secret values in Terraform/state:
- registry_pull_secret: native registry configuration, private namespace pull only.
- databaseConfig config map: exact private host, port, native PEM ca_pem and operator_user.
- operator_jobs.operatorSecret: separate operator SQL password; only operating tasks.
- apiSecret generic secret: password for the generated API SQL login only.
- workerSecret generic secret: worker SQL password and existing accounting_token.
- parserSecret generic secret: token, exactly 64 lowercase hexadecimal characters
  from 32 cryptographically random bytes; only worker and parser reference it.

Read native connection/CA metadata for this exact database deployment. Never use a
public hostname or weaken TLS verification to bypass private connectivity. Supply
bootstrap's private operator files and create both nonadministrative logins, exact
schema/grants and memberships. Native CA/token rotation requires an explicit rollout;
rotate parser/worker together and verify old/missing tokens are denied. The parent
parser removes the token from its environment and its native tools use a minimal
explicit environment. This is not an OS sandbox or proof of inherited platform IAM.

The API derives its same-origin policy only from documented Code Engine app/domain/
subdomain/region settings matched to its compiler-owned service name. No request
Host or Forwarded header chooses a trusted origin. The App ID redirect resource
references the created API endpoint after creation, avoiding a Terraform cycle.
`;
