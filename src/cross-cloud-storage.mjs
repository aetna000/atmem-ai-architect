import {existingReference,existingReferenceFiles} from './existing-references.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';
// Narrow native storage contracts; this does not imply general provider coverage.
const definitions={azure:{name:'Azure Blob Storage',provider:'azurerm',source:'hashicorp/azurerm',version:'4.81.0',types:['azurerm_storage_account','azurerm_storage_container','azurerm_role_definition','azurerm_role_assignment']},gcp:{name:'Google Cloud Storage',provider:'google',source:'hashicorp/google',version:'7.46.2',types:['google_storage_bucket','google_storage_bucket_iam_member']},ibm:{name:'IBM Cloud Object Storage',provider:'ibm',source:'IBM-Cloud/ibm',version:'1.89.0',types:['ibm_cos_bucket','ibm_iam_service_policy']}};
const address=id=>'block_'+Array.from(new TextEncoder().encode(id),b=>b.toString(16).padStart(2,'0')).join('');
export const hasCrossCloud=project=>project.nodes.some(n=>n.data.kind!=='note'&&['azure','gcp','ibm'].includes(n.data.provider)&&n.data.implementation==='private-object-storage');
export function crossCloudPlan(project){
 const nodes=project.nodes.filter(n=>n.data.kind!=='note'),providers=[...new Set(nodes.filter(n=>n.data.origin!=='existing').map(n=>n.data.provider))];
 const provider=providers.length===1?providers[0]:null,definition=definitions[provider];
 const stores=nodes.filter(n=>definition&&n.data.provider===provider&&n.data.origin!=='existing'&&n.data.implementation==='private-object-storage'&&String(n.data.service||n.data.label)===definition.name);
 const actors=nodes.filter(n=>n.data.provider==='tools'&&n.data.origin==='existing'&&n.data.binding==='cloud-storage-principal');
 const connections=project.edges.filter(e=>e.access==='storage-object-admin'&&actors.some(a=>a.id===e.source)&&stores.some(n=>n.id===e.target));
 const gapDetails=[];
 if(actors.length!==1)gapDetails.push({id:'caller-scope',message:'This storage contract requires one explicit existing caller; multiple independent identities need separate permission inputs.'});
 if(!definition)gapDetails.push({id:'cloud-scope',message:'Only one provider per native storage export is supported; mixed-cloud deployment remains unimplemented.'});
 for(const n of nodes){
  if(!stores.includes(n)&&!actors.includes(n)&&!existingReference(n))gapDetails.push({id:'resource-'+address(n.id),componentIds:[n.id],message:`${n.data.label}: native storage implementation is unavailable for this component.`});
  if(stores.includes(n)&&connections.filter(e=>e.target===n.id).length!==1)gapDetails.push({id:'access-'+address(n.id),componentIds:[n.id],message:`${n.data.label}: exactly one explicit object-admin caller binding is required.`});
  if(actors.includes(n)&&!connections.some(e=>e.source===n.id))gapDetails.push({id:'access-'+address(n.id),componentIds:[n.id],message:'Caller is not connected to a supported storage component.'});
 }
 for(const e of project.edges)if(!connections.includes(e))gapDetails.push({id:'connection-'+address(e.id),edgeIds:[e.id],message:'Unsupported storage integration; preserve and implement the requested flow.'});
 if(!stores.length)gapDetails.push({id:'no-storage',message:'Select a supported private-object-storage implementation.'});
 const rows=nodes.map(n=>({id:n.id,address:address(n.id),label:n.data.label,provider:n.data.provider,service:n.data.service||n.data.label,existing:n.data.origin==='existing',foundation:stores.includes(n),compute:false,reference:actors.includes(n),existingServiceReference:existingReference(n),implemented:stores.includes(n)||actors.includes(n)||!!existingReference(n),resources:stores.includes(n)?definition.types:[],settings:{},region:n.data.config?.region||'To be selected',dependencies:[],terraform:existingReference(n)?'Existing service reference — preserved without provisioning or import; behavior and connections remain unverified':stores.includes(n)?'Typed native storage and scoped object permissions generated; cloud verification required':actors.includes(n)?'Existing principal reference; permissions require review':'Implementation needed'}));
 return {revision:project.revision,provider,rows,connections:project.edges.map(e=>({...e,generated:connections.includes(e)})),storageContracts:stores.map(n=>({id:n.id,address:address(n.id),callerId:connections.find(e=>e.target===n.id)?.source})),gapDetails,gaps:gapDetails.map(g=>g.message),accessPlan:{bindings:[],connections:[]},asyncPlan:{pipelines:[]},summaryPlan:{entries:[],modelIds:[]},ragPlan:{entries:[],componentIds:[]},sourceContractPlan:{sources:[],connections:[]},webPlan:{entries:[],componentIds:[]},scope:'Native storage foundation only; emulator does not validate IAM or control-plane deployment.',sources:[]};
}

