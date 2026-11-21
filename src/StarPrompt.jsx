import React,{useEffect,useRef}from'react';
import{Star,X}from'lucide-react';
export const STAR_URL='https://github.com/aetna000/atmem-ai-architect';
const KEY='atmem-architect-star-prompt-v1',SNOOZE=30*24*60*60*1000;
export function shouldOfferStar(value,now=Date.now()){
 if(!value)return true;
 try{const record=JSON.parse(value);return record.choice!=='opened'&&(!Number.isFinite(record.after)||record.after<=now);}catch{return true;}
}
export function StarPrompt({offer=0}){
 const dialog=useRef(null),choice=useRef('later');
 function dismiss(value='later'){
  choice.current=value;
  try{localStorage.setItem(KEY,JSON.stringify({choice:value,after:Date.now()+SNOOZE}));}catch{}
  dialog.current?.close();
 }
 useEffect(()=>{
  if(!offer)return;
  let allowed=true;try{allowed=shouldOfferStar(localStorage.getItem(KEY));}catch{}
  if(allowed&&!dialog.current.open){choice.current='later';dialog.current.showModal();}
 },[offer]);
 return <dialog ref={dialog} className="star-prompt" aria-labelledby="star-prompt-title" onCancel={event=>{event.preventDefault();dismiss();}}>
  <header><h2 id="star-prompt-title"><Star size={22} aria-hidden="true"/> Enjoying Architect?</h2><button type="button" className="icon" aria-label="Close star invitation" onClick={()=>dismiss()}><X size={20}/></button></header>
  <p>If Architect helped, a GitHub star helps others find it.</p>
  <div className="star-prompt-actions"><a className="btn primary" href={STAR_URL} target="_blank" rel="noopener noreferrer" onClick={()=>dismiss('opened')}><Star size={18} aria-hidden="true"/> Star on GitHub</a><button type="button" className="btn" onClick={()=>dismiss()}>Later</button></div>
 </dialog>;
}
