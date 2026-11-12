import React from'react';
import{estimate}from'./estimate.mjs';
import{cloudMapping}from'./journey.mjs';
export function FinalChecklist({project,implementation,terraform,checks=[]}){
 const cost=estimate(project),mapping=cloudMapping(project),requirements=!!(project.needs?.length||project.brief?.application);
 const rows=[['Requirements',requirements?'Recorded':'Not recorded',requirements],['Cloud and region',mapping.ready?'Selected':'Unresolved',mapping.ready],['Cost estimate',cost.complete?'Calculated':cost.lines.some(l=>l.cost!=null)?'Partial · charges missing':'Not calculated',cost.complete],['Implementation',implementation?'Included':'Not generated',!!implementation],['Application checks',checks.length?checks.every(c=>c.state==='finished'&&c.result?.status==='passed')?'Passed':'Needs attention':'Not run',checks.length>0&&checks.every(c=>c.state==='finished'&&c.result?.status==='passed')],['Terraform checks',terraform?.status==='passed'?'Passed':terraform?.status==='failed'?'Failed':terraform?.status==='incomplete'?'Incomplete':'Not run',terraform?.status==='passed']];
 return <section className="final-checklist" aria-label="Final checklist"><h3>Final checklist</h3><ul>{rows.map(([name,status,complete])=><li key={name}><span className={complete?'check-complete':'check-pending'} aria-label={complete?'Complete':'Needs attention'}>{complete?'✓':'!'}</span><span>{name}</span><strong>{status}</strong></li>)}</ul></section>;
}
