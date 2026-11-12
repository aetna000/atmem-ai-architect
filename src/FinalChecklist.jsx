import React,{useState,useRef} from'react';
import{BrainActivity}from'./BrainActivity.jsx';
import{estimate}from'./estimate.mjs';
import{cloudMapping}from'./journey.mjs';
import{OPTION_NAMES}from'./pack.mjs';
export function FinalChecklist({project,implementation,terraform,checks=[],onNavigate}){
 const [opening,setOpening]=useState(null),[error,setError]=useState('');const navigating=useRef(false);
 async function open(name,target){if(navigating.current||!onNavigate)return;navigating.current=true;setError('');setOpening(name);
  // Let the pressed row paint before the destination’s work starts.
  await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
  try{await onNavigate(target);}catch(e){setError(e.message||'Could not open that section. Try again.');}finally{navigating.current=false;setOpening(null);}
 }
 const cost=estimate(project),mapping=cloudMapping(project),requirements=!!(project.needs?.length||project.brief?.application);
 const selectedRegion=[...(project.decisions||[])].reverse().find(d=>d.subject==='cloud.region'&&d.status==='Accepted')?.decision;
 const country=[...(project.decisions||[])].reverse().find(d=>d.subject==='data.country'&&d.status==='Accepted')?.decision;
 const proposed=project.nodes.filter(n=>n.data.kind!=='note'&&n.data.origin!=='existing');
 const placements=proposed.map(n=>n.data.config?.region).filter(r=>typeof r==='string'&&r.trim()&&!/select|unknown|tbd/i.test(r));
 const region=selectedRegion||(proposed.length&&placements.length===proposed.length?[...new Set(placements)].join(', '):null);
 const missing=[...new Set([...cost.lines.filter(l=>l.cost==null).map(l=>l.component),...cost.notCosted])];
 const costReason=cost.complete?'':missing.length?`${missing.length} unpriced component${missing.length===1?'':'s'}: ${missing.slice(0,2).map(name=>String(name).split(/\s+/).slice(0,5).join(' ')).join(', ')}${missing.length>2?'…':''}`:cost.gaps.length?'Some charges are excluded. Open costs for details.':'';
 const rows=[['Requirements',requirements?'Recorded':'Not recorded',requirements],['Cloud',mapping.provider?(OPTION_NAMES[mapping.provider]||mapping.provider):'Not selected',!!mapping.provider],['Data country',country||'Not selected',!!country],['Cloud region',region||'Choose region',!!region],['Cost estimate',cost.complete?'Calculated':cost.lines.some(l=>l.cost!=null)?'Partial · charges missing':'Not calculated',cost.complete],['Implementation',implementation?'Included':'Not generated',!!implementation],['Application checks',checks.length?checks.every(c=>c.state==='finished'&&c.result?.status==='passed')?'Passed':'Needs attention':'Not run',checks.length>0&&checks.every(c=>c.state==='finished'&&c.result?.status==='passed')],['Terraform checks',terraform?.status==='passed'?'Passed':terraform?.status==='failed'?'Failed':terraform?.status==='incomplete'?'Incomplete':'Not run',terraform?.status==='passed']];
 const targets=['requirements','location','location','location','cost','implementation','checks','checks'];
 return <section className="final-checklist" aria-label="Final checklist" aria-busy={!!opening}><h3>Final checklist</h3><ul>{rows.map(([name,status,complete],index)=><li key={name}><button type="button" onClick={()=>open(name,targets[index])} disabled={!!opening||!onNavigate} aria-label={`${name}: ${status}. Open ${name}`}><span className={complete?'check-complete':'check-pending'} aria-label={complete?'Complete':'Needs attention'}>{complete?'✓':'!'}</span><span className="checklist-label">{name}{name==='Cost estimate'&&costReason&&<small>{costReason}</small>}</span><strong>{opening===name?<>Opening… <BrainActivity/></>:status}</strong><span className="checklist-arrow" aria-hidden="true">→</span></button></li>)}</ul>{opening&&<p role="status" className="checklist-loading">Opening {opening}…</p>}{error&&<p role="alert">{error}</p>}</section>;
}
