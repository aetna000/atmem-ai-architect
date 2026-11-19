import{review,blockers}from'./review.mjs';
// Describe the exact generated gate. Never remove or resolve an unfinished item.
export function describeTerraformBlockers(files,project){
 const config=JSON.parse(files['main.tf.json']),schedule=files['resource-schedule.json']?JSON.parse(files['resource-schedule.json']):{};
 const details=new Map((schedule.gapDetails||[]).map(row=>[row.id,row]));
 const findings=blockers(review(project));
 return(config.locals?.unfinished_work||[]).map(id=>{
  const detail=details.get(id);if(detail)return{...detail,action:detail.action||(String(id).startsWith('access-')?'Define the caller identity and access permissions.':String(id).startsWith('connection-')?'Define the interface, permissions and integration test.':String(id).startsWith('container-setting-')?'Update this component’s runtime configuration.':'Define the implementation and deployment mapping; add generator support where required.')};
  const match=/^architecture review blocker (\d+)$/.exec(String(id));const finding=match?findings[Number(match[1])-1]:null;
  if(finding)return{id,message:finding.statement,action:finding.action,componentIds:finding.components||[],rule:finding.rule};
  if(id==='provider-workload-implementation-required')return{id,message:'This workload has no complete Terraform compiler for its selected deployment.',action:'Add generator support or supply a supported deployment mapping.',category:'generator_support'};
  return{id,message:String(id),action:'Review this item in the generated resource schedule and architecture findings.'};
 });
}
export function applyBlockers(report){
 if(!report)return[];
 const details=new Map((report.blockerDetails||[]).map(row=>[row.id,row]));
 const ids=report.blockers||report.blockerDetails?.map(row=>row.id)||[];
 return ids.map(id=>details.get(id)||{id,message:String(id)});
}
