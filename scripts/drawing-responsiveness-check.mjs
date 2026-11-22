// Dense synthetic geometry and an instant fake model response isolate browser latency.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium,expect} from '@playwright/test';
const base=process.argv[2]||'http://127.0.0.1:5199',out=process.env.RESPONSIVENESS_EVIDENCE||'.local/drawing-responsiveness';
if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw Error('Loopback only.');fs.mkdirSync(out,{recursive:true});
const nodes=Array.from({length:20},(_,i)=>({id:'stage-'+i,type:'resource',position:{x:50+(i%5)*700,y:50+Math.floor(i/5)*350},data:{label:'Archive stage '+i,kind:'resource',provider:'tools',description:'Synthetic record processing stage.',origin:'proposed',inputPosition:'left',outputPosition:'right',config:{region:'To be selected',classification:'Internal',timeout:5000}}}));
const edges=Array.from({length:94},(_,i)=>{const a=i%20,b=(a+1+Math.floor(i/20)*3)%20;return{id:'exchange-'+i,source:nodes[a].id,target:nodes[b].id,label:'Record exchange '+i,type:'smoothstep'};});
const project={version:1,revision:1,id:'dense-responsiveness-test',name:'Archive exchanges',provider:'tools',nodes,edges};
const browser=await chromium.launch(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{});let page;
try{
 page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(15000);const errors=[];let requests=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(project=>{localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'low'}));window.__long=[];new PerformanceObserver(list=>window.__long.push(...list.getEntries().map(e=>e.duration))).observe({type:'longtask',buffered:true});},project);
 await page.route('**/api/**',r=>{const p=new URL(r.request().url()).pathname;if(p==='/api/architect')requests++;return r.fulfill({json:p==='/api/session'?{status:'local-sidecar',token:'fixture',engineeringEnabled:true,providers:{codex:{available:true}}}:p==='/api/architect'?{message:'Synthetic response.'}:{saved:true,sessions:[],projects:[],events:[],artifacts:[],checks:[],enabled:false,status:'disabled'}});});
 const start=Date.now();await page.goto(base);const canvas=page.locator('.drawio-canvas:visible').last();
 await expect(canvas.locator('[data-cell-kind=edge][role=button]')).toHaveCount(94);const readyMs=Date.now()-start;
 const input=page.getByRole('textbox',{name:'Your message',exact:true});const typed=Date.now();await input.fill('What is the next step?');const inputMs=Date.now()-typed;
 const sent=Date.now();await page.getByRole('button',{name:'Send message',exact:true}).click();await page.getByText('Synthetic response.',{exact:true}).waitFor();const responseMs=Date.now()-sent;
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 assert.deepEqual(saved.nodes,project.nodes);assert.deepEqual(saved.edges,project.edges);assert.equal(requests,1);assert.deepEqual(errors,[]);
 assert.ok(readyMs<10000,'Dense page becomes interactive without a prolonged freeze');assert.ok(inputMs<2000,'Typing is responsive');assert.ok(responseMs<3000,'Canvas does not block an immediate model response');
 const metrics={readyMs,inputMs,responseMs,nodes:20,edges:94,requests,errors,longTasks:await page.evaluate(()=>({count:__long.length,max:Math.max(0,...__long),total:__long.reduce((a,b)=>a+b,0)}))};
 await page.screenshot({path:out+'/dense.png'});fs.writeFileSync(out+'/results.json',JSON.stringify(metrics,null,2));console.log(JSON.stringify(metrics));
}catch(error){await page?.screenshot({path:out+'/failure.png',timeout:3000}).catch(()=>{});throw error;}finally{await browser.close();}
