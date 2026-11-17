import React,{useEffect,useRef,useState} from 'react';
import {Download,ExternalLink,LoaderCircle,RefreshCw,Square} from 'lucide-react';

const terminal=new Set(['published_proposals','needs_attention','reconciliation_required','inspect_recorded_actions']);
const download=(value)=>{const u=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='atmem-publication-preview.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};

export default function PublicationPanel({session,project,campaign,onCampaign}){
 const scope=project.id+':'+campaign.id,storage='atmem-github-'+scope;
 const owner=useRef(scope),mounted=useRef(false);owner.current=scope;
 const [caps,setCaps]=useState(null),[connections,setConnections]=useState([]),[mapping,setMapping]=useState({}),[review,setReview]=useState(null),[accepted,setAccepted]=useState(false),[status,setStatus]=useState(null),[proposals,setProposals]=useState([]),[tag,setTag]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const active=['queued','running'].includes(status?.status),result=campaign.result;
 const roots=result?[result.module,...Object.keys(result.consumers||{})]:[];
 const merged=new Set(result?.observedMergedConsumers||[]);
 const wave=campaign.status==='module_release_pending'&&!merged.size?'module':'consumers';
 const ready=wave==='module'?campaign.status==='module_release_pending':campaign.status==='local_release_checked'&&result?.release?.observation==='github_authenticated_tag';
 const targetRoots=wave==='module'?[result?.module]:Object.keys(result?.consumers||{}).filter(id=>!merged.has(id));
 const live=()=>mounted.current&&owner.current===scope;
 const request=async(path,body,headers={})=>{
  const r=await fetch('/api/maintenance/github'+path,{method:body===undefined?'GET':'POST',signal:AbortSignal.timeout(120000),headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`,...headers},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const v=await r.json();if(!r.ok)throw Error(typeof v.detail==='string'?v.detail:'Request failed. Review the recorded state.');return v;
 };
 const act=async(fn)=>{setBusy(true);setError('');try{await fn();}catch(e){if(live())setError(e.message);}finally{if(live())setBusy(false);}};
 const refreshCampaign=async()=>{const r=await fetch('/api/maintenance/campaigns/'+campaign.id,{headers:{Authorization:`Bearer ${session.token}`}});const v=await r.json();if(!r.ok)throw Error('Reload campaign evidence before continuing.');if(live()&&v.aggregate.id===campaign.id&&v.aggregate.projectId===project.id)onCampaign(v);};
 const refreshConnections=async()=>{const v=await request('/connections?projectId='+encodeURIComponent(project.id));if(live())setConnections(v.connections);};
 const refreshProposals=async()=>{const v=await request('/campaigns/'+campaign.id+'/proposals?projectId='+encodeURIComponent(project.id));if(live()){setProposals(v.proposals||[]);if(v.status&&v.status!==campaign.status)await refreshCampaign();}};
 useEffect(()=>{mounted.current=true;act(async()=>{
  const capability=await request('/capabilities');if(!live())return;setCaps(capability);if(!capability.enabled)return;
  await refreshConnections();
  const stored=JSON.parse(localStorage.getItem(storage)||'{}');if(live())setMapping(stored.mapping||{});
  if(stored.preview){const v=await request('/previews/'+stored.preview+'/review?projectId='+encodeURIComponent(project.id));const s=await request('/previews/'+stored.preview+'?projectId='+encodeURIComponent(project.id));if(live()){setReview(v);setStatus(s);}}
  await refreshProposals();
 });return()=>{mounted.current=false;};},[scope,session?.token]);
 useEffect(()=>{if(review&&review.resultDigest!==result?.digest)setAccepted(false);},[result?.digest,review?.id]);
 useEffect(()=>{if(!active||!review)return;let stop=false,timer;const poll=async()=>{try{const s=await request('/previews/'+review.id+'?projectId='+encodeURIComponent(project.id));if(!stop&&live()){setStatus(s);if(terminal.has(s.status))await refreshProposals();}}catch(e){if(!stop&&live())setError(e.message);}finally{if(!stop)timer=setTimeout(poll,1200);}};timer=setTimeout(poll,400);return()=>{stop=true;clearTimeout(timer);};},[active,review?.id]);
 const mapped=id=>{const [connection,repository]=(mapping[id]||'').split('|');return connection&&repository&&connections.some(c=>c.id===connection&&Object.hasOwn(c.repositories,repository))?{root:id,connection,repository}:null;};
 const change=(id,value)=>{const next={...mapping,[id]:value};setMapping(next);localStorage.setItem(storage,JSON.stringify({mapping:next,preview:null}));setReview(null);setAccepted(false);};
 const preview=()=>act(async()=>{
  const v=await request('/campaigns/'+campaign.id+'/preview',{projectId:project.id,campaignId:campaign.id,wave,targets:targetRoots.map(mapped)});
  const summary=await request('/previews/'+v.id+'/review?projectId='+encodeURIComponent(project.id));if(live()){setReview(summary);setAccepted(false);setStatus(null);localStorage.setItem(storage,JSON.stringify({mapping,preview:v.id}));}
 });
 const publish=()=>act(async()=>{
  const grant=await request('/previews/'+review.id+'/authorize',{projectId:project.id,previewDigest:review.digest,automationAccepted:accepted});
  const s=await request('/previews/'+review.id+'/publish',{projectId:project.id,previewDigest:review.digest,authorizationId:grant.id},{'Idempotency-Key':crypto.randomUUID()});if(live()){setStatus(s);setAccepted(false);if(terminal.has(s.status))await refreshProposals();}
 });
 const observe=()=>act(async()=>{const target=mapped(result.module);const v=await request('/campaigns/'+campaign.id+'/observe-release',{projectId:project.id,expectedProjectRevision:campaign.revision,graphDigest:campaign.graph.digest,computeConfirmed:true,connection:target.connection,repository:target.repository,tag},{'Idempotency-Key':crypto.randomUUID()});if(live()){onCampaign(v);setReview(null);setAccepted(false);}});
 if(!caps?.enabled||!result)return null;
 const done=status?.operations?.filter(o=>o.state==='confirmed').length||0,total=review?.actions.length||0;
 return <section className="maintenance-progress publication-panel" aria-label="GitHub proposals">
  <h3>GitHub proposals</h3><p>Publish reviewed draft PRs in separate module and consumer waves. No merges or deployment.</p>
  {caps.acceptancePending&&<p className="muted">Developer acceptance mode · real GitHub qualification is pending.</p>}
  {error&&<div role="alert"><p className="maintenance-error">Review needs attention.</p><details><summary>Details</summary><pre>{error}</pre></details></div>}
  <details open={!connections.length}><summary>Connect selected repositories</summary><p>Run this command in Terminal. Tokens stay in your OS keychain.</p><code>atmem-architect --maintenance-github</code><div className="maintenance-actions"><button className="btn" onClick={()=>navigator.clipboard.writeText(project.id)}>Copy project ID</button><button className="btn" disabled={busy||active} onClick={()=>act(refreshConnections)}><RefreshCw size={14}/>Refresh connections</button></div></details>
  {!!connections.length&&<details open={!review}><summary>Repository mapping</summary><div className="campaign-form">{roots.map(id=><label key={id}>{id}<select aria-label={'GitHub repository for '+id} value={mapping[id]||''} disabled={busy||active} onChange={e=>change(id,e.target.value)}><option value="">Choose selected repository</option>{connections.flatMap(c=>Object.keys(c.repositories).map(repo=><option key={c.id+repo} value={c.id+'|'+repo}>{repo} · {c.tokenOwnerLogin}</option>))}</select></label>)}</div></details>}
  {!active&&ready&&<button className="btn primary" disabled={busy||!targetRoots.length||!targetRoots.every(id=>mapped(id))} onClick={preview}>{wave==='module'?'Review module PR':'Review remaining consumer PRs'}</button>}
  {review&&<div className="publication-review">{review.resultDigest!==result.digest&&<p className="maintenance-error">Inputs changed. Reconcile prior writes and review a fresh wave.</p>}<h3>{review.wave==='module'?'Module wave':'Consumer wave'}</h3>
   {review.targets.map(t=><div className="publication-target" key={t.root}><strong>{t.repository}</strong><span>{t.files.length} files · {t.branch}</span><details><summary>Exact source and patch</summary><p>Base: <code>{t.baseCommit}</code></p><p>Patch: <code>{t.patchDigest}</code></p><ul>{t.files.map(p=><li key={p}>{p}</li>)}</ul></details></div>)}
   <p>Creating branches and PRs can trigger repository or external automation.</p>
   <details><summary>Automation and exact actions</summary>{review.automation.map(a=><div key={a.repository}><strong>{a.repository}</strong><p>{a.detectedAutomation.length?'Detected automation: '+a.detectedAutomation.join(', '):'No automation detected in selected source. External automation remains unknown.'}</p></div>)}<ol>{review.actions.map((a,i)=><li key={i}>{a.repository} · {a.kind} · {a.ref}</li>)}</ol></details>
   <div className="maintenance-actions"><button className="btn" disabled={busy} onClick={()=>act(async()=>download(await request('/previews/'+review.id+'/export?projectId='+encodeURIComponent(project.id))))}><Download size={14}/>Download exact preview</button></div>
   {!active&&status?.status!=='published_proposals'&&<><label className="publication-confirm"><input type="checkbox" checked={accepted} disabled={busy} onChange={e=>setAccepted(e.target.checked)}/>I reviewed these patches and accept repository automation.</label><button className="btn primary" disabled={busy||!accepted||review.resultDigest!==result.digest} onClick={publish}>Publish draft PRs</button></>}
  </div>}
  {(active||busy)&&<div className="maintenance-status" role="status"><LoaderCircle className="maintenance-spin" size={16}/><span>{active?'Publishing checked proposals':'Reading repository evidence'}</span>{active&&<button className="btn" onClick={()=>act(async()=>{await request('/previews/'+review.id+'/cancel',{projectId:project.id});const s=await request('/previews/'+review.id+'?projectId='+encodeURIComponent(project.id));if(live())setStatus(s);})}><Square size={14}/>Stop new writes</button>}</div>}
  {active&&<><progress aria-label="Confirmed publication actions" max={total||1} value={done}/><p>{done} of {total} actions confirmed</p></>}
  {status?.status==='published_proposals'&&<p role="status">{review?.resultDigest===result.digest?'Draft proposals delivered. Review them on GitHub.':'Previous wave delivered. Current inputs require a fresh review.'}</p>}
  {['needs_attention','reconciliation_required','inspect_recorded_actions'].includes(status?.status)&&<div><p className="maintenance-error">Inspect recorded actions before retrying. Uncertain writes are not repeated blindly.</p>{status.detail&&<details><summary>Details</summary><pre>{status.detail}</pre></details>}<button className="btn" disabled={busy||active} onClick={()=>act(async()=>{await request('/previews/'+review.id+'/reconcile',{projectId:project.id,credentialOverrides:Object.fromEntries(review.targets.flatMap(t=>{const selected=mapped(t.root);return selected?.repository===t.repository?[[t.repository,selected.connection]]:[];}))});const s=await request('/previews/'+review.id+'?projectId='+encodeURIComponent(project.id));if(live())setStatus(s);})}>Reconcile recorded writes</button></div>}
  {!!proposals.length&&<div><h3>Proposals</h3><ul>{proposals.map(p=><li key={p.repositoryId+':'+p.number}><a href={p.url} target="_blank" rel="noreferrer">{p.repository} #{p.number} <ExternalLink size={12}/></a> · {p.merged?'Merged':p.state==='closed'?'Closed':'Open'}</li>)}</ul><button className="btn" disabled={busy||active} onClick={()=>act(refreshProposals)}>Refresh PR status</button><p className="muted">Remote status refreshes at most every 30 seconds.</p></div>}
  {mapped(result.module)&&['module_release_pending','local_release_checked'].includes(campaign.status)&&<details><summary>Check actual module release</summary><p>Merge the module proposal and create its release tag. AtMem fetches matching bytes and checks consumers again.</p><label>Existing GitHub release tag<input aria-label="Existing GitHub module release tag" value={tag} disabled={busy||active||campaign.status==='checking'} onChange={e=>setTag(e.target.value)}/></label><button className="btn primary" disabled={busy||active||!tag||campaign.status==='checking'} onClick={observe}>Fetch release and check consumers</button><p className="muted">Consumer patches pin the authenticated commit SHA. A new wave requires fresh confirmation.</p></details>}
 </section>;
}
