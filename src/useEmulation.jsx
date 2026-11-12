import {useEffect,useMemo,useRef,useState} from 'react';
import {emulationPreflight} from './emulation-guidance.mjs';
import {terraformSketch} from './terraform.mjs';
import {toProjectFile} from './project-file.mjs';

export function useEmulation(project,environment,session){
 const [last,setLast]=useState(null),[running,setRunning]=useState(false),[autoRetest,setAutoRetest]=useState(true),[coach,setCoach]=useState(true),[retestLimitReached,setRetestLimitReached]=useState(false);
 const preflight=useMemo(()=>emulationPreflight(project),[project]);
 const controller=useRef(null),retest=useRef(null),runRef=useRef(null),automaticRounds=useRef(0);
 const key=useMemo(()=>JSON.stringify([project.id,environment,terraformSketch(project,environment)]),[project,environment]);
 useEffect(()=>{
  controller.current?.abort();controller.current=null;setRunning(false);
  if(retest.current===project.id){retest.current=null;const timer=setTimeout(()=>runRef.current?.({automatic:true}),100);return ()=>clearTimeout(timer);}
  retest.current=null;
 },[key,project.id]);
 useEffect(()=>()=>controller.current?.abort(),[]);
 useEffect(()=>{automaticRounds.current=0;setRetestLimitReached(false);},[project.id]);
 async function run(options={}){
  if(preflight)return;
  if(!options.automatic){automaticRounds.current=0;setRetestLimitReached(false);}
  if(controller.current)return;
  const request=new AbortController();controller.current=request;setRunning(true);
  const timer=setTimeout(()=>request.abort(),115000);
  const save=report=>{if(controller.current===request)setLast({key,projectId:project.id,report});};
  try{
   toProjectFile(project);if(!session?.token)throw Error('Connect to the architect service before emulating.');
   const response=await fetch('/api/emulation/run',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({project,environment}),signal:request.signal});
   const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Emulation failed.');
   if(!request.signal.aborted)save(body);
  }catch(error){save({status:'failed',checks:[],message:request.signal.aborted?'Stopped waiting; no pass was recorded. The worker retains its server time limit.':error.message});}
  finally{clearTimeout(timer);if(controller.current===request){controller.current=null;setRunning(false);}}
 }
 runRef.current=run;
 const result=last?.key===key?last.report:null,previous=last?.projectId===project.id&&last.key!==key?last.report:null;
 return {result,previous,running,preflight,retestLimitReached,coach,setCoach,run,stop:()=>controller.current?.abort(),autoRetest,setAutoRetest,scheduleRetest:()=>{if(autoRetest&&automaticRounds.current<2){automaticRounds.current++;retest.current=project.id;}else if(autoRetest)setRetestLimitReached(true);}};
}
