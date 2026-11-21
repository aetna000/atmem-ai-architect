import {INVOICE_SERVICES} from './invoice-plan.mjs';
import {containerContract} from './container-contracts.mjs';
import {invoiceTerraform} from './invoice-terraform.mjs';
import {containerTerraform} from './container-terraform.mjs';
import {planCapabilityComposition,deliveryUnitProject} from './capability-composition.mjs';
import {composeTerraformUnits} from './terraform-composition.mjs';
// Reviewed domain/provider policies remain explicit adapters. The partitioner and
// linker operate on contracts and unit identities, never project names or corpus IDs.
export const DELIVERY_CAPABILITIES=Object.freeze([
 Object.freeze({id:'invoice-workflow',matches:node=>node.data.origin==='proposed'&&node.data.implementation==='invoice-workflow'&&node.data.service===INVOICE_SERVICES[node.data.provider],compile:(project,plan,environment)=>invoiceTerraform(project,plan,environment,{stateScope:'parent'})}),
 Object.freeze({id:'container-service',matches:containerContract,compile:containerTerraform}),
]);
export const capabilityCompositionPlan=(project,planProject)=>planCapabilityComposition(project,DELIVERY_CAPABILITIES,planProject);
export function compileCapabilityComposition(project,plan,planProject,environment='staging'){
 if(!['staging','production','qualification'].includes(environment))throw Error('Use an explicit supported composition environment.');
 const current=capabilityCompositionPlan(project,planProject);
 if(!current||plan.revision!==project.revision||JSON.stringify(current.composition)!==JSON.stringify(plan.composition)||JSON.stringify(current.gapDetails)!==JSON.stringify(plan.gapDetails))throw Error('The composition plan is stale; compile the latest complete design.');
 const units=current.composition.units.map(unit=>{
  const scoped=deliveryUnitProject(project,unit.id),adapter=DELIVERY_CAPABILITIES.find(c=>c.id===unit.implementation),child=planProject(scoped);
  return {id:unit.id,implementation:unit.implementation,files:adapter.compile(scoped,child,environment)};
 });
 const files=composeTerraformUnits(project,units,{environment,gaps:current.gapDetails.map(g=>g.id)});
 files['resource-schedule.json']=JSON.stringify(current,null,2)+'\n';
 return files;
}