const CLIENT=`"""Generated object CRUD adapters. Configure an authenticated provider SDK separately.
Emulator injection is test-only; this file neither discovers credentials nor provisions resources.
"""
def azure_put(container,key,data):
    return container.upload_blob(key,data,overwrite=True)
def azure_get(container,key):
    return container.download_blob(key).readall()
def azure_delete(container,key):
    container.delete_blob(key,delete_snapshots='include')
def gcp_put(bucket,key,data,expected_generation=None):
    blob=bucket.blob(key)
    blob.upload_from_string(data,if_generation_match=expected_generation,timeout=5,retry=None)
    return blob.generation
def gcp_get(bucket,key,generation=None):
    return bucket.blob(key,generation=generation).download_as_bytes(timeout=5,retry=None)
def gcp_delete(bucket,key,generation=None):
    bucket.blob(key,generation=generation).delete(timeout=5,retry=None)
def ibm_put(client,bucket,key,data):
    return client.put_object(Bucket=bucket,Key=key,Body=data)
def ibm_get(client,bucket,key,version=None):
    args={'Bucket':bucket,'Key':key}
    if version:args['VersionId']=version
    result=client.get_object(**args)
    try:return result['Body'].read()
    finally:result['Body'].close()
def ibm_delete(client,bucket,key,version):
    client.delete_object(Bucket=bucket,Key=key,VersionId=version)
`;

