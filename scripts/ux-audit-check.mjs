// Deterministic first-use UX loop. Provider/job responses in the lifecycle phase are fixtures, not runtime evidence.
import{resolve}from'node:path';import fs from'node:fs';import assert from'node:assert/strict';import{chromium}from'playwright';
const url=process.argv[2]||'http://127.0.0.1:5174/',dir=resolve(process.env.UX_EVIDENCE||'/tmp/atmem-ux-review')+'/';fs.mkdirSync(dir,{recursive:true});
const b=await chromium.launch({channel:'chrome'});const results=[];
try{
 for(const width of [1512,390]){
  const p=await b.newPage({viewport:{width,height:945}});const errors=[],requests=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(r.url().includes('/api/engineering/list'))requests.push(r.url())});
  await p.route('**/api/projects/save',r=>r.fulfill({json:{saved:true,sha256:'a'.repeat(64)}}));
  await p.goto(url);await p.waitForTimeout(2400);
  assert.equal(requests.length,0,'Unsaved projects must not poll engineering/list');
  const initial=p.getByRole('button',{name:'Explore runnable AI example',exact:true});await initial.click();await p.waitForTimeout(700);
  assert.equal(await p.getByRole('region',{name:'Project overview'}).count(),1);await p.screenshot({path:dir+width+'-Overview.png'});await p.getByRole('button',{name:'Traceability',exact:true}).click();assert.ok(await p.locator('.traceability-scroll tbody tr').count()>0);await p.screenshot({path:dir+width+'-Traceability.png'});await p.getByRole('button',{name:'Scenarios',exact:true}).click();assert.match(await p.locator('.project-overview').innerText(),/scenario/i);
  for(const stage of ['Board','Requirements','Choices','Review','Delivery']){
   await p.getByRole('tab',{name:new RegExp(stage)}).first().click();await p.waitForTimeout(700);
   await p.screenshot({path:dir+width+'-'+stage+'.png'});
   fs.writeFileSync(dir+width+'-'+stage+'.txt',await p.locator('body').innerText());
   if(stage==='Requirements'){assert.equal(await p.locator('.requirements-word-toolbar:visible').count(),0);assert.equal((await p.locator('body').innerText()).split('Proposed verification').length-1,0);}
   if(stage==='Review')assert.equal(await p.getByText('Missing content',{exact:true}).count(),0);
   assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth),width,stage+' must not overflow horizontally');const unnamed=await p.locator('button:visible').evaluateAll(ns=>ns.filter(n=>!n.textContent.trim()&&!n.getAttribute('aria-label')&&!n.title).map(n=>n.outerHTML.slice(0,200)));assert.deepEqual(unnamed,[],stage+' buttons need accessible names');
  }
  assert.deepEqual(errors,[]);results.push({width,stages:5,blankProjectPolls:0,overflow:false,unnamedButtons:0,pageErrors:0,overview:true,traceability:true,requirementsReadMode:true});
  await p.close();
 }
}finally{await b.close();fs.writeFileSync(dir+'ux-results.json',JSON.stringify(results,null,2));}

