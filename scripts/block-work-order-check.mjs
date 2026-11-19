import assert from'node:assert/strict';import{chromium}from'@playwright/test';import{toProjectFile}from'../src/project-file.mjs';
const projectId='order-theatre-project',sessionId='00000000-0000-0000-0000-000000000001';
const project={id:projectId,version:1,revision:1,name:'Theatre operations',provider:'tools',needs:[],edges:[],nodes:[{id:'seat-ledger',type:'resource',position:{x:0,y:0},data:{kind:'resource',provider:'tools',origin:'proposed',label:'Seat ledger',buildSpec:{behavior:'One seat owner',inputs:'Seat and request',outputs:'Durable receipt',tests:'Race duplicate requests'}}}]};
project.nodes[0].data.parentBlockId='theatre';project.nodes.push({id:'theatre',type:'resource',position:{x:0,y:0},data:{kind:'resource',provider:'tools',origin:'proposed',label:'Theatre'}});
const browser=await chromium.launch();let request,attempts=0,ordinaryStarts=0;const errors=[];
try{const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'medium'})));
 const job={id:sessionId,model:'gpt-6.2-sol',effort:'medium',state:'idle',run:null,last_status:null};
 await page.route('**/api/**',async route=>{
  const action=new URL(route.request().url()).pathname;let result={status:'disabled',projects:[],bin:[],sessions:[],events:[],artifacts:[]};
  if(action==='/api/session')result={status:'local-sidecar',token:'fixture',engineeringEnabled:true,providers:{codex:{installed:true,available:true,signedIn:true}}};
  if(action==='/api/projects/save')result={saved:true,sha256:'b'.repeat(64)};
  if(action==='/api/engineering/list')result={sessions:route.request().postDataJSON().projectId===projectId?[job]:[]};
  if(action==='/api/engineering/recover'||action==='/api/engineering/state')result=job;
  if(action==='/api/engineering/events')result={events:request?[{sequence:1,kind:'work_order_prepared',runId:request.requestId,text:'Server compiled scope',workOrder:{version:1,kind:'build_block',blockId:request.blockId,contextSha256:request.contextSha256}},{sequence:2,kind:'accepted',runId:request.requestId,text:'Server compiled scope'}]:[],session:job};
  if(action==='/api/engineering/start')ordinaryStarts++;
  if(action==='/api/engineering/work-orders/block'){
   attempts++;const body=route.request().postDataJSON();assert.equal(body.blockId,'seat-ledger');assert.equal(body.projectId,projectId);assert.equal(body.sessionId,sessionId);assert.equal(body.contextSha256,'b'.repeat(64));assert.equal('text'in body,false);
   if(!request){request=body;return route.fulfill({status:503,json:{detail:'Acceptance reply unavailable. Recover the saved request.'}});}
   assert.deepEqual(body,request);result={...job,acceptedRunId:request.requestId,replayed:true,workOrder:{version:1,kind:'build_block',blockId:request.blockId,contextSha256:request.contextSha256}};
  }
  await route.fulfill({json:result});
 });
 await page.goto(process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194');
 await page.locator('#project-file-input').setInputFiles({name:'theatre.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(toProjectFile(project)))});
 await page.waitForFunction(id=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').id===id,projectId);
 // Retained legacy requests remain recoverable; new module work uses external handoff.
 await page.evaluate(async({projectId,sessionId})=>{
  const {pendingBlockOrder,saveBlockOrder,blockOrderPayload}=await import('/src/block-work-order-client.mjs');
  const {engineeringCall}=await import('/src/engineering-client.mjs');
  const order=pendingBlockOrder(projectId,sessionId,'seat-ledger','b'.repeat(64));
  saveBlockOrder(localStorage,projectId,order);
  try{await engineeringCall({token:'fixture'},'work-orders/block',blockOrderPayload(order));throw Error('Expected ambiguous acknowledgement');}
  catch(error){if(error.status!==503)throw error;}
 },{projectId,sessionId});
 await page.reload();await page.getByRole('tab',{name:'Review',exact:true}).click();
 await page.getByRole('button',{name:'Retry saved block request',exact:true}).waitFor();await page.waitForTimeout(1500);assert.equal(attempts,1,'An ambiguous failure must not automatically start another order');
 const saved=await page.evaluate(id=>JSON.parse(localStorage.getItem('atmem-block-order-v1:'+id)),projectId);assert.deepEqual({...saved,version:undefined},{...request,version:undefined});
 await page.reload();await page.locator('.stage-tabs button').filter({hasText:'Review'}).click();
 await page.getByRole('button',{name:'Retry saved block request',exact:true}).click();
 await page.waitForFunction(id=>localStorage.getItem('atmem-block-order-v1:'+id)===null,projectId);
 assert.equal(attempts,2);assert.equal(ordinaryStarts,0);
 const after=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 assert.equal(after.extensions?.architectureWork?.intents?.length||0,0,'A typed execution control must not become a global architecture requirement');assert.deepEqual(errors,[]);
 console.log('Legacy typed block request retained through failed acknowledgement and reload; retry reused exact block/session/nonce/digest without global intent or an ordinary start.');
}finally{await browser.close();}
