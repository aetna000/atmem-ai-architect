import {existingDeployment} from './deployment-ownership.mjs';
import {resourceAddress} from './identifiers.mjs';
import {validateExternalReferences,externalIdentity} from './external-identities.mjs';
// State adoption/moves/removal are distinct authorized operations. No current
// adapter implements them. Observed state metadata must remain reference-only.
export function inspectOwnership(project,configs,add){
 validateExternalReferences(project);
 const preserved=project.nodes.filter(n=>n.data.kind!=='note'&&existingDeployment(n));
 for(const scope of configs){
  const config=scope.config;
  for(const key of ['import','moved','removed'])if(config[key]!==undefined)add('ownership-transition-unreviewed','State '+key+' instructions are outside current reviewed adapter ownership. Preserve references and require an explicit implementation/authorization contract.');
  for(const [type,entries]of Object.entries(config.resource||{}))if(type!=='terraform_data')for(const name of Object.keys(entries)){
   const owner=preserved.find(n=>name===resourceAddress(n.id)||name.startsWith(resourceAddress(n.id)+'_'));
   if(owner)add('existing-resource-managed','A preserved external component gained a managed resource address: '+(scope.prefix||'')+type+'.'+name+'.',owner.id);
  }
 }
}
export function ownershipInventory(project,configs){
 validateExternalReferences(project);
 return {version:1,designRevision:project.revision,stateAdoptionSupported:false,migrationAuthorized:false,components:project.nodes.filter(n=>n.data.kind!=='note').map(n=>({id:n.id,provider:n.data.provider,origin:n.data.origin||'proposed',deploymentMode:n.data.deploymentMode||null,disposition:existingDeployment(n)?'reference_only':n.data.origin==='existing'?'existing_source_new_deployment':'new_deployment',externalIdentity:externalIdentity(project,n.id),managedAddresses:configs.flatMap(scope=>Object.entries(scope.config.resource||{}).filter(([type])=>type!=='terraform_data').flatMap(([type,items])=>Object.keys(items).filter(name=>name===resourceAddress(n.id)||name.startsWith(resourceAddress(n.id)+'_')).map(name=>(scope.prefix||'')+type+'.'+name)))})),boundary:'Generated address/provenance inventory, not resource discovery, effective permissions, state adoption, migration approval or runtime behavior.'};
}
export function applyOwnershipTasks(emitted,tasks){
 if(!emitted['deployment-ownership.json'])return;
 for(const task of tasks.filter(t=>t.id.startsWith('TASK-RESOURCE-'))){
  task.files=[...new Set([...(task.files||[]),'terraform/deployment-ownership.json'])];
  task.steps.unshift('Read terraform/deployment-ownership.json for this component. Preserve reference-only/observed state provenance separately from existing application source/new deployment. URNs are not native import IDs. No state import, move or removal is implemented or authorized by this inventory; adoption requires its own reviewed capability and separate authorization.');
 }
}
