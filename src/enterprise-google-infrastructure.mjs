import {resourceAddress} from './identifiers.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';
import {googleDocumentJobTests} from './enterprise-google-tests.mjs';
import {enterpriseApplicationFiles}from'./enterprise-application.mjs';

// Partial compiler building block. Do not register a complete private-assistant
// capability until application/operator/recovery and the other clouds qualify.
export function googleDocumentJobTerraform(project,row,environment='staging'){
 if(!project||typeof project.id!=='string'||!project.id||project.id.length>255||!Number.isSafeInteger(project.revision)||project.revision<1)throw Error('Use the stable owned project and design revision');
 if(!row||row.provider!=='gcp'||typeof row.id!=='string'||!row.id||typeof row.address!=='string'||!/^block_[0-9a-f]+$/.test(row.address)||typeof row.region!=='string'||!(/^[a-z]+-[a-z]+[1-9][0-9]?$/).test(row.region))throw Error('Preserve the explicit Google provider and canonical selected region');
 encodeURIComponent(row.id); // Reject invalid Unicode instead of replacing bytes.
 const address=resourceAddress(row.id);
 if(row.address!==address)throw Error('Keep the canonical source-component address; do not redirect another component');
 if(!['staging','production','qualification'].includes(environment))throw Error('Use an explicit supported environment');
 const n=row.address,seed='https://atmem.ai/workspaces/'+encodeURIComponent(project.id)+'/'+n+'/'+environment;
 const v=key=>'${var.'+key+'}',r=(type,key,attribute)=>'${'+type+'.'+key+'.'+attribute+'}',l=key=>'${local.'+key+'}';
 const variable={review_approved:{type:'bool',default:false,nullable:false,description:'Review the exact destination, IAM scope, raw-data retention, costs and operating responsibilities before any apply.'},images_ready:{type:'bool',default:false,nullable:false,description:'Enable configuration output only after actual immutable parser/transfer artifacts are built and reviewed.'}};
 const examples={review_approved:false,images_ready:false},resource={},output={};
 function input(name,description,example,pattern,defaultValue){
  variable[name]={type:'string',nullable:false,description,validation:{condition:'${can(regex('+JSON.stringify(pattern)+',var.'+name+'))}',error_message:'Supply the reviewed '+name+' destination input.'}};
  if(defaultValue!==undefined)variable[name].default=defaultValue;examples[name]=example;return v(name);
 }
 const destination=input('project_id','Existing owned project in which this package administers Batch jobs. Review project-scoped control permissions; unrelated workloads are not adopted.','reviewed-project','^[a-z][a-z0-9-]{4,28}[a-z0-9]$');
 const region=input('region','Placement is bound to the selected architecture; regenerate to change it.',row.region,'^'+row.region+'$',row.region);
 const worker=input('worker_service_account','Existing question-worker service account in this project, referenced without changing its other roles or SQL identity.','owned-worker@reviewed-project.iam.gserviceaccount.com','^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9][.]iam[.]gserviceaccount[.]com$');
 const locals={name:'${format("doc-%s",substr(sha256('+JSON.stringify(seed)+'),0,12))}'};
 const checks=[{condition:v('review_approved'),error_message:'Review the destination and complete this component plan before any apply.'},
  {condition:'${endswith(var.worker_service_account,format("@%s.iam.gserviceaccount.com",var.project_id))}',error_message:'The existing worker identity must belong to this destination project.'},
  {condition:'${var.worker_service_account != format("%s-vm@%s.iam.gserviceaccount.com",local.name,var.project_id)}',error_message:'Keep question-worker and parser-transfer VM identities separate.'}];
 for(const purpose of ['parser','transfer']){
  const name=purpose+'_image';
  variable[name]={type:'string',default:'',nullable:false,description:'Immutable package-owned regional '+purpose+' artifact; empty only during foundation.',validation:{condition:'${!var.images_ready || can(regex("^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$",var.'+name+'))}',error_message:'Use the actual reviewed immutable '+purpose+' artifact.'}};
  examples[name]='';
  checks.push({condition:'${!var.images_ready || startswith(var.'+name+',format("%s-docker.pkg.dev/%s/%s/'+purpose+'@sha256:",var.region,var.project_id,local.name))}',error_message:'Keep '+purpose+' in the owned regional registry with a reviewed digest.'});
 }
 variable.parser_revision={type:'string',default:'',nullable:false,description:'Full independently qualified parser artifact revision, supplied by the image build receipt, not guessed from a source revision.',validation:{condition:'${!var.images_ready || can(regex("^[0-9a-f]{64}$",var.parser_revision))}',error_message:'Supply the actual qualified parser artifact revision.'}};examples.parser_revision='';
 const literal=value=>value.replace(/\$\{/g,()=>'$${').replace(/%\{/g,()=>'%%{');
 resource.terraform_data={[n+'_review']:{input:{design_revision:project.revision,environment,source_component:literal(row.id)},lifecycle:{precondition:checks}}};
 const add=(type,name,body)=>((resource[type]??={})[name]={...body,depends_on:['terraform_data.'+n+'_review',...(body.depends_on||[])]});
 const apiDependencies=[];
 for(const [key,service]of Object.entries({compute:'compute.googleapis.com',batch:'batch.googleapis.com',identity:'iam.googleapis.com',storage:'storage.googleapis.com',registry:'artifactregistry.googleapis.com',dns:'dns.googleapis.com'})){
  add('google_project_service',n+'_'+key,{project:destination,service,disable_on_destroy:false});apiDependencies.push('google_project_service.'+n+'_'+key);
 }
 add('google_project_service_identity',n+'_batch_agent',{provider:'google-beta',project:destination,service:'batch.googleapis.com',depends_on:['google_project_service.'+n+'_batch']});
 add('google_project_iam_member',n+'_batch_agent',{project:destination,role:'roles/batch.serviceAgent',member:r('google_project_service_identity',n+'_batch_agent','member')});
 add('google_service_account',n+'_vm',{project:destination,account_id:l('name')+'-vm',display_name:'Trusted one-file transfer and Batch reporting; no source/model/SQL role',depends_on:['google_project_service.'+n+'_identity']});
 const vmMember='${format("serviceAccount:%s",google_service_account.'+n+'_vm.email)}',workerMember='${format("serviceAccount:%s",var.worker_service_account)}';
 add('google_project_iam_member',n+'_reporter',{project:destination,role:'roles/batch.agentReporter',member:vmMember,depends_on:['google_project_service.'+n+'_batch']});
 add('google_service_account_iam_member',n+'_worker_act_as',{service_account_id:r('google_service_account',n+'_vm','name'),role:'roles/iam.serviceAccountUser',member:workerMember});
 add('google_project_iam_custom_role',n+'_control',{project:destination,role_id:'${replace(local.name,"-","_")}_control',title:'Owned private document job controller',stage:'GA',permissions:['batch.jobs.create','batch.jobs.get','batch.jobs.delete','batch.operations.get'],depends_on:['google_project_service.'+n+'_batch']});
 add('google_project_iam_member',n+'_worker_control',{project:destination,role:r('google_project_iam_custom_role',n+'_control','name'),member:workerMember});
 add('google_artifact_registry_repository',n,{project:destination,location:region,repository_id:l('name'),format:'DOCKER',description:'Reviewed immutable parser and trusted transfer artifacts',depends_on:['google_project_service.'+n+'_registry'],lifecycle:{prevent_destroy:true}});
 add('google_artifact_registry_repository_iam_member',n+'_image_read',{project:destination,location:region,repository:r('google_artifact_registry_repository',n,'repository_id'),role:'roles/artifactregistry.reader',member:vmMember});
 add('google_storage_bucket',n,{project:destination,name:'${format("atmem-doc-%s",substr(sha256(format("%s:%s",var.project_id,local.name)),0,20))}',location:region,storage_class:'STANDARD',uniform_bucket_level_access:true,public_access_prevention:'enforced',force_destroy:false,
  versioning:{enabled:false},soft_delete_policy:{retention_duration_seconds:0},lifecycle_rule:[{action:{type:'Delete'},condition:{age:1,matches_prefix:['document-jobs/']}}],lifecycle:{prevent_destroy:true},depends_on:['google_project_service.'+n+'_storage']});
 for(const [role,permissions,member]of [['transfer',['storage.objects.get','storage.objects.create'],vmMember],['worker',['storage.objects.get','storage.objects.create','storage.objects.delete'],workerMember]]){
  add('google_project_iam_custom_role',n+'_'+role+'_objects',{project:destination,role_id:'${replace(local.name,"-","_")}_'+role+'_objects',title:'Private parser '+role+' temporary bytes',stage:'GA',permissions,depends_on:['google_project_service.'+n+'_storage']});
  add('google_storage_bucket_iam_member',n+'_'+role,{bucket:r('google_storage_bucket',n,'name'),role:r('google_project_iam_custom_role',n+'_'+role+'_objects','name'),member});
 }
 add('google_compute_network',n,{project:destination,name:l('name'),auto_create_subnetworks:false,delete_default_routes_on_create:true,depends_on:['google_project_service.'+n+'_compute'],lifecycle:{prevent_destroy:true}});
 add('google_compute_subnetwork',n,{project:destination,name:l('name'),region,network:r('google_compute_network',n,'id'),ip_cidr_range:'10.87.0.0/24',private_ip_google_access:true,lifecycle:{prevent_destroy:true}});
 // No NAT/public IP or broad internet route: only Google private API VIPs and
 // the documented direct connectivity range are reachable from trusted VMs.
 for(const [suffix,cidr]of [['api','199.36.153.8/30'],['direct','34.126.0.0/18']])add('google_compute_route',n+'_'+suffix,{project:destination,name:l('name')+'-'+suffix,network:r('google_compute_network',n,'id'),dest_range:cidr,next_hop_gateway:'default-internet-gateway',priority:1000});
 add('google_compute_firewall',n+'_allow_api',{project:destination,name:l('name')+'-api',network:r('google_compute_network',n,'id'),direction:'EGRESS',priority:1000,destination_ranges:['199.36.153.8/30','34.126.0.0/18'],target_service_accounts:[r('google_service_account',n+'_vm','email')],allow:[{protocol:'tcp',ports:['443']}]});
 add('google_compute_firewall',n+'_deny_egress',{project:destination,name:l('name')+'-deny-egress',network:r('google_compute_network',n,'id'),direction:'EGRESS',priority:2000,destination_ranges:['0.0.0.0/0'],deny:[{protocol:'all'}]});
 add('google_compute_firewall',n+'_deny_ingress',{project:destination,name:l('name')+'-deny-ingress',network:r('google_compute_network',n,'id'),direction:'INGRESS',priority:1000,source_ranges:['0.0.0.0/0'],deny:[{protocol:'all'}]});
 for(const [key,domain]of [['apis','googleapis.com.'],['registry','pkg.dev.']]){
  add('google_dns_managed_zone',n+'_'+key,{project:destination,name:l('name')+'-'+key,dns_name:domain,visibility:'private',description:'Owned private parser API resolution',private_visibility_config:{networks:[{network_url:r('google_compute_network',n,'id')}]},depends_on:['google_project_service.'+n+'_dns'],lifecycle:{prevent_destroy:true}});
  add('google_dns_record_set',n+'_'+key+'_wildcard',{project:destination,managed_zone:r('google_dns_managed_zone',n+'_'+key,'name'),name:'*.'+domain,type:'CNAME',ttl:300,rrdatas:['private.googleapis.com.']});
 }
 add('google_dns_record_set',n+'_private_vip',{project:destination,managed_zone:r('google_dns_managed_zone',n+'_apis','name'),name:'private.googleapis.com.',type:'A',ttl:300,rrdatas:['199.36.153.8','199.36.153.9','199.36.153.10','199.36.153.11']});
 locals.document_job_configuration={format:'enterprise-google-document-job-v1',projectId:destination,region,bucket:r('google_storage_bucket',n,'name'),parserImage:v('parser_image'),transferImage:v('transfer_image'),workerServiceAccount:worker,vmServiceAccount:r('google_service_account',n+'_vm','email'),network:'${format("projects/%s/global/networks/%s",var.project_id,google_compute_network.'+n+'.name)}',subnetwork:'${format("projects/%s/regions/%s/subnetworks/%s",var.project_id,var.region,google_compute_subnetwork.'+n+'.name)}'};
 output.document_job_configuration={value:'${var.images_ready ? local.document_job_configuration : null}',description:'Exact runtime adapter shape; not evidence of worker wiring, crash recovery or account acceptance.',depends_on:Object.entries(resource).flatMap(([type,items])=>Object.keys(items).map(name=>type+'.'+name))};
 locals.document_executor_configuration={format:'enterprise-document-executor-v1',provider:'gcp',parserRevision:v('parser_revision'),configuration:l('document_job_configuration')};
 output.document_executor_configuration={value:'${var.images_ready ? local.document_executor_configuration : null}',description:'Owned worker envelope matching the approved parser revision; complete application hosting/export acceptance remains separate.'};
 output.document_job_artifacts={value:{repository:r('google_artifact_registry_repository',n,'repository_id'),parserRevision:v('parser_revision'),parserImage:v('parser_image'),transferImage:v('transfer_image')}};
 const main={terraform:{required_version:'>= 1.17.1, < 2.0.0',required_providers:{google:{source:'hashicorp/google',version:'7.46.2'},'google-beta':{source:'hashicorp/google-beta',version:'7.46.2'}}},provider:{google:{project:destination,region},'google-beta':{project:destination,region}},variable,locals,resource,output};
 return{...enterpriseApplicationFiles('gcp',n),'main.tf.json':JSON.stringify(main,null,2)+'\n','.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS.gcp+'\n'+CLOUD_PROVIDER_LOCKS.gcpBeta,
  'deployment.tfvars.json.example':JSON.stringify(examples,null,2)+'\n',
  'tests/document-jobs.tftest.hcl':googleDocumentJobTests(n,seed,row.region),
  'document-job-boundary.json':JSON.stringify({provider:'gcp',component:row.id,address:n,environment,region:row.region,designRevision:project.revision,scope:'Temporary parser substrate only; not the complete private assistant.',existingWorker:'Referenced, not recreated. Other existing IAM memberships are not changed.',crashRecovery:'Unfinished. Lifecycle age=1 is an asynchronous fallback request, not a maximum retention guarantee.',productionQualified:false,cloudOperations:false},null,2)+'\n',
  'README.md':'# Private Google document substrate\n\nGenerated from the owned design; this is one unfinished composition block, not a complete project. Use the same selected region, owned destination and existing question-worker identity. Terraform manages only the declared bucket, parser VM identity, custom roles, private registry/network/DNS and API prerequisites. It does not create a user website, company identity provider or document sources.\n\nThe controller gets four project-scoped Batch permissions and actAs only on the transfer VM identity. Object permissions are separate custom roles bound solely to the ephemeral bucket; the transfer VM cannot delete objects or access source/model/SQL credentials through these grants. Existing inherited permissions still require account inspection.\n\nBuild/review immutable artifacts after the foundation and set images_ready only with real build receipts. Foundation output is null; image inputs contain no synthetic published digest. Generated runtime configuration matches enterprise_google_jobs.py. Application hosting, provider/artifact binding, durable orphan recovery, key/audit operations and complete Spec Kit/export integration remain unfinished. No private capability or whole-case acceptance is implied.\n\nOrdinary completion deletes temporary input/results. Bucket versioning and soft deletion are disabled to avoid hidden retained copies. No retention lock or replication is requested. Age-one-day lifecycle is an asynchronous last-resort cleanup request; it does not provide a strict upper retention bound or replace the required reconciler. Observe organization policies and deletion propagation in the destination before release.\n\nVMs have no external IP in the emitted runtime request. Private Google Access, private googleapis.com/pkg.dev DNS, explicit private API routes, TCP443 allow rules and deny-all egress/ingress supply the substrate. Batch-container network isolation and actual VM/agent/IAM/DNS behavior require destination testing; mock plans do not prove those behaviors. No cloud apply or deployment was performed.\n'};
}
