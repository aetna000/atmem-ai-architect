import {useEffect,useState}from 'react';
import {engineeringCall}from './engineering-client.mjs';
// Observe durable work across stage navigation; polling never starts or resumes a turn.
export function useEngineeringStatus(session,projectId){
 const [status,setStatus]=useState(null);
 useEffect(()=>{
  if(!session?.engineeringEnabled){setStatus(null);return;}
  const controller=new AbortController();let stopped=false,timer;
  async function poll(){try{
   const result=await engineeringCall(session,'list',{projectId},{signal:controller.signal});
   if(!stopped)setStatus({projectId,job:result.sessions?.at(-1)||null});
  }catch(error){if(!stopped&&error.name!=='AbortError')setStatus(null);}
  finally{if(!stopped)timer=setTimeout(poll,1500);}}
  void poll();return()=>{stopped=true;clearTimeout(timer);controller.abort();};
 },[session?.token,session?.engineeringEnabled,projectId]);
 return status?.projectId===projectId?status.job:null;
}
