import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const base=process.argv[2]||'http://localhost:5297';
const main=await(await fetch(base+'/src/main.jsx?implementation-handoff-v1')).text();
const reactUrl=main.match(/from "([^"]*\/react\.js[^";]*)"/)?.[1];
const reactDomUrl=main.match(/from "([^"]*react-dom_client[^";]*)"/)?.[1];
assert.ok(reactUrl&&reactDomUrl,'Resolve the preview React runtime');
const browser=await chromium.launch({headless:true});
const results=[];
try{
 for(const scenario of ['selection','design-busy','restore-failed','uncertain','cancel']){
  const page=await browser.newPage();page.setDefaultTimeout(10000);
  let creates=0,starts=0,lists=0,recoveries=0;const errors=[];const requests=[];
  let job={id:'fixture-session',state:scenario==='uncertain'?'starting':'idle',model:'gpt-6.1-sol',effort:'high'};
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/engineering/**',async route=>{
   const action=new URL(route.request().url()).pathname.split('/').at(-1);
   const payload=route.request().postDataJSON();requests.push({action,payload});
   if(action==='list'){
    lists++;
    if(scenario==='restore-failed'&&lists===1)return route.fulfill({status:503,json:{detail:'Synthetic history service unavailable'}});
    return route.fulfill({json:{sessions:scenario==='uncertain'?[job]:[]}});
   }
   if(action==='recover'){
    recoveries++;if(recoveries>1)job={...job,state:'idle'};
    return route.fulfill({json:job});
   }
   if(action==='create'){creates++;return route.fulfill({json:job});}
   if(action==='start'){starts++;job={...job,state:'running',run:'fixture-run'};return route.fulfill({json:job});}
   if(action==='events')return route.fulfill({json:{events:[],session:job}});
   if(action==='artifacts')return route.fulfill({json:{artifacts:[]}});
   throw Error('Unexpected fixture action '+action);
  });
  await page.route('**/handoff-fixture',route=>route.fulfill({contentType:'text/html',body:`<div id="root"></div><script type="module">
   import React from '${reactUrl}';import ReactDOM from '${reactDomUrl}';
   import {EngineeringPanel} from '/src/EngineeringPanel.jsx?implementation-handoff-v1';
   import {CLOUD_STORAGE_SCENARIOS} from '/src/cloud-storage-scenarios.mjs';
   const scenario=${JSON.stringify(scenario)},project=CLOUD_STORAGE_SCENARIOS[0].project;
   window.handled=0;window.saves=0;
   function App(){
    const [connection,setConnection]=React.useState(['selection','cancel'].includes(scenario)?null:{provider:'codex',model:'gpt-6.1-sol',effort:'high'});
    const [contextBusy,setContextBusy]=React.useState(scenario==='design-busy');
    const [request,setRequest]=React.useState({id:'fixture-request',projectId:project.id,intent:'test'});
    return React.createElement(React.Fragment,null,
     React.createElement('button',{onClick:()=>setContextBusy(false)},'Finish design changes'),
     React.createElement(EngineeringPanel,{project,projectId:project.id,session:{token:'fixture'},connection,contextBusy,buildRequest:request,
      onBuildRequestHandled:id=>{window.handled++;setRequest(null)},
      onConnections:()=>setConnection({provider:'codex',model:'gpt-6.1-sol',effort:'high'}),
      saveProject:async()=>{window.saves++;return {sha256:'a'.repeat(64)}}}));
   }
   ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
  </script>`}));
  await page.goto(base+'/handoff-fixture');
  if(['selection','cancel'].includes(scenario)){
   await page.getByText('Your implementation request is waiting here.',{exact:false}).waitFor();
   assert.equal(creates,0);assert.equal(starts,0);assert.equal(await page.evaluate(()=>window.handled),0);
   if(scenario==='cancel')await page.getByRole('button',{name:'Cancel queued request'}).click();
   await page.getByRole('button',{name:'Choose model',exact:true}).click();
  }else if(scenario==='design-busy'){
   await page.getByText('Your implementation request is waiting for the current design changes.',{exact:false}).waitFor();
   assert.equal(starts,0);assert.equal(await page.evaluate(()=>window.handled),0);
   await page.getByRole('button',{name:'Finish design changes'}).click();
  }else if(scenario==='restore-failed'){
   await page.getByRole('button',{name:'Retry loading earlier work'}).waitFor();
   assert.equal(creates,0);assert.equal(starts,0);assert.equal(await page.evaluate(()=>window.handled),0);
   assert.equal(await page.getByRole('button',{name:'Build this design',exact:true}).isDisabled(),true);
   await page.getByRole('button',{name:'Retry loading earlier work'}).click();
  }else{
   await page.getByText('Your implementation request is waiting. Recover the existing request first',{exact:false}).waitFor();
   assert.equal(starts,0);assert.equal(await page.evaluate(()=>window.handled),0);
   await page.getByRole('button',{name:'Recover connection'}).click();
  }
  if(scenario==='cancel'){
   await page.getByText('gpt-6.1-sol · high',{exact:true}).waitFor();
   assert.equal(creates,0);assert.equal(starts,0);
  }else{
   await page.getByText('Working · gpt-6.1-sol · high',{exact:true}).waitFor();
   assert.equal(starts,1);assert.equal(creates,scenario==='uncertain'?0:1);
   assert.equal(await page.evaluate(()=>window.handled),1);
   const start=requests.find(request=>request.action==='start').payload;
   assert.match(start.text,/run its local checks/);assert.match(start.text,/No cloud deployment or account access/);
   assert.equal(start.contextSha256,'a'.repeat(64));
   const create=requests.find(request=>request.action==='create')?.payload;
   if(create){assert.equal(create.model,'gpt-6.1-sol');assert.equal(create.effort,'high');}
   // Another render must not replay the consumed implementation intent.
   await page.getByRole('button',{name:'Finish design changes'}).click();
   assert.equal(starts,1);
  }
  assert.deepEqual(errors,[]);results.push({scenario,passed:true,creates,starts,lists,recoveries});await page.close();
 }
 console.log(JSON.stringify({passed:true,results,fixtureOnly:true,nativeInferenceRequests:0,ownerProjectWrites:0}));
}finally{await browser.close()}