let job=null,starts=0,checkedProvider=null,saved;
const session={status:'local-sidecar',token:'fixture',engineeringEnabled:true,diagramAuthoringEnabled:true,providers:{codex:{installed:true,signedIn:true,available:true},'claude-code':{installed:true,signedIn:true,available:true}}};
const browser=await chromium.launch({channel:'chrome'}),root=dir;
const page=await browser.newPage({viewport:{width:1512,height:945}});page.setDefaultTimeout(12000);
await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'claude-opus-5-5',effort:'low'})));
await page.route('**/api/**',async route=>{
 const url=new URL(route.request().url()),name=url.pathname;
 if(name==='/api/session')return route.fulfill({json:session});
 if(name==='/api/models')return route.fulfill({json:{models:[{id:'fixture-model',efforts:['low'],defaultEffort:'low'}]}});
 if(name==='/api/projects/save'){saved=route.request().postDataJSON().file;return route.fulfill({json:{saved:true,sha256:'a'.repeat(64)}});}
 if(name==='/api/design-sources')return route.fulfill({json:{sources:[{name:'architecture.txt',mime:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',text:'A client uploads documents and receives cited answers.',mode:'extracted',sha256:'b'.repeat(64)}]}});
 if(name==='/api/architect'){checkedProvider=route.request().postDataJSON().provider;return route.fulfill({json:{message:'Connection verified.'}});}
 if(name==='/api/engineering/list')return route.fulfill({json:{sessions:job?[job]:[]}});
 if(name==='/api/engineering/create'){job={id:'11111111-1111-4111-8111-111111111111',model:'fixture-model',effort:'low',state:'idle',run:null,last_status:null};return route.fulfill({json:job});}
 if(name==='/api/engineering/start'){starts++;job={...job,state:'running',run:'22222222-2222-4222-8222-222222222222'};return route.fulfill({json:job});}
 if(name==='/api/engineering/recover')return route.fulfill({json:job});
 if(name==='/api/engineering/events')return route.fulfill({json:{session:job,events:[]}});
 if(name==='/api/engineering/artifacts')return route.fulfill({json:{artifacts:[]}});
 if(name==='/api/engineering/delivery')return route.fulfill({json:{artifact:null,canPackage:false,checks:[]}});
 return route.fulfill({json:{projects:[],bin:[],status:'disabled',memories:[],items:[]}});
});
try{
 await page.goto(url);
 await page.locator('#requirements-file-input').setInputFiles({name:'architecture.txt',mimeType:'text/plain',buffer:Buffer.from('A client uploads documents and receives cited answers.')});
 let dialog=page.getByRole('dialog').filter({hasText:'Connect to generate architecture'});
 await dialog.waitFor();assert.equal(await dialog.getByRole('radiogroup',{name:'Provider',exact:true}).getByRole('radio').count(),1);assert.equal(await dialog.getByRole('radio',{name:'ChatGPT (Codex)',exact:true}).getAttribute('aria-checked'),'true');
 await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
 await page.reload();await page.getByRole('button',{name:'Connect and start',exact:true}).waitFor();
 assert.equal(starts,0);assert.equal(await page.getByRole('region',{name:'Start your project'}).count(),0);
 await page.getByRole('button',{name:'Connect and start',exact:true}).click();await dialog.waitFor();
 await dialog.getByRole('button',{name:'Connect and start',exact:true}).click();
 await page.waitForTimeout(3000);assert.equal(checkedProvider,'codex');assert.equal(starts,1);
 await page.getByRole('status',{name:'Architecture work status'}).waitFor();assert.match(await page.locator('body').innerText(),/Building your architecture/);
 await page.screenshot({path:root+'connection-running.png'});
 await page.clock.install();await page.clock.fastForward(96000);await page.getByRole('alert',{name:'Architecture work status'}).waitFor();assert.match(await page.getByRole('alert',{name:'Architecture work status'}).innerText(),/No recent/);await page.screenshot({path:root+'quiet-generation.png'});await page.clock.resume();
 job={...job,state:'idle',last_status:'interrupted'};await page.waitForTimeout(2200);
 await page.waitForTimeout(300);const alert=page.getByRole('alert',{name:'Architecture work status'});await alert.waitFor();assert.match(await alert.innerText(),/interrupted/);assert.match(await alert.innerText(),/retained|available/);
 assert.equal(await page.getByRole('button',{name:'Resume architecture',exact:true}).count(),1);
 await page.screenshot({path:root+'interrupted.png'});
 await page.getByRole('button',{name:'Resume architecture',exact:true}).click();await page.waitForTimeout(2500);assert.equal(starts,2);
 assert.equal(saved.meta.name,'architecture');
 fs.writeFileSync(dir+'lifecycle-results.json',JSON.stringify({provider:'codex',dismissalRetainsRequest:true,reloadRetainsRequest:true,quietProgressVisible:true,connectionStartsOnce:true,interruptedAlert:true,resumeStarts:starts,sourceBasedTitle:true},null,2));
 console.log('PASS Codex selected, queued upload retained through dismissal, one-click connection starts once, visible interrupted status, resume uses existing job, source-based project title.');
}catch(e){console.log(await page.locator('body').innerText());await page.screenshot({path:root+'lifecycle-failure.png'});throw e;}finally{await browser.close();}
