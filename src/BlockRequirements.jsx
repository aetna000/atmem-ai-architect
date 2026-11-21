import React,{useState} from 'react';
function RequirementCard({requirement,busy,onSave}){
 const [editing,setEditing]=useState(false),[text,setText]=useState(requirement.statement),[error,setError]=useState('');
 async function save(e){e.preventDefault();try{await onSave(requirement.id,text);setEditing(false);setError('');}catch(e){setError(e.message);}}
 return <article className="block-requirement" aria-label={`Requirement ${requirement.id}`}>
  {editing?<form onSubmit={save}><label>Requirement<textarea aria-label="Requirement text" maxLength={1000} value={text} onChange={e=>setText(e.target.value)}/></label><div className="block-review-actions"><button className="btn primary" disabled={busy||!text.trim()}>Save & re-evaluate</button><button type="button" className="btn ghost" disabled={busy} onClick={()=>setEditing(false)}>Cancel</button></div>{error&&<p role="alert">{error}</p>}</form>:<><p>{requirement.statement}</p><button className="link" disabled={busy} onClick={()=>{setText(requirement.statement);setEditing(true);}}>Edit requirement</button></>}
  {requirement.measure&&<small>Acceptance target: {requirement.measure.metric} {requirement.measure.op} {String(requirement.measure.target)} {requirement.measure.unit}</small>}
 </article>;
}
export function BlockRequirements({project,nodeId,busy,onSave}){
 const needs=(project.needs||[]).filter(r=>r.links?.includes(nodeId));
 return <section className="block-requirements" aria-label="Block requirements"><strong>Requirements for this block</strong>{needs.length?needs.map(r=><RequirementCard key={r.id} requirement={r} busy={busy} onSave={onSave}/>):<p className="muted">No requirements linked yet.</p>}<small>Saving updates local checks and requests an Architect review when connected. Linked blocks will need review again.</small></section>;
}
