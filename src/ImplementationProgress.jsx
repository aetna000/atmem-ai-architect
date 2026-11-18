import React,{useEffect,useMemo,useState} from 'react';
import {engineeringCall} from './engineering-client.mjs';
import {artifactWorkProjection} from './artifact-work.mjs';

export function ImplementationProgress({project,session,job,artifact}){
 const [checks,setChecks]=useState([]),[error,setError]=useState(''),[review,setReview]=useState(null),[reviewError,setReviewError]=useState('');
 const [specification,setSpecification]=useState(null);
 useEffect(()=>{
  setSpecification(null);if(!job)return;
  const controller=new AbortController();let stopped=false,timer;
  async function poll(){try{const value=await engineeringCall(session,'specification',{projectId:project.id,sessionId:job.id},{signal:controller.signal});if(!stopped)setSpecification(value);}catch(e){if(!stopped&&e.name!=='AbortError')setSpecification(null);}finally{if(!stopped)timer=setTimeout(poll,1500);}}
  void poll();return()=>{stopped=true;controller.abort();clearTimeout(timer);};
 },[project.id,session?.token,job?.id]);
 useEffect(()=>{
  setReview(null);setReviewError('');if(!job||!artifact||artifact.runId!==job.run||['running','starting'].includes(job.state))return;
  const controller=new AbortController();let stopped=false;
  engineeringCall(session,'architecture-review',{projectId:project.id,sessionId:job.id,artifactId:artifact.id},{signal:controller.signal}).then(value=>{if(!stopped)setReview(value);}).catch(e=>{if(!stopped&&e.name!=='AbortError')setReviewError(e.message);});
  return()=>{stopped=true;controller.abort();};
 },[project.id,project.extensions?.architecturePolicy?.revision,session?.token,job?.id,job?.run,job?.state,artifact?.id]);
 useEffect(()=>{
  setChecks([]);setError('');if(!job||!artifact)return;
  const controller=new AbortController();let stopped=false,timer;
  async function poll(){try{
   const value=await engineeringCall(session,'validation/list',{projectId:project.id,sessionId:job.id,artifactId:artifact.id},{signal:controller.signal});
   if(!stopped){setChecks(value.checks||[]);setError(value.memoryStatus==='unavailable'?'Restore AtMem to remember these check results.':'');}
  }catch(e){if(!stopped&&e.name!=='AbortError')setError('Check evidence is unavailable.');}
  finally{if(!stopped)timer=setTimeout(poll,1500);}}
  void poll();return()=>{stopped=true;controller.abort();clearTimeout(timer);};
 },[project.id,session?.token,job?.id,artifact?.id]);
 const coverage=useMemo(()=>{try{return artifactWorkProjection(project).coverage;}catch{return [];}},[project]);
 const taskLinks=useMemo(()=>{const links=new Map();try{for(const mapping of artifactWorkProjection(project).mappings.filter(m=>m.contextStatus==='current'&&m.artifactId===artifact?.id&&m.contextSha256===specification?.contextSha256))for(const record of mapping.records)for(const id of record.data?.specTaskIds||[]){const value=links.get(id)||{files:new Set(),code:false};for(const path of record.data.files||[])value.files.add(path);value.code||=record.kind==='implementation';links.set(id,value);}}catch{}return links;},[project,artifact?.id,specification?.contextSha256]);
 const files=artifact?.files?.filter(f=>f.kind==='file')||[];
 const supplied=new Set(Object.keys(artifact?.pinnedInputs||{}));
 const outputFiles=files.filter(f=>!supplied.has(f.path)&&!f.path.startsWith('atmem-inputs/'));
 const previous=!!artifact&&(artifact.runId!==job?.run||['starting','running'].includes(job?.state));
 const specs=files.filter(f=>/(^|\/)(spec-kit|specs)\//.test(f.path));
 const code=outputFiles.filter(f=>/\.(py|js|mjs|jsx|ts|tsx|go|rs|java|cs)$/.test(f.path)&&!/(^|\/)(tests?|spec-kit|specs|atmem-tools)\//.test(f.path));
 const infra=outputFiles.filter(f=>/\.tf(\.json)?$/.test(f.path));
 const latest=[...new Map(checks.map(c=>[c.validatorId,c])).values()];
 const passed=latest.filter(c=>c.state==='finished'&&c.result?.status==='passed');
 const failed=latest.filter(c=>c.state==='finished'&&c.result?.status!=='passed');
 const checking=latest.some(c=>c.state!=='finished');
 const currentReview=review?.state==='completed'&&review.policyRevision===project.extensions?.architecturePolicy?.revision&&review.artifactId===artifact?.id&&review.artifactSha256===artifact?.sha256;
 const items=[['Spec Kit',specification?`${specification.tasks.length} tasks defined`:specs.length?`${specs.length} captured files`:'Awaiting specification files'],['Code',code.length?`${code.length} captured files`:'Awaiting implementation'],
  ['Tests',error||failed.length?error||`${failed.length} checks need attention`:checking?'Checks running':passed.length?`${passed.length} checks passed`:'No test evidence yet'],['Infrastructure',review?!currentReview?'Rules changed · review needed':({pass:'Rules passed · static check',warn:'Unresolved infrastructure checks',fail:'Rule violations found'}[review.report.verdict]):infra.length?`${infra.length} Terraform files · draft`:'Awaiting infrastructure files']];
 return <section className="implementation-progress" aria-label="Specification to implementation progress">
  <div className="implementation-stages">{items.map(([name,state],i)=><article key={name} data-state={previous?'stale':i===2&&passed.length&&!failed.length?'checked':'pending'}><span>{i+1}</span><div><strong>{name}</strong><small>{previous?'Previous snapshot · '+state:state}</small></div></article>)}</div>
  {specification&&<details open><summary>Spec Kit tasks · {specification.tasks.length}</summary><ul className="specification-task-progress">{specification.tasks.map(task=>{const linked=taskLinks.get(task.id);return <li key={task.id}><span aria-hidden="true">{linked?'◐':'○'}</span><div><strong>{task.id}</strong> {task.title}<small>{linked?`${linked.files.size} files linked · acceptance needs evidence`:'Planned · no current implementation binding'}</small></div></li>;})}</ul></details>}
  {coverage.length>0&&<details><summary>Specification and subsystem bindings · {coverage.filter(c=>c.status==='file_reference_linked').length}/{coverage.length} linked</summary>
   <ul>{coverage.map(c=><li key={c.ref}><strong>{c.title}</strong> · {c.status==='file_reference_linked'?'Files linked · acceptance needs evidence':'Not linked'}{c.references.length>0&&<small>{[...new Set(c.references.flatMap(r=>r.files))].join(', ')}</small>}</li>)}</ul>
  </details>}
  {review&&<details><summary>{currentReview?'Generated infrastructure rule results':'Earlier infrastructure rule results'}</summary><p>{review.fileCount} captured files checked against approved rules.</p><ul>{review.report.violations.map((v,i)=><li key={i}>{v.rule_id} · {v.title}</li>)}{review.report.unverified.map((u,i)=><li key={'u'+i}>{u.rule_id} · {u.reason}</li>)}</ul></details>}
  {reviewError&&<p role="status">Infrastructure review: {reviewError}</p>}
 </section>;
}
