import {PROVIDER_REGION_PATTERNS,validProviderRegion} from './deployment-region.mjs';
import {containerContract} from './container-contracts.mjs';
import {resourceAddress} from './identifiers.mjs';
import {inspectContainerSecurity} from './container-security-inspection.mjs';
// Inspect emitted configuration independently of the allocation compiler. Exact
// quantity conversion is explicit; no platform default or rounded value is proof.
const bytes=value=>{
 if(typeof value!=='string')return NaN;
 const match=/^(\d+(?:\.\d+)?)(Mi|Gi|M|G)$/.exec(value);
 return match?Number(match[1])*({Mi:1048576,Gi:1073741824,M:1000000,G:1000000000}[match[2]]):NaN;
};
export function inspectContainerConfiguration(node,row,config,plan,add,{root=config,scope=null}={}){
 const contract=containerContract(node);if(!contract)return;
 const cloud=node.data.provider,name=resourceAddress(node.id),settings=node.data.config||{},resource=config.resource||{};
 const fail=message=>add('container-constraint-mismatch',message,node.id);
 if(row.address!==name)fail('The resource schedule changed the canonical container identity.');
 const expectedResources=new Set(['terraform_data.review_gate',contract.type+'.'+name,...(cloud==='aws'?['aws_ecs_cluster','aws_cloudwatch_log_group','aws_iam_role','aws_iam_role_policy','aws_ecs_task_definition'].map(type=>type+'.'+name).concat('aws_iam_role.'+name+'_task'):cloud==='gcp'?['google_service_account.'+name]:[])]);
 for(const [type,entries]of Object.entries(resource))for(const id of Object.keys(entries)){if(!expectedResources.delete(type+'.'+id))fail('The supplied-image unit contains a managed resource outside its reviewed ownership footprint.');}
 if(expectedResources.size)fail('The supplied-image unit is missing a required owned resource or review gate.');
 const expectedData=cloud==='aws'?['aws_subnet','aws_security_group','aws_partition']:cloud==='azure'?['azurerm_container_app_environment']:cloud==='ibm'?['ibm_code_engine_project']:[];
 for(const [type,entries]of Object.entries(config.data||{}))for(const id of Object.keys(entries))if(!expectedData.includes(type)||id!==name)fail('The supplied-image unit queries data outside its reviewed existing-system boundary.');
 const body=resource[contract.type]?.[name];if(!body)return;
 const rawRegion=settings.region,selected=rawRegion&&rawRegion!=='To be selected'&&validProviderRegion(cloud,rawRegion)?rawRegion:null;
 const expectedValidation='${can(regex('+JSON.stringify(PROVIDER_REGION_PATTERNS[cloud])+', var.region))'+(selected?' && var.region == '+JSON.stringify(selected):'')+'}';
 if(config.variable?.region?.default!==(selected??undefined)||config.variable?.region?.validation?.condition!==expectedValidation)fail('The deployment region input does not preserve the accepted placement and supported identifier contract.');
 if(rawRegion&&rawRegion!=='To be selected'&&!selected&&!(plan.gapDetails||[]).some(g=>g.componentIds?.includes(node.id)&&g.id.endsWith('-region')))fail('Unsupported placement was discarded instead of remaining blocking scope.');
 const rootName=key=>scope?scope.module+'__'+key:key,rootRef=key=>'${var.'+rootName(key)+'}';
 const candidates=root.provider?.[contract.provider],providers=Array.isArray(candidates)?candidates:[candidates],provider=providers.find(p=>p&&(scope?p.alias===scope.module:!p.alias));
 inspectContainerSecurity(cloud,name,config,provider,rootRef,fail);
 if(!provider||cloud!=='azure'&&provider.region!==rootRef('region'))fail('The native provider is not bound to its own delivery-unit region input.');
 if(cloud==='azure'&&provider?.subscription_id!==rootRef('subscription_id'))fail('The Azure lookup and application lost their owned subscription input.');
 if(cloud==='gcp'&&provider?.project!==rootRef('project_id'))fail('The Google provider lost its reviewed project input.');
 for(const [type,entries]of Object.entries(resource))if(type!=='terraform_data')for(const item of Object.values(entries)){
  if(item.provider!==undefined&&item.provider!==contract.provider)fail('A container resource overrides its owned provider configuration.');
  if(cloud==='aws'&&item.region!==undefined&&item.region!=='${var.region}')fail('A container resource overrides its owned deployment region.');
 }
 const conditions=body.lifecycle?.precondition||[],has=condition=>Array.isArray(conditions)&&conditions.some(rule=>rule.condition===condition);
 if(cloud==='aws')for(const [type,key]of [['aws_subnet','subnets'],['aws_security_group','security_groups']]){
  const lookup=config.data?.[type]?.[name];
  if(!lookup||lookup.for_each!=='${toset(var.'+name+'_'+key+')}'||lookup.id!=='${each.value}'||Object.keys(lookup).some(key=>!['for_each','id','provider'].includes(key))||lookup.provider!==undefined&&lookup.provider!=='aws'||body.network_configuration?.[key]!=='${var.'+name+'_'+key+'}')fail('An AWS network lookup or service no longer follows its exact existing network inputs.');
  if(!has('${alltrue([for item in values(data.'+type+'.'+name+') : item.vpc_id == var.'+name+'_vpc_id])}'))fail('The AWS existing network lost its native VPC membership check.');
 }
 if(cloud==='gcp'&&body.location!=='${var.region}')fail('Cloud Run location no longer uses the accepted unit region.');
 if(cloud==='azure'){
  const existing=config.data?.azurerm_container_app_environment?.[name];
  if(!existing||existing.name!=='${try(split("/", var.environment_id)[8], "invalid")}'||existing.resource_group_name!=='${try(split("/", var.environment_id)[4], "invalid")}'||existing.provider!==undefined&&existing.provider!=='azurerm'||body.container_app_environment_id!=='${var.environment_id}')fail('The Azure existing-environment lookup no longer follows the exact selected resource ID.');
  if(!has('${lower(replace(data.azurerm_container_app_environment.'+name+'.location, " ", "")) == var.region}')||!has('${lower(data.azurerm_container_app_environment.'+name+'.id) == lower(var.environment_id)}'))fail('The Azure existing environment lost its native region or subscription/resource-ID check.');
 }
 if(cloud==='ibm'){
  const existing=config.data?.ibm_code_engine_project?.[name];
  if(!existing||existing.project_id!=='${var.code_engine_project_id}'||existing.provider!==undefined&&existing.provider!=='ibm'||body.project_id!=='${var.code_engine_project_id}')fail('The IBM existing-project lookup no longer follows the reviewed project ID.');
  if(!has('${data.ibm_code_engine_project.'+name+'.region == var.region}')||!has('${data.ibm_code_engine_project.'+name+'.account_id == var.account_id}'))fail('The IBM existing project lost its native region or account check.');
 }

 let actualMemory,privateIngress,explicitIdentity;
 if(cloud==='aws'){
  const task=resource.aws_ecs_task_definition?.[name];actualMemory=Number(task?.memory)*1048576;
  privateIngress=body.network_configuration?.assign_public_ip===false;
  explicitIdentity=!!resource.aws_iam_role?.[name]&&!!resource.aws_iam_role?.[name+'_task']&&task?.execution_role_arn==='${aws_iam_role.'+name+'.arn}'&&task?.task_role_arn==='${aws_iam_role.'+name+'_task.arn}';
  if(settings.logRetentionDays!=null&&resource.aws_cloudwatch_log_group?.[name]?.retention_in_days!==settings.logRetentionDays)fail('CloudWatch retention does not retain the explicit finite setting.');
 }else if(cloud==='azure'){
  actualMemory=bytes(body.template?.container?.memory);privateIngress=body.ingress?.external_enabled===false;explicitIdentity=body.identity?.type==='SystemAssigned';
 }else if(cloud==='gcp'){
  actualMemory=bytes(body.template?.containers?.resources?.limits?.memory);privateIngress=body.ingress==='INGRESS_TRAFFIC_INTERNAL_ONLY';explicitIdentity=!!resource.google_service_account?.[name]&&body.template?.service_account==='${google_service_account.'+name+'.email}';
 }else if(cloud==='ibm'){
  actualMemory=bytes(body.scale_memory_limit);privateIngress=body.managed_domain_mappings==='local';explicitIdentity=body.run_service_account==='none';
 }
 if(!privateIngress)fail('The private supplied-image contract gained public or implicit ingress.');
 if(!explicitIdentity)fail('The supplied-image contract lost its explicit scoped runtime identity.');
 const memoryBlocked=(plan.gapDetails||[]).some(g=>g.componentIds?.includes(node.id)&&/container-setting-.*-(memoryMb|containerMemoryBytes)$/.test(g.id));
 if(!memoryBlocked){
  const targets=[...(settings.containerMemoryBytes==null?[]:[settings.containerMemoryBytes]),...(settings.memoryMb==null?[]:[settings.memoryMb*1048576])];
  if(targets.some(expected=>actualMemory!==expected))fail('Emitted container memory does not exactly retain the explicit byte quantity.');
 }
}
