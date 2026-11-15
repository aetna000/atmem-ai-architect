import React,{useState} from 'react';
import receipt from './reference-example/receipt.json';
export function ReadyExampleDownload({compact=false}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 async function download(){setBusy(true);setError('');try{
  const response=await fetch(receipt.url);if(!response.ok)throw Error('Example download unavailable. Retry.');
  const bytes=await response.arrayBuffer();const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==receipt.sha256)throw Error('Example integrity check failed. Retry.');
  const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'})),link=document.createElement('a');link.href=url;link.download='atmem-ai-complete-example.zip';link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
 }catch(e){setError(e.message)}finally{setBusy(false)}}
 return <><button type="button" className={compact?'btn ready-download':'btn primary'} onClick={download} disabled={busy}>{busy?'Preparing…':compact?'Download example ZIP':'Download complete example'}</button>{error&&<p role="alert">{error}</p>}</>;
}
export function ReadyExampleChecklist(){
 const rows=[['Requirements','Recorded'],['Cloud','AWS'],['Data country','Australia'],['Cloud region','Sydney'],['Cost worksheet','USD 7.56/month · sample'],['Implementation','Source + built runtime'],['Application checks','13 local tests passed'],['Terraform checks','Validated · 2 mock plans passed']];
 return <section className="final-checklist ready-reference" aria-label="Prepared example checklist"><h3>Complete reference example</h3><p>These checks apply to the bundled example ZIP. Your edited project has separate checks.</p><ul>{rows.map(([name,value])=><li key={name}><span className="check-complete">✓</span><span>{name}</span><strong>{value}</strong></li>)}</ul><ReadyExampleDownload/><details><summary>Evidence and scope</summary><p>Local fixtures and mocked AWS. Live deployment and real tenant integration have not run.</p><p>Illustrative AWS usage; assumptions and official price snapshots are included.</p></details></section>;
}
