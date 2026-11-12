import React from'react';
import{estimate}from'./estimate.mjs';
import{cloudMapping}from'./journey.mjs';
import{OPTION_NAMES}from'./pack.mjs';
export function FinalChecklist({project,implementation,terraform,checks=[],onNavigate}){
 const cost=estimate(project),mapping=cloudMapping(project),requirements=!!(project.needs?.length||project.brief?.application);
 const selectedRegion=[...(project.decisions||[])].reverse().find(d=>d.subject==='cloud.region'&&d.status==='Accepted')?.decision;
 const country=[...(project.decisions||[])].reverse().find(d=>d.subject==='data.country'&&d.status==='Accepted')?.decision;
 const proposed=project.nodes.filter(n=>n.data.kind!=='note'&&n.data.origin!=='existing');
 const placements=proposed.map(n=>n.data.config?.region).filter(r=>typeof r==='string'&&r.trim()&&!/select|unknown|tbd/i.test(r));
 const region=selectedRegion||(proposed.length&&placements.length===proposed.length?[...new Set(placements)].join(', '):null);
 const rows=[['Requirements',requirements?'Recorded':'Not recorded',requirements],['Cloud',mapping.provider?(OPTION_NAMES[mapping.provider]||mapping.provider):'Not selected',!!mapping.provider],['Data country',country||'Not selected',!!country],['Cloud region',region||'Choose region',!!region],['Cost estimate',cost.complete?'Calculated':cost.lines.some(l=>l.cost!=null)?'Partial · charges missing':'Not calculated',cost.complete],['Implementation',implementation?'Included':'Not generated',!!implementation],['Application checks',checks.length?checks.every(c=>c.state==='finished'&&c.result?.status==='passed')?'Passed':'Needs attention':'Not run',checks.length>0&&checks.every(c=>c.state==='finished'&&c.result?.status==='passed')],['Terraform checks',terraform?.status==='passed'?'Passed':terraform?.status==='failed'?'Failed':terraform?.status==='incomplete'?'Incomplete':'Not run',terraform?.status==='passed']];
 const targets=['requirements','location','location','location','cost','implementation','checks','checks'];
 return <section className="final-checklist" aria-label="Final checklist"><h3>Final checklist</h3><ul>{rows.map(([name,status,complete],index)=><li key={name}><button type="button" onClick={()=>onNavigate?.(targets[index])} aria-label={`${name}: ${status}. Open ${name}`}><span className={complete?'check-complete':'check-pending'} aria-label={complete?'Complete':'Needs attention'}>{complete?'✓':'!'}</span><span>{name}</span><strong>{status}</strong><span className="checklist-arrow" aria-hidden="true">→</span></button></li>)}</ul></section>;
}
