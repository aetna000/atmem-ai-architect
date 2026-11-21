// Reuse user-accepted placement without asking for the same fact on every block.
// This does not verify regional service availability or invent a residency decision.
export function prefillAcceptedSettings(project){
 const accepted=subject=>(project.decisions||[]).filter(d=>d.subject===subject&&d.status==='Accepted').at(-1)?.decision;
 const region=accepted('cloud.region'),provider=accepted('platform.cloud')||project.provider;
 if(typeof region!=='string'||!region.trim()||!['aws','azure','gcp','ibm'].includes(provider))return project;
 const applied=[];
 const nodes=project.nodes.map(n=>{
  const d=n.data,current=d.config?.region;
  if(d.kind==='note'||d.provider!==provider||(d.origin==='existing'&&d.deploymentMode!=='create')||(current&&!/^(to be selected|unknown|undecided|tbd)$/i.test(current.trim())))return n;
  applied.push({componentId:n.id,field:'config.region',value:region,basis:'User-accepted project cloud.region decision'});
  return {...n,data:{...d,config:{...d.config,region}}};
 });
 if(!applied.length)return project;
 const previous=(project.extensions?.engineeringDefaults||[]).filter(x=>!applied.some(a=>a.componentId===x.componentId&&a.field===x.field));
 return {...project,nodes,extensions:{...project.extensions,engineeringDefaults:[...previous,...applied]}};
}
