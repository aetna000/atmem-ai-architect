import React,{useEffect,useRef,useState} from 'react';
import {memoryCall} from './local-agent.mjs';
import {BrainActivity} from './BrainActivity.jsx';
import {reviewDesignContent} from './project-file.mjs';
import './architecture-rules.css';

async function hash(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(reviewDesignContent(value))))].map(b=>b.toString(16).padStart(2,'0')).join('');}
function basicPolicy(regions,budget,privateStorage){
 const rules={schema:'atmem-architecture/v1'};
 const allowed=regions.split(',').map(s=>s.trim()).filter(Boolean);
 if(allowed.length)rules.regions=[{id:'APPROVED-REGIONS',allowed,severity:'error'}];
 if(budget!=='')rules.budget=[{id:'MONTHLY-BUDGET',monthly_max:Number(budget),currency:'USD',severity:'error'}];
 if(privateStorage)rules.network=[{id:'PRIVATE-STORAGE',check:{resource:'aws_s3_bucket_public_access_block',attribute:'block_public_policy',must_equal:true},severity:'error'},
  {id:'PRIVATE-DATABASE',check:{resource:'aws_db_instance',attribute:'publicly_accessible',must_equal:false},severity:'error'}];
 return '---\n'+JSON.stringify(rules,null,2)+'\n---\n';
}
function basicValues(content){
 try{
  const value=JSON.parse(content.split('---')[1]);
  const regions=(value.regions?.[0]?.allowed||[]).join(', '),budget=value.budget?.[0]?.monthly_max??'';
  const privateStorage=!!value.network?.length;
  return basicPolicy(regions,String(budget),privateStorage)===content?{regions,budget:String(budget),privateStorage}:null;
 }catch{return null;}
}

