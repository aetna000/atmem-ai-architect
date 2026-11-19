import {applyBlockers} from './terraform-emulation-blockers.mjs';
import React,{useEffect,useRef,useState} from 'react';
import {Play,CheckCircle2,AlertCircle,CircleDashed,Loader2,MinusCircle,X,Download,ChevronDown,ChevronUp,RotateCw} from 'lucide-react';
import {BrainActivity} from './BrainActivity.jsx';
import {toProjectFile} from './project-file.mjs';
import {applyEmulationSummary,applyStages,APPLY_STATUS_TITLES,applyTrack,applyCaption} from './terraform-apply-emulation.mjs';

// Real Terraform CLI and provider against a loopback cloud API; the server owns generation.
export function useTerraformApplyEmulation(project,environment,session,filesKey){
  const [state,setState]=useState({running:false,events:[],report:null,key:null});
  const active=useRef(0);
  useEffect(()=>{active.current++;setState({running:false,events:[],report:null,key:null});return ()=>{active.current++;};},[filesKey]);
  async function run(){
    if(state.running)return;
    const run=++active.current,headers={'Content-Type':'application/json',Authorization:`Bearer ${session?.token}`};
    const finish=report=>{if(active.current===run)setState(s=>({...s,running:false,report,key:filesKey}));};
    setState({running:true,events:[],report:null,key:filesKey});
    try{
      toProjectFile(project);
      if(!session?.token)throw Error('Connect the local service before running apply emulation.');
      const started=await fetch('/api/terraform/emulate',{method:'POST',headers,body:JSON.stringify({project,environment}),signal:AbortSignal.timeout(30000)});
      const job=await started.json();if(!started.ok)throw Error(typeof job.detail==='string'?job.detail:'Apply emulation could not start.');
      const deadline=Date.now()+1600000;
      for(let failures=0;active.current===run;){
        if(Date.now()>deadline)throw Error('Emulation exceeded its waiting limit. No pass was recorded.');
        await new Promise(resolve=>setTimeout(resolve,600));
        const response=await fetch('/api/terraform/emulate/status',{method:'POST',headers,body:JSON.stringify({jobId:job.jobId,projectId:project.id}),signal:AbortSignal.timeout(30000)});
        if(!response.ok){if(++failures>5)throw Error('Lost contact with the emulation job; no pass was recorded.');continue;}
        const body=await response.json();
        if(active.current!==run)return;
        if(body.state==='finished'){setState(s=>({...s,events:body.events}));return finish(body.report);}
        setState(s=>({...s,events:body.events}));
      }
    }catch(error){finish({status:'failed',stages:[],resources:[],message:error.message});}
  }
  return {...state,current:state.key===filesKey,run};
}

