import {containerContract} from './container-contracts.mjs';
import {resourceAddress} from './identifiers.mjs';
// Inspect emitted configuration independently of the allocation compiler. Exact
// quantity conversion is explicit; no platform default or rounded value is proof.
const bytes=value=>{
 if(typeof value!=='string')return NaN;
 const match=/^(\d+(?:\.\d+)?)(Mi|Gi|M|G)$/.exec(value);
 return match?Number(match[1])*({Mi:1048576,Gi:1073741824,M:1000000,G:1000000000}[match[2]]):NaN;
};
export function inspectContainerConfiguration(node,row,config,plan,add){
 const contract=containerContract(node);if(!contract)return;
 const cloud=node.data.provider,name=resourceAddress(node.id),settings=node.data.config||{},resource=config.resource||{};
 const fail=message=>add('container-constraint-mismatch',message,node.id);
 if(row.address!==name)fail('The resource schedule changed the canonical container identity.');
 const body=resource[contract.type]?.[name];if(!body)return;
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
