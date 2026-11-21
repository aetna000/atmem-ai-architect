import {useEffect,useState}from 'react';
import {engineeringCall}from './engineering-client.mjs';
// Observe durable work across stage navigation; polling never starts or resumes a turn.
export function useEngineeringStatus(session,projectId,enabled=true,availabilityKey=null){
 const [status,setStatus]=useState(null);
 useEffect(()=>{
  if(!session?.engineeringEnabled||!enabled){setStatus(null);return;}
  const controller=new AbortController();let stopped=false,timer,unavailable=false,lastReconciled=Date.now(),failures=0;
  async function poll(){try{
   const result=await engineeringCall(session,'list',{projectId},{signal:controller.signal});
   let job=result.sessions?.at(-1)||null;
   if(['running','starting'].includes(job?.state)&&Date.now()-lastReconciled>30000){lastReconciled=Date.now();job=await engineeringCall(session,'recover',{projectId,sessionId:job.id},{signal:controller.signal});}
   failures=0;if(!stopped)setStatus({projectId,job});
  }catch(error){failures++;if(error.status===404)unavailable=true;if(!stopped&&error.name!=='AbortError')setStatus(current=>({projectId,job:{...(current?.projectId===projectId?current.job:{}),observationError:error.message}}));}
  finally{if(!stopped&&!unavailable)timer=setTimeout(poll,Math.min(30000,1500*2**failures));}}
  void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
 },[session?.token,session?.engineeringEnabled,projectId,enabled,availabilityKey]);
 return status?.projectId===projectId?status.job:null;
}