export function crossCloudTerraform(project,environment='staging'){
 const plan=crossCloudPlan(project),d=definitions[plan.provider],p=d?.provider||'google';
 const variable={review_approved:{type:'bool',default:false,description:'Explicitly review the real destination, permissions, cost and plan before apply.'},region:{type:'string',description:'Reviewed provider-native region; emulator region does not select a deployment location.'}};
 const resource={terraform_data:{review_gate:{input:{design_revision:project.revision,environment},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'Unfinished work or missing review blocks deployment.'}]}}}};
 const add=(type,name,body)=>{(resource[type]||={})[name]={...body,depends_on:['terraform_data.review_gate']};};
 const v=name=>'${var.'+name+'}',ref=(type,name,field)=>'${'+type+'.'+name+'.'+field+'}';
 const input=(name,description)=>variable[name]={type:'string',nullable:false,description};
 const examples={review_approved:true,region:{azure:'australiaeast',gcp:'australia-southeast1',ibm:'au-syd'}[plan.provider]||'australia-southeast1'};
 const provider=d?{[p]:{}}:{};
 if(plan.provider==='azure'){
  input('subscription_id','Reviewed Azure subscription UUID.');input('resource_group_name','Existing reviewed resource group.');input('principal_object_id','Existing Entra principal object UUID; no credentials.');
  provider[p]={features:{},subscription_id:v('subscription_id'),storage_use_azuread:true};Object.assign(examples,{subscription_id:'11111111-1111-1111-1111-111111111111',resource_group_name:'synthetic-qualification',principal_object_id:'22222222-2222-2222-2222-222222222222'});
 }
 if(plan.provider==='gcp'){input('project_id','Reviewed existing Google Cloud project.');input('principal_member','Existing serviceAccount:email identity for object CRUD; no allUsers or allAuthenticatedUsers.');variable.principal_member.validation={condition:'${can(regex("^serviceAccount:[^@ ]+@[^ ]+\\\\.iam\\\\.gserviceaccount\\\\.com$", var.principal_member))}',error_message:'Select a specific existing service account.'};provider[p]={project:v('project_id'),region:v('region')};Object.assign(examples,{project_id:'synthetic-qualification',principal_member:'serviceAccount:operator@synthetic-qualification.iam.gserviceaccount.com'});}
 if(plan.provider==='ibm'){input('cos_instance_crn','Existing reviewed COS instance CRN.');input('iam_service_id','Existing IBM IAM service ID for bucket-scoped object access.');provider[p]={region:v('region')};Object.assign(examples,{cos_instance_crn:'crn:v1:bluemix:public:cloud-object-storage:global:a/00000000000000000000000000000000:11111111-1111-1111-1111-111111111111::',iam_service_id:'ServiceId-22222222-2222-2222-2222-222222222222'});}
 let storageIndex=0;
 for(const store of plan.storageContracts){
  storageIndex++;
  const n=store.address;input(n+'_name','Globally unique reviewed storage name.');examples[n+'_name']=plan.provider==='azure'?`atmemsynthetic${storageIndex}`:`atmem-synthetic-storage-${storageIndex}`;
  if(plan.provider==='azure'){
   add('azurerm_storage_account',n,{name:v(n+'_name'),resource_group_name:v('resource_group_name'),location:v('region'),account_tier:'Standard',account_replication_type:'LRS',account_kind:'StorageV2',min_tls_version:'TLS1_2',https_traffic_only_enabled:true,allow_nested_items_to_be_public:false,shared_access_key_enabled:false,blob_properties:{versioning_enabled:true,delete_retention_policy:{days:7}},lifecycle:{prevent_destroy:environment!=='qualification'}});
   add('azurerm_storage_container',n,{name:'documents',storage_account_id:ref('azurerm_storage_account',n,'id'),container_access_type:'private'});
   add('azurerm_role_definition',n,{name:'AtMem object CRUD '+v(n+'_name'),scope:ref('azurerm_storage_account',n,'id'),permissions:[{data_actions:['Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read','Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write','Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete']}],assignable_scopes:[ref('azurerm_storage_account',n,'id')]});
   add('azurerm_role_assignment',n,{scope:ref('azurerm_storage_container',n,'resource_manager_id'),role_definition_id:ref('azurerm_role_definition',n,'role_definition_resource_id'),principal_id:v('principal_object_id')});
  }
  if(plan.provider==='gcp'){
   add('google_storage_bucket',n,{name:v(n+'_name'),project:v('project_id'),location:v('region'),uniform_bucket_level_access:true,public_access_prevention:'enforced',versioning:{enabled:true},force_destroy:false,lifecycle:{prevent_destroy:environment!=='qualification'}});
   add('google_storage_bucket_iam_member',n,{bucket:ref('google_storage_bucket',n,'name'),role:'roles/storage.objectUser',member:v('principal_member')});
  }
  if(plan.provider==='ibm'){
   add('ibm_cos_bucket',n,{bucket_name:v(n+'_name'),resource_instance_id:v('cos_instance_crn'),region_location:v('region'),storage_class:'standard',object_versioning:{enable:true},force_delete:false,lifecycle:{prevent_destroy:environment!=='qualification'}});
   add('ibm_iam_service_policy',n,{iam_service_id:v('iam_service_id'),roles:['Writer'],resources:[{service:'cloud-object-storage',resource_instance_id:'${split(":", var.cos_instance_crn)[7]}',resource_type:'bucket',resource:ref('ibm_cos_bucket',n,'bucket_name')}]});
  }
 }
 const gaps=[...plan.gapDetails.map(g=>g.id),...(environment==='production'?['production-remote-state-and-operational-review-required']:[])];
 const config={terraform:{required_version:'>= 1.7.0, < 2.0.0',required_providers:d?{[p]:{source:d.source,version:d.version}}:{}},provider,variable,locals:{unfinished_work:gaps},resource,output:{design_revision:{value:project.revision},environment:{value:environment}}};
 const values=Object.entries(examples).map(([k,val])=>`  ${k} = ${JSON.stringify(val)}`).join('\n');
 return {...existingReferenceFiles(project),...(d?{'.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS[plan.provider],'requirements.txt':({azure:'azure-storage-blob==12.31.1',gcp:'google-cloud-storage==3.17.1',ibm:'boto3==1.43.123'})[plan.provider]+'\n'}:{}),'main.tf.json':JSON.stringify(config,null,2),'resource-schedule.json':JSON.stringify(plan,null,2),'storage_client.py':CLIENT,'deployment.tfvars.json.example':JSON.stringify({...examples,review_approved:false},null,2),'.gitignore':'.terraform/\n*.tfstate*\n*.tfplan\n*.tfvars\n*.tfvars.json\n__pycache__/\n',
  'tests/storage.tftest.hcl':`mock_provider "${p}" {}\nvariables {\n${values}\n}\nrun "reviewed_storage_plan" { command = plan }\nrun "unreviewed_plan_blocked" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n`,
  'README.md':`# ${d?.name||'Unsupported cloud'} storage foundation\n\nNative resources and an SDK adapter for explicit private-object-storage + cloud-storage-principal + storage-object-admin contracts. Object permissions include deletion for this synthetic CRUD scenario. Existing principal permissions and public grants outside this export require review; no default emulator identity is a deployment identity. Azure uses a container-scoped custom data role, GCP a bucket-scoped objectUser grant, IBM a bucket-scoped Writer grant. Existing subscription/project/resource group/COS instance inputs must be reviewed. Provider-managed encryption defaults apply; customer-managed keys and private-network routing are not implemented by this contract. Azure has an authenticated public network endpoint, not a private endpoint.\n\nEmulation exercises object APIs and emitted client functions, not control-plane apply or IAM enforcement. Run terraform init -backend=false, terraform validate, then terraform test in a credential-free directory. Use the standard provider credential chain only for a separately approved account plan. No credentials belong in this export. Generated examples use synthetic placeholders. Production is blocked pending remote state and operational review. Never clear those gates to obtain a pass. SDK adapters accept an explicitly configured authenticated client; install the pinned SDK from requirements.txt in an isolated environment before configuring the authenticated client; SDK dependency installation is operator-owned (Azure azure-storage-blob, GCP google-cloud-storage, IBM S3-compatible boto3/HMAC client).\n`};
}