function saveApplyReport(project,report){const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`atmem-terraform-apply-emulation-r${project.revision}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

const ICONS={passed:CheckCircle2,failed:AlertCircle,running:Loader2,pending:CircleDashed,skipped:MinusCircle};

export function TerraformApplyPanel({project,emulation,blocked,onOpenBlock}){
  const {running,events,report}=emulation;
  const stages=applyStages(events,report,running),summary=applyEmulationSummary(report);
  const title=running?'Applying on the local emulator…':report?APPLY_STATUS_TITLES[report.status]||'Apply emulation failed':'Apply on a local emulator';
  const save=()=>saveApplyReport(project,report);
  return <section className={`apply-emulation ${running?'is-running':''} ${report?'is-'+report.status:''}`} aria-label="Terraform apply emulation">
    <div className="apply-emulation-head"><div><span className="emulation-eyebrow">TERRAFORM APPLY · LOCAL EMULATOR</span><h3 aria-live="polite">{title}</h3></div>
      <button type="button" className="btn primary" disabled={running||blocked} aria-busy={running} onClick={emulation.run}><Play size={17}/> {report?'Run again':'Run apply emulation'}</button></div>
    <p className="apply-emulation-caption">{blocked?'Finish the unfinished tasks first.':report?.message||'Real Terraform and provider. Loopback cloud API. No account, credentials or cost.'}</p>
    <ApplyBlockerList report={report} project={project} onOpenBlock={onOpenBlock}/>
    {!!stages.length&&<ol className="apply-emulation-stages" aria-label="Lifecycle stages">{stages.map(stage=>{const Icon=ICONS[stage.status]||CircleDashed;return <li key={stage.name} className={stage.status}><Icon size={16} aria-hidden="true"/><span>{stage.name}</span><small>{stage.detail}</small></li>;})}</ol>}
    {summary&&<div className="apply-emulation-facts" role="status">{summary.facts.map(fact=><div key={fact.label}><strong>{fact.value}</strong><span>{fact.label}</span></div>)}</div>}
    {report&&<>
      {!!summary?.gaps.length&&<details open><summary>Emulator gaps — not a pass</summary><ul>{summary.gaps.map(gap=><li key={gap}>{gap}</li>)}</ul></details>}
      {!!summary?.failures.length&&<details open><summary>Resource errors</summary><ul>{summary.failures.map(item=><li key={item.address}><strong>{item.address}</strong><br/>{item.error}</li>)}</ul></details>}
      {!!summary?.types.length&&<details><summary>Resource types</summary><table><thead><tr><th>Type</th><th>Applied</th><th>SDK read-back</th></tr></thead><tbody>{summary.types.map(row=><tr key={row.type}><td>{row.type}</td><td>{row.applied}/{row.planned}</td><td>{row.sdkVerified||'provider refresh'}</td></tr>)}</tbody></table></details>}
      {report.stages?.filter(stage=>stage.output).map(stage=><details key={stage.name}><summary>{stage.name} output</summary><pre className="terraform-code">{stage.output}</pre></details>)}
      {!!report.boundaries?.length&&<details><summary>Still requires cloud verification</summary><ul>{report.boundaries.map((item,i)=><li key={i}>{item}</li>)}</ul></details>}
      {report.artifactDigest&&<button type="button" className="btn" onClick={save}>Download apply report (JSON)</button>}
    </>}
  </section>;
}

// Board dock: one click runs the real Terraform lifecycle; the diagram follows its events.
export function TerraformApplyDock({project,emulation,blocked,onClose,onOpenBlock}){
  const {running,events,report}=emulation;
  const [expanded,setExpanded]=useState(false);
  const track=applyTrack(events,report,running),stages=applyStages(events,report,running),summary=applyEmulationSummary(report);
  const title=running?'Applying on the local emulator…':report?APPLY_STATUS_TITLES[report.status]||'Apply emulation failed':'Rehearse terraform apply';
  const icon=(label,Icon,action,options={})=><button type="button" className={`emulation-icon ${options.active?'active':''}`} aria-label={label} title={label} onClick={action} disabled={options.disabled} aria-busy={options.busy}><Icon size={19}/></button>;
  return <aside className={`emulation-panel apply-dock ${running?'is-working':''} ${report?'is-'+report.status:''}`} aria-label="Terraform apply emulation">
    <div className="emulation-heading"><span className={`emulation-orb ${running?'working':''}`}><BrainActivity size={34} active={running}/></span><div><span className="emulation-eyebrow">EMULATE · TERRAFORM APPLY</span><h3 aria-live="polite">{title}</h3></div>{onClose&&icon('Close apply emulation',X,onClose)}</div>
    <div className="emulation-controls row">
      {icon(report?'Run apply emulation again':'Run apply emulation',report&&!running?RotateCw:Play,emulation.run,{active:true,disabled:running||blocked,busy:running})}
      {icon('Download apply report',Download,()=>saveApplyReport(project,report),{disabled:!report?.artifactDigest})}
      {icon(expanded?'Hide details':'Show details',expanded?ChevronUp:ChevronDown,()=>setExpanded(!expanded))}
    </div>
    <div className="emulation-track" aria-label="Apply emulation progress">{track.map((step,i)=><React.Fragment key={step.label}>{i>0&&<i/>}<span className={step.state}>{step.label}</span></React.Fragment>)}</div>
    {running&&<div className="emulation-progress" role="progressbar" aria-label="Running apply emulation"><span/></div>}
    <p className="emulation-caption" role="status">{blocked?'Finish the unfinished tasks first.':applyCaption(events,report,running)}</p>
    <ApplyBlockerList report={report} project={project} onOpenBlock={onOpenBlock}/>
    {summary&&!running&&<div className="apply-emulation-facts compact">{summary.facts.slice(0,3).map(fact=><div key={fact.label}><strong>{fact.value}</strong><span>{fact.label}</span></div>)}</div>}
    {expanded&&<div className="emulation-evidence">
      {!!stages.length&&<ol className="apply-emulation-stages" aria-label="Lifecycle stages">{stages.map(stage=>{const Icon=ICONS[stage.status]||CircleDashed;return <li key={stage.name} className={stage.status}><Icon size={16} aria-hidden="true"/><span>{stage.name}</span><small>{stage.detail}</small></li>;})}</ol>}
      {!!summary?.gaps.length&&<details open><summary>Emulator gaps — not a pass</summary><ul>{summary.gaps.map(gap=><li key={gap}>{gap}</li>)}</ul></details>}
      {!!summary?.failures.length&&<details open><summary>Resource errors</summary><ul>{summary.failures.map(item=><li key={item.address}><strong>{item.address}</strong><br/>{item.error}</li>)}</ul></details>}
      {!!report?.boundaries?.length&&<details><summary>Still requires cloud verification</summary><ul>{report.boundaries.map((item,i)=><li key={i}>{item}</li>)}</ul></details>}
      {!stages.length&&<p>Real Terraform CLI and provider run against a private loopback AWS API. Blocks light up as their resources are created.</p>}
    </div>}
  </aside>;
}

function ApplyBlockerList({report,project,onOpenBlock}){
 const rows=applyBlockers(report);if(!rows.length)return null;
 const nodes=new Map(project.nodes.map(n=>[n.id,n]));
 return <section className="apply-blockers" aria-label="Gaps blocking emulation"><h4>{rows.length} {rows.length===1?'gap':'gaps'} to resolve</h4><ol>{rows.map((row,index)=>{
  const ids=[...new Set([...(row.componentIds||[]),...(row.edgeIds||[]).flatMap(id=>{const edge=project.edges.find(e=>e.id===id);return edge?[edge.source,edge.target]:[];})])];
  return <li key={String(row.id)+'-'+index}><p>{row.message}</p>{row.action&&<p className="apply-blocker-action">{row.action}</p>}{ids.map(id=>nodes.has(id)&&(onOpenBlock?<button key={id} className="link" onClick={()=>onOpenBlock(id)}>Open {nodes.get(id).data.label}</button>:<small key={id}>{nodes.get(id).data.label}</small>))}{row.taskId&&<small>Task: {row.taskId}</small>}</li>;
 })}</ol></section>;
}
