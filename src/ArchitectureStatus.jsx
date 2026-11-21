import React,{useEffect,useState} from 'react';
import {Loader2,TriangleAlert} from 'lucide-react';
export function ArchitectureStatus({activity,error,connected,job,pending,sources,hasDesign,onReview,onConnect,onRetry}){
 const currentActivity=activity?.runId===job?.run?activity:null;
 const active=['running','starting'].includes(job?.state);
 const failed=['interrupted','failed','cancelled'].includes(job?.last_status)&&!active;
 const attention=error||job?.observationError||(currentActivity?.phase==='review'?currentActivity.text:null);
 const waiting=!!pending&&!active&&!connected;
 const [now,setNow]=useState(Date.now()),[started,setStarted]=useState(null);
 const quiet=active&&now-(currentActivity?.receivedAt||started||now)>90000;
 useEffect(()=>{
  if(!active){setStarted(null);return;}
  const key='atmem-run-seen:'+job.id+':'+job.run;
  let value=Date.now();
  try{value=Number(localStorage.getItem(key))||value;localStorage.setItem(key,String(value));}catch{}
  setStarted(value);const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);
 },[job?.id,job?.run,active]);
 if(!active&&!failed&&!attention&&!pending&&(hasDesign||!job&&!sources.length))return null;
 const title=attention?'Generation needs attention':failed?'Architecture generation '+job.last_status:quiet?'No recent generation updates':currentActivity?.phase==='checking'?'Checking architecture':active?(job.state==='starting'?'Confirming generation start':'Building your architecture'):waiting?'Ready to generate':!job?'Preparing architecture':'Draft requires review';
 const seconds=Math.max(0,Math.floor((now-(started||now))/1000));
 return <section className={'architecture-job-status'+(failed||attention?' failed':'')} role={failed||attention||quiet?'alert':'status'} aria-label="Architecture work status">
  <div>{failed||attention||quiet?<TriangleAlert size={23}/>:<Loader2 size={23}/>}<div><strong>{title}</strong><p>{sources.length} specifications retained{active?' · '+Math.floor(seconds/60)+'m '+seconds%60+'s since connected':''}</p></div></div>
  <p>{attention|| (failed?'Your sources and completed captures remain available. Open generation to inspect or recover.':quiet?'No recent progress received. Check live status in generation.':active?(currentActivity?.text||'Reading specifications and preparing the architecture.') :currentActivity?.phase==='checking'?currentActivity.text:waiting?'Connect ChatGPT (Codex) to continue the retained architecture request.':'Your specification is retained. Open generation to inspect the next step.')}</p>
  <footer><button className="btn primary" onClick={waiting?onConnect:onReview}>{waiting?'Connect and start':'Open generation'}</button>{attention&&!active&&pending&&(!job?.id||job.state==='idle')&&<button className="btn" onClick={onRetry}>Retry queued request</button>}{failed&&job?.state==='idle'&&<button className="btn" onClick={onRetry}>Resume architecture</button>}</footer>
 </section>;
}
