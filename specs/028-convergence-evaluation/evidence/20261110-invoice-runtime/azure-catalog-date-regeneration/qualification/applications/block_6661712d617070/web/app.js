'use strict';
const el=id=>document.getElementById(id);
let config=null,pending=null,epoch=0;
const status=text=>{el('status').textContent=text;};
function ready(){el('submit').disabled=!config||!!pending;el('activity').hidden=!pending;}
function clear(){epoch++;if(pending)pending.abort();pending=null;el('question').value='';el('answer').textContent='';el('citations').replaceChildren();status('Ask about our published help articles.');ready();}
function render(reply){
 const result=reply.result;
 if(reply.requiresHumanReview!==true||!result||typeof result.answer!=='string'||!result.answer.trim()||new TextEncoder().encode(result.answer).length>16000||typeof result.abstained!=='boolean'||!Array.isArray(result.citations)||result.citations.length>2||result.abstained&&result.citations.length||!result.abstained&&!result.citations.length)throw Error('invalid-result');
 const fragment=document.createDocumentFragment(),seen=new Set();
 for(const citation of result.citations){
  if(!citation||typeof citation.id!=='string'||seen.has(citation.id)||typeof citation.title!=='string'||typeof citation.quote!=='string'||typeof citation.url!=='string'||citation.title.length>500||citation.quote.length>2000)throw Error('invalid-source');
  seen.add(citation.id);const item=document.createElement('li'),label=document.createElement(citation.url?'a':'strong'),quote=document.createElement('blockquote');
  label.textContent=citation.title;
  if(citation.url){const url=new URL(citation.url);if(url.protocol!=='https:'||url.username||url.password)throw Error('invalid-source');label.href=url.href;label.target='_blank';label.rel='noopener noreferrer';}
  quote.textContent=citation.quote;item.append(label,quote);fragment.append(item);
 }
 el('answer').textContent=result.answer;el('citations').replaceChildren(fragment);status(result.abstained?'The published articles do not contain enough information.':'See the cited articles for more detail.');
}
el('clear').addEventListener('click',clear);
el('ask').addEventListener('submit',async event=>{
 event.preventDefault();if(!config||pending)return;
 const text=el('question').value.trim();if(!text||new TextEncoder().encode(text).length>config.maxInputBytes){status('Enter a question of up to '+config.maxInputBytes.toLocaleString()+' UTF-8 bytes.');return;}
 const current=epoch,controller=new AbortController();pending=controller;el('answer').textContent='';el('citations').replaceChildren();status('Finding an answer in the published articles…');ready();
 const timer=setTimeout(()=>controller.abort(),config.requestDeadlineMs);
 try{
  const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal});
  if(current!==epoch)return;
  const reply=await response.json();if(current!==epoch)return;
  if(response.status===429){status('The assistant is busy. Please try again shortly.');return;}
  if(!response.ok){status(reply.error==='data_retention_unverified'?'The site owner needs to finish the AI data-handling setup. Your question was not sent to the AI.':'An answer is unavailable right now. Please try again shortly; if it keeps happening, contact the site owner.');return;}
  render(reply);
 }catch(error){if(current===epoch)status(error.name==='AbortError'?'The request took too long. Please try again shortly.':'The answer or its sources could not be verified. Please try again shortly.');}
 finally{clearTimeout(timer);if(pending===controller)pending=null;ready();}
});
fetch('/config.json',{cache:'no-store',credentials:'same-origin',redirect:'error'}).then(async response=>{
 if(!response.ok)throw Error('config');const value=await response.json();
 if(value.sourcePolicy!=='public-catalog-only'||!Number.isInteger(value.maxInputBytes)||value.maxInputBytes!==2000||!Number.isInteger(value.requestDeadlineMs)||value.requestDeadlineMs<1000||value.requestDeadlineMs>120000)throw Error('config');
 config=value;ready();status('Ask about our published help articles.');
}).catch(()=>{config=null;ready();status('The assistant could not load its setup. Please reload the page or contact the site owner.');});
ready();
