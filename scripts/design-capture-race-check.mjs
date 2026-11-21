import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {chromium} from '@playwright/test';
// Real panel/browser with delayed history and synthetic receipts. No native inference.
const output=process.env.ATMEM_DESIGN_RACE_OUTPUT||'.local/design-capture-race';fs.mkdirSync(output,{recursive:true});
const fixture='.local/ui-design-capture-race';fs.mkdirSync(fixture,{recursive:true});
fs.writeFileSync(path.join(fixture,'index.html'),`<div id="root"></div><script type="module">
import React from 'react';import {createRoot} from 'react-dom/client';import {EngineeringPanel} from '/src/EngineeringPanel.jsx';import '/src/style.css';
window.calls={mapped:0,assessed:0,opened:0};const phase=new URL(location.href).searchParams.get('phase');const project={id:'fixture-project',nodes:[],edges:[],extensions:{designSources:[{sha256:'a'.repeat(64)}]}};
if(['applied-design','mismatched-pin-design'].includes(phase)){project.extensions.architectureDocuments={artifactId:'capture-one',draftSha256:(phase==='mismatched-pin-design'?'d':'f').repeat(64)};project.extensions.architectureDraftQuality={artifactId:'capture-one',draftSha256:'f'.repeat(64),appliedBasis:'e'.repeat(64)};}
createRoot(document.getElementById('root')).render(React.createElement(EngineeringPanel,{project,projectId:project.id,session:{token:'fixture',providers:{}},saveProject:async()=>({sha256:'a'.repeat(64)}),onWorkModelChange:()=>window.calls.mapped++,onAssessCanvas:async()=>{window.calls.assessed++;await new Promise(resolve=>setTimeout(resolve,100));if(window.calls.mapped)throw Error('Design metadata changed during assessment.');return {quality:{ready:true,gates:{},measurements:[]}};},onCanvas:()=>window.calls.opened++}));
</script>`);
const hash=value=>createHash('sha256').update(value).digest('hex');
const context=JSON.stringify({format:'atmem.ai-architect.project',meta:{id:'fixture-project'},design:{nodes:[],edges:[]}});
const payload={format:'atmem.architecture-proposal',version:1,projectId:'fixture-project',sessionId:'fixture-session',runId:'current-run',artifactId:'capture-one',artifactSha256:'a'.repeat(64),proposalSha256:'b'.repeat(64),context:{id:'context',revision:1,projectId:'fixture-project',content:context,sha256:hash(context)},events:[],proposal:{records:[]},files:[],definitionSha256:'c'.repeat(64),boundary:'artifact_file_binding_only'};
const content=JSON.stringify(payload),browser=await chromium.launch();
try{for(const phase of ['design','implementation','applied-design','mismatched-pin-design']){
 const page=await browser.newPage();let historyReady=false,mappingRequests=0;
 const job={id:'fixture-session',state:'idle',run:'current-run',last_status:'completed',model:'selected-model',effort:'medium'};
 await page.route('**/api/engineering/**',async route=>{
  const action=new URL(route.request().url()).pathname.split('/').at(-1);let result={};
  if(action==='list')result={sessions:[job]};if(action==='recover')result=job;
  if(action==='artifacts')result={artifacts:[{id:'capture-one',runId:job.run,sha256:'a'.repeat(64),files:[{path:'architecture.canvas.json',kind:'file'},{path:'architecture.review.md',kind:'file'},{path:'architecture-work-proposal.json',kind:'file'}]}]};
  if(action==='events'){
   const after=route.request().postDataJSON().after;
   if(after===0)result={session:job,events:[{sequence:1,runId:'previous-run',kind:'accepted',text:'Earlier implementation request.'}]};
   else if(after===1){await new Promise(resolve=>setTimeout(resolve,700));historyReady=true;result={session:job,events:[{sequence:2,runId:job.run,kind:'accepted',text:phase!=='implementation'?'Design the full system described by the saved source documents.':'Implement the approved module.'}]};}
   else result={session:job,events:[]};
  }
  if(action==='reconciliation'){mappingRequests++;result={status:'prepared',content,sha256:hash(content)};}
  if(['start','steer'].includes(action))throw Error('Unexpected inference request.');
  await route.fulfill({json:result});
 });
 await page.goto((process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194')+'/'+fixture+'/index.html?phase='+phase);
 if(phase==='applied-design'){for(let i=0;!historyReady&&i<100;i++)await page.waitForTimeout(50);await page.waitForTimeout(300);}
 else if(phase!=='implementation')await page.waitForFunction(()=>window.calls.opened===1,{},{timeout:7000});else await page.waitForFunction(()=>window.calls.mapped===1,{},{timeout:7000});
 assert.equal(historyReady,true);const calls=await page.evaluate(()=>window.calls);
 if(phase==='design'||phase==='mismatched-pin-design'){assert.equal(calls.mapped,0);assert.equal(mappingRequests,0);assert.equal(calls.assessed,1);assert.equal(calls.opened,1);}else if(phase==='implementation'){assert.equal(calls.assessed,0);assert.equal(calls.opened,0);assert.equal(mappingRequests,1);}else{assert.equal(calls.assessed,0);assert.equal(calls.opened,0);assert.equal(calls.mapped,0);assert.equal(mappingRequests,0);}
 fs.writeFileSync(path.join(output,phase+'.json'),JSON.stringify({phase,...calls,mappingRequests,evidence:'Real React/browser with delayed event history and explicit fixture receipts; no native generation.'},null,2)+'\n');await page.screenshot({path:path.join(output,phase+'.png')});await page.close();
}console.log('Design assessment waited for current intent and ignored legacy mappings; implementation mapping remained available.');}finally{await browser.close();}