export function ArchitectureRulesPanel({session,project,environment='staging',onGate,onPolicy}){
 const [policy,setPolicy]=useState(null),[review,setReview]=useState(null),[text,setText]=useState(''),[advanced,setAdvanced]=useState(false);
 const [regions,setRegions]=useState(''),[budget,setBudget]=useState(''),[privateStorage,setPrivateStorage]=useState(true);
 const [loading,setLoading]=useState(true),[working,setWorking]=useState(false),[error,setError]=useState(''),[projectHash,setProjectHash]=useState(null);
 const request=useRef(0),live=useRef(true),locked=useRef(false),edited=useRef(false),editBase=useRef(null);
 function touch(){if(!edited.current)editBase.current=policy?.revision||null;edited.current=true;}
 function hydrate(content){const values=basicValues(content);setText(content);setAdvanced(!values);if(values){setRegions(values.regions);setBudget(values.budget);setPrivateStorage(values.privateStorage);}}
 const content=advanced?text:basicPolicy(regions,budget,privateStorage),key=JSON.stringify(project);
 const dirty=!!policy&&content!==policy.content;
 const current=!!review&&review.state==='completed'&&review.projectSha256===projectHash&&review.policyRevision===policy?.revision&&review.environment===environment&&!dirty;
 const blocked=loading||working||!!error||!policy||!current||review?.report?.verdict==='fail';
 useEffect(()=>{onGate?.({projectId:project.id,blocked,reason:error||(!policy?'Save your project rules before coding.':!current?'Review the current design against your rules before coding.':review?.report?.verdict==='fail'?'Resolve the rule violations before coding.':'')});},[project.id,blocked,current,error,policy?.revision,review?.report?.verdict,onGate]);
 useEffect(()=>{let stopped=false;setProjectHash(null);void hash(project).then(v=>{if(!stopped)setProjectHash(v);}).catch(()=>{if(!stopped)setError('The project cannot be reviewed until its invalid fields are resolved.');});return()=>{stopped=true;};},[key]);
 useEffect(()=>{
  live.current=true;const controller=new AbortController();let stopped=false,timer;
  setLoading(true);setPolicy(null);setReview(null);setError('');edited.current=false;
  async function poll(){try{
   const value=await memoryCall(session,'architecture/status',{projectId:project.id},controller.signal);
   if(stopped)return;setPolicy(value.policy);setReview(value.review);if(value.policy)onPolicy?.(value.policy);
   if(value.policy&&!edited.current){hydrate(value.policy.content);editBase.current=value.policy.revision;}
   setError('');
  }catch(e){if(!stopped&&e.name!=='AbortError')setError(e.message);}finally{if(!stopped){setLoading(false);timer=setTimeout(poll,1500);}}}
  if(session?.token)void poll();else{setLoading(false);setError('Connect Architect’s local service to use AtMem rules.');}
  return()=>{stopped=true;live.current=false;controller.abort();clearTimeout(timer);};
 },[project.id,session?.token]);
 async function act(kind){
  if(locked.current)return;locked.current=true;setWorking(true);setError('');const serial=++request.current;
  try{
   if(kind==='save'){
    const value=await memoryCall(session,'architecture/rules',{projectId:project.id,content,expectedRevision:edited.current?editBase.current:policy?.revision||null});
    if(live.current&&serial===request.current){setPolicy(value);hydrate(value.content);edited.current=false;editBase.current=value.revision;setReview(null);onPolicy?.(value);}
   }else{
    const value=await memoryCall(session,'architecture/run',{projectId:project.id,project,environment});
    if(live.current&&serial===request.current)setReview(value);
   }
  }catch(e){if(live.current&&serial===request.current)setError(e.message);}finally{locked.current=false;if(live.current)setWorking(false);}
 }
 const report=review?.report;
 const status=loading?'Loading rules…':working||review?.state==='running'?'Reviewing…':!policy?'Set project rules':!current?'Review needed':({pass:'Passed',warn:'Needs review',fail:'Blocked'}[report?.verdict]||'Not reviewed');
 return <section className="architecture-rules" aria-label="Architecture rules" aria-busy={working||review?.state==='running'}>
  <header><div><h3>Project rules</h3><small>Remembered by AtMem · {policy?'Approved '+policy.revision.slice(0,8):'Not saved'}</small></div><strong role="status" className={current&&report?.verdict==='pass'?'check-complete':'check-pending'}>{status}</strong></header>
  <details open={!policy||undefined}><summary>Edit rules</summary>
   {!advanced?<div className="architecture-rule-fields">
    <label>Allowed regions<input value={regions} placeholder="e.g. ap-southeast-2" onChange={e=>{touch();setRegions(e.target.value);}}/></label>
    <label>Monthly budget (USD)<input type="number" min="0" value={budget} placeholder="Optional" onChange={e=>{touch();setBudget(e.target.value);}}/></label>
    <label className="architecture-checkbox"><input type="checkbox" checked={privateStorage} onChange={e=>{touch();setPrivateStorage(e.target.checked);}}/> Keep AWS storage and databases private</label>
   </div>:<label>Rules<textarea aria-label="Architecture policy" value={text} maxLength={12000} rows={8} onChange={e=>{touch();setText(e.target.value);}}/></label>}
   {!advanced&&<button className="link" onClick={()=>{touch();setText(content);setAdvanced(true);}}>More rule options</button>}
   <button className="btn" disabled={loading||working||!session?.token||policy?.content===content} onClick={()=>act('save')}>Save rules to AtMem</button>
   {policy&&dirty&&<button className="link" onClick={()=>{hydrate(policy.content);edited.current=false;editBase.current=policy.revision;setError('');}}>Reload saved rules</button>}
  </details>
  <div className="architecture-rule-actions"><button className="btn primary" disabled={!policy||dirty||working||loading||review?.state==='running'} onClick={()=>act('run')}>{working||review?.state==='running'?<><BrainActivity size={18}/> Reviewing…</>:'Review design against rules'}</button>
  <span className="muted small">Checks the generated Terraform draft. No deployment.</span></div>
  {review?.state==='running'&&<div className="generation-progress" role="progressbar" aria-label="Architecture rules review"><span/></div>}
  {review?.actions?.length>0&&<ol className="architecture-rule-activity" aria-label="Rules review activity">{review.actions.map((a,i)=><li key={i}>{a.text}</li>)}</ol>}
  {report&&<><p role="status">{current?`${report.violations.length} rule issues · ${report.unverified?.length||0} unresolved checks`:'Design or rules changed. Review again.'}</p>
   <ul className="architecture-rule-findings">{report.violations.map((v,i)=><li key={i}><strong>{v.rule_id}</strong> · {v.title}<details><summary>Evidence</summary><pre>{JSON.stringify(v.evidence,null,2)}</pre></details></li>)}
   {report.unverified?.map((v,i)=><li key={'u'+i}>{v.rule_id} · {v.reason}</li>)}</ul>
   <details><summary>Review report and input binding</summary><pre>{JSON.stringify(report,null,2)}</pre></details>
  </>}
  {(error||review?.error)&&<p role="alert">{error||review.error}</p>}
 </section>;
}
