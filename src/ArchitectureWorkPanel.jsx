import React,{useState,useMemo} from 'react';
import {architectureWork,workContextIdentity} from './architecture-work.mjs';
import {artifactWorkProjection} from './artifact-work.mjs';
const labels={current:'Context current',changed:'Review again',missing:'Missing reference',unreviewed:'Not reviewed'};
function WorkPanel({project,onChange,busy=false}){
 const [error,setError]=useState('');
 const result=useMemo(()=>{try{return {model:project?architectureWork(project):null,artifacts:project?artifactWorkProjection(project):null};}catch(e){return {error:e.message};}},[project]);
 if(!project)return null;
 if(result.error)return <p role="alert">Work context could not be read: {result.error}</p>;
 const model=result.model;
 const intents=model.entities.filter(e=>e.kind==='intent'&&e.value?.text?.trim()).length,requirements=model.entities.filter(e=>e.kind==='requirement').length;
 const sourceName=id=>model.entities.find(e=>e.id===id)?.title||project.extensions?.architectureWork?.snapshots.findLast(s=>s.ref===id)?.value.title||id;
 const priority={changed:0,missing:0,unreviewed:1,current:2};
 const mappings=model.entities.filter(e=>['responsibility','delivery-unit','interface','implementation','assumption','decision','evidence','requirement','removed'].includes(e.kind)).sort((a,b)=>priority[a.contextStatus]-priority[b.contextStatus]);
 function apply(change){onChange(change,project.id);setError('');}
 return <details className="architecture-work"><summary>Architecture work context · {mappings.filter(e=>e.contextStatus==='changed'||e.contextStatus==='missing').length} need review</summary>
  <p>Requirements, responsibilities, interfaces and implementation mappings share their change context. A current context is a recorded review; it does not establish that an implementation or test passed.</p>
  <p>{intents} intent {intents===1?'source':'sources'} · {requirements} {requirements===1?'requirement':'requirements'}. Free-form engineering updates affect every mapping until reconciled.</p>
  {mappings.length?<ul aria-label="Architecture work mappings">{mappings.map(e=><li key={e.id} data-work-ref={e.id}>
   <strong>{e.title}</strong><span> · {e.kind} · {labels[e.contextStatus]}</span>
   {e.value&&<details><summary>Sources and mapping details</summary><pre>{JSON.stringify({value:e.value,dependsOn:e.dependsOn,review:e.review},null,2)}</pre></details>}
   {e.value?.source&&<small> · {e.value.source} · {e.value.agreement||'recorded'}</small>}
   {e.changedRefs.length>0&&<p>Changed: {e.changedRefs.map(sourceName).join(', ')}</p>}
   {e.missingRefs.length>0&&<p>Missing: {e.missingRefs.map(sourceName).join(', ')}</p>}
   {onChange&&e.contextStatus!=='missing'&&<button disabled={busy} onClick={()=>{try{apply({kind:'review',ref:e.id,expectedContext:workContextIdentity(project,e.id)});}catch(e){setError(e.message);}}}>Record context review: {e.title}</button>}
  </li>)}</ul>:<p>No responsibilities or implementation mappings recorded yet. Engineering can propose them without changing the existing diagram.</p>}
  {result.artifacts.mappings.length>0&&<section aria-label="Linked artifact mappings">
   <h3>Linked artifacts</h3><p>File and context references remain proposed. They do not establish that a test passed or that the implementation meets every requirement.</p>
   <ul>{result.artifacts.mappings.map(m=><li key={m.id} data-artifact-mapping={m.artifactId}>
    <strong>{m.contextStatus==='current'?'Saved context matches':m.contextStatus==='superseded'?'Earlier artifact retained':'Design changed; regenerate mappings'}</strong>
    <span> · {m.records.length} proposed mappings · context revision {m.contextRevision}</span>
    <details><summary>Artifact and file references</summary><pre>{JSON.stringify({artifactId:m.artifactId,artifactSha256:m.artifactSha256,contextSha256:m.contextSha256,files:m.files,changedRefs:m.changedRefs,scope:m.scope},null,2)}</pre></details>
   </li>)}</ul>
  </section>}
  {error&&<p role="alert">{error}</p>}
 </details>;
}

export const ArchitectureWorkPanel=React.memo(WorkPanel);
