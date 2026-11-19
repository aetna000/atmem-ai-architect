import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
// Real React/browser, synthetic context and unavailable evidence fixture; no inference.
const output=process.env.ATMEM_EXPORT_RACE_OUTPUT||'.local/output-download-race';
fs.mkdirSync(output,{recursive:true});
const fixture='.local/ui-output-download-race';fs.mkdirSync(fixture,{recursive:true});
fs.writeFileSync(path.join(fixture,'index.html'),`<div id="root"></div><script type="module">
import React from 'react';import {createRoot} from 'react-dom/client';
import {OutputsView} from '/src/OutputsView.jsx';import '/src/style.css';
let release;window.downloads=[];window.preparing=false;
const session={token:'fixture',engineeringEnabled:false};
const original={version:1,id:'export-race-fixture',revision:1,createdAt:'2026-11-19T00:00:00Z',name:'Export race fixture',provider:'tools',nodes:[],edges:[],needs:[],decisions:[],openQuestions:[],extensions:{architectureDocuments:{version:1,artifactId:'11111111-1111-4111-8111-111111111111',draftSha256:'a'.repeat(64),contextSha256:'b'.repeat(64),files:[]}}};
function App(){const [project,setProject]=React.useState(original);
window.changeDesign=()=>setProject(value=>({...value,name:'Changed export race fixture'}));
window.release=()=>release?.(session);
return React.createElement(OutputsView,{project,session,onPrepareSources:()=>{if(window.preparing)return session;window.preparing=true;return new Promise(resolve=>release=resolve);},onDownload:bundle=>window.downloads.push(bundle.project.name)});}
createRoot(document.getElementById('root')).render(React.createElement(App));
</script>`);
const browser=await chromium.launch();let page;
try{
 page=await browser.newPage();await page.route('**/api/design-evidence/draft',route=>route.fulfill({status:409,json:{detail:'Synthetic missing capture.'}}));
 await page.goto((process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194')+'/'+fixture+'/index.html');
 const download=page.getByRole('button',{name:'Download project ZIP',exact:true});await download.click();await page.waitForFunction(()=>window.preparing);
 await page.evaluate(()=>window.changeDesign());await page.waitForFunction(()=>document.querySelector('.output-preview')?.textContent.includes('Changed export race fixture'));
 await page.evaluate(()=>window.release());
 await page.getByRole('alert').getByText('Design changed while preparing files. Download again.',{exact:true}).waitFor({timeout:10000});
 assert.deepEqual(await page.evaluate(()=>window.downloads),[]);
 await page.getByRole('button',{name:'Retry preparing outputs',exact:true}).click();await download.click();await page.waitForFunction(()=>window.downloads.length===1);
 assert.deepEqual(await page.evaluate(()=>window.downloads),['Changed export race fixture']);
 const receipt={evidence:'Real browser with synthetic context and unavailable evidence response',staleDownloadRejected:true,visibleRetry:true,currentSnapshotDownload:true,implementationExecuted:false,deploymentExecuted:false};
 fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');await page.screenshot({path:path.join(output,'delivery.png')});console.log(JSON.stringify(receipt,null,2));
}catch(error){await page?.screenshot({path:path.join(output,'failure.png')});throw error;}finally{await browser.close();}
