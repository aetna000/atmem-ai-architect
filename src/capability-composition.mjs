import {existingDeployment} from './deployment-ownership.mjs';
import {deliveryUnitName} from './terraform-composition.mjs';
// Partition only explicit implementation contracts. This core knows no business
// domain, provider, service spelling or evaluation project identity.
export function deliveryUnitProject(project,id){
 const owner=project.nodes.find(n=>n.id===id);if(!owner)throw Error('Delivery-unit owner is absent from the current design.');
 const neighbors=new Set(project.edges.filter(e=>e.source===id||e.target===id).flatMap(e=>[e.source,e.target]));
 const nodes=project.nodes.filter(n=>n.id===id||neighbors.has(n.id)&&n.data.kind!=='note'&&existingDeployment(n));
 const ids=new Set(nodes.map(n=>n.id));
 return {...project,nodes,edges:project.edges.filter(e=>ids.has(e.source)&&ids.has(e.target))};
}
export function planCapabilityComposition(project,contracts,planProject){
 if(new Set(project.nodes.map(n=>n.id)).size!==project.nodes.length||new Set(project.edges.map(e=>e.id)).size!==project.edges.length)throw Error('Composition requires unique component and interface identities.');
 if(!Array.isArray(contracts)||new Set(contracts.map(c=>c.id)).size!==contracts.length)throw Error('Use uniquely registered capability contracts.');
 const units=[],ambiguous=[];
 for(const node of project.nodes){
  if(node.data.kind==='note'||existingDeployment(node))continue;
  const matches=contracts.filter(c=>c.matches(node));
  if(matches.length>1){ambiguous.push(node.id);continue;}
  if(matches.length===1)units.push({id:node.id,implementation:matches[0].id,module:deliveryUnitName(node.id),path:'units/'+deliveryUnitName(node.id)});
 }
 if(units.length<2)return null; // Preserve established standalone adapters.
 if(units.length>64)throw Error('A composition exceeds 64 delivery units; no unit was discarded.');
 units.sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
 const base=planProject(project),children=units.map(unit=>{const scoped=deliveryUnitProject(project,unit.id);return {unit,project:scoped,plan:planProject(scoped)};});
 const claimed=new Map(),generatedEdges=new Set(),gapDetails=[];
 for(const {unit,plan,project:scoped}of children){
  const row=plan.rows.find(row=>row.id===unit.id);if(!row?.implemented)throw Error('Registered capability did not implement its declared delivery-unit owner: '+unit.id);
  claimed.set(unit.id,{...row,module:unit.module,modulePath:unit.path});
  for(const edge of plan.connections)if(edge.generated){if(!scoped.edges.some(e=>e.id===edge.id))throw Error('A capability claimed an interface outside its declared unit boundary.');generatedEdges.add(edge.id);}
  for(const gap of plan.gapDetails)gapDetails.push({...gap,id:unit.module+':'+gap.id});
 }
 const rows=base.rows.map(row=>claimed.get(row.id)||(row.existing?row:{...row,implemented:false,terraform:'This preserved component needs a registered composable implementation contract'}));
 for(const row of rows)if(!row.implemented)gapDetails.push({id:'resource-'+row.address,message:row.label+': '+row.terraform+'.',componentIds:[row.id]});
 for(const id of ambiguous)gapDetails.push({id:'ambiguous-capability-'+deliveryUnitName(id),message:'Multiple implementation contracts claim the same component; resolve the contract instead of choosing by order.',componentIds:[id]});
 const connections=project.edges.map(edge=>({id:edge.id,source:edge.source,target:edge.target,data:edge.label||'data',generated:generatedEdges.has(edge.id),status:generatedEdges.has(edge.id)?'Typed unit boundary/source generated; runtime and destination acceptance remain required':'Preserved integration needs a composable implementation and acceptance contract'}));
 for(const edge of connections)if(!edge.generated)gapDetails.push({id:'connection-'+deliveryUnitName(edge.id),message:'Implement the preserved integration '+edge.source+' → '+edge.target+'.',edgeIds:[edge.id]});
 const unique=[...new Map(gapDetails.map(g=>[g.id,g])).values()];
 const plan={...base,rows,connections,gapDetails:unique,gaps:unique.map(g=>g.message),composition:{version:1,units},scope:'Explicit capability units with preserved external ownership and unresolved scope. Generated module structure is not application/runtime/destination acceptance.'};
 // An old whole-project adapter cannot claim unrelated implementation subplans.
 for(const [key,value]of Object.entries(base))if(key.endsWith('Plan')&&value&&typeof value==='object')plan[key]=Object.fromEntries(Object.entries(value).map(([name,entries])=>[name,Array.isArray(entries)?[]:entries]));
 plan.invoicePlan={entries:children.flatMap(({plan})=>plan.invoicePlan?.entries||[]).map(entry=>({...entry,row:claimed.get(entry.row.id)||entry.row})),componentIds:children.flatMap(({plan})=>plan.invoicePlan?.componentIds||[]),edgeIds:children.flatMap(({plan})=>plan.invoicePlan?.edgeIds||[])};
 return plan;
}
