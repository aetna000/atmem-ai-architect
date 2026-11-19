// Browser transfer check: a second source refines an existing laboratory design.
// Service captures are fixtures; this does not constitute native model evidence.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {zipSync,strToU8} from 'fflate';
import {chromium} from '@playwright/test';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const source='a'.repeat(64),context='b'.repeat(64);
const base=process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194';
const scenarios=[{name:'Register',steps:[{sender:'Scanner',receiver:'Ledger',action:'Register stable sample key'}]},
 {name:'Recover',steps:[{sender:'Scanner',receiver:'Ledger',action:'Replay stable key after disconnect'}]}];
const buildSpec={inputs:'Stable sample key',outputs:'Durable receipt',behavior:'One effect per key',failures:'Reconcile timeout',implementation:'Transactional ledger',infrastructure:'Site database',operations:'Backup and restore',tests:'Race concurrent replay',scenarios};
const node=(id,parent)=>({id,type:'resource',position:{x:0,y:0},data:{label:id,provider:'tools',kind:'resource',origin:'proposed',buildSpec,...(parent?{parentBlockId:parent}:{})}});
const contract={transport:'HTTPS',input:'Sample key',output:'Receipt',authorization:'Lab operator',failure:'Replay same key',verification:'Two replays create one record'};
const original=fromProjectFile(toProjectFile({id:'laboratory-update',version:1,revision:3,name:'Laboratory custody',provider:'tools',nodes:[node('Laboratory'),node('Ledger','Laboratory')],
 edges:[{id:'register',source:'Laboratory',target:'Ledger',label:'Register sample',interfaceSpec:contract}],
 needs:[{id:'once',statement:'Register each sample once.',acceptance:'Two concurrent registrations produce one durable receipt.',kind:'nonfunctional',priority:'must',status:'met',source:'user',links:['Ledger']}],
 decisions:[{id:'adr-one',title:'Keep site data',status:'Accepted',decision:'Keep custody records on premises.'}],
 extensions:{designSources:[{name:'Lab brief.txt',sha256:source,text:'1. Register samples exactly once.'}],systemSpec:{title:'Laboratory custody',decomposition:'Ledger and scanner responsibilities',infrastructure:'Portable site service',operations:'Backup and restore',testing:'Replay and recover',journeys:scenarios,
 stateMachines:[{name:'Sample',states:['New','Registered'],initial:'New',transitions:[{from:'New',to:'Registered',event:'Registered'}]}],deploymentUnits:[{name:'Lab runtime',placement:'on-prem',blocks:['Laboratory','Ledger']}]}}})).project;
const engineeringModel={format:'atmem.engineering-model',version:1,id:'lab-model',name:'Laboratory custody model',elements:[
 {id:'sample-key',name:'SampleKey',kind:'dataType',basis:'proposed'},
 {id:'receipt',name:'RegistrationReceipt',kind:'class',basis:'proposed',blockId:'Ledger',requirementIds:['once'],description:'Identifies the durable registration outcome.',attributes:[{id:'receipt-key',name:'sampleKey',typeRef:'sample-key',visibility:'private'}]},
 {id:'receipt-row',name:'ReceiptRecord',kind:'entity',basis:'proposed',blockId:'Ledger',columns:[{id:'receipt-row-key',name:'sampleKey',typeRef:'sample-key',nullable:false}],primaryKey:['receipt-row-key']}
 ],relationships:[{id:'receipt-mapping',name:'Durable registration',kind:'mapping',source:'receipt',target:'receipt-row'}],diagrams:[
 {id:'receipt-class',name:'Registration contract',kind:'class',placements:[{elementId:'receipt',x:0,y:0}],relationships:[]},
 {id:'receipt-schema',name:'Registration identity',kind:'schema',placements:[{elementId:'receipt-row',x:0,y:0}],relationships:[]}
 ]};
const file={name:'Scanner recovery.txt',mimeType:'text/plain',buffer:Buffer.from('2. After a link outage scanners replay the original sample key and retrieve its durable receipt.\n')};
const browser=await chromium.launch();
try{
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let saved,started,capture,legacy=0;
 const job={id:'lab-session',state:'idle',run:1,last_status:'completed',model:'gpt-6.2-sol',effort:'medium'};
 await page.addInitScript(project=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'medium'}));},original);
 await page.route('**/api/**',async route=>{
  const pathname=new URL(route.request().url()).pathname;let result={status:'disabled',projects:[],bin:[],sessions:[],events:[],artifacts:[]};
  if(pathname==='/api/session')result={status:'local-sidecar',token:'fixture',engineeringEnabled:true,providers:{codex:{installed:true,available:true,signedIn:true}}};
  if(pathname==='/api/projects/save'){saved=route.request().postDataJSON().file;result={saved:true,sha256:context};}
  if(pathname==='/api/design-sources'){
   assert.equal(route.request().postDataJSON().projectId,original.id);
   const [source]=route.request().postDataJSON().attachments;assert.deepEqual(Buffer.from(source.data,'base64'),file.buffer);
   result={sources:[{name:source.name,mime:source.mime,text:file.buffer.toString(),sha256:hash(file.buffer)}]};
  }
  if(pathname==='/api/engineering/create')result={id:job.id,state:'idle',model:job.model,effort:job.effort};
  if(pathname==='/api/engineering/start'){
   started=route.request().postDataJSON();assert.equal(saved.extensions.designSources.length,2);
   assert.equal(saved.design.nodes.length,2);
   const draft={version:1,baseRevision:saved.meta.revision,sourceSlots:[1,2],title:'Scanner recovery',addNodes:[],addEdges:[],requirements:[],engineeringModel,
    updateNodes:[{id:'Ledger',data:{buildSpec:{failures:'Read the stored receipt after the scanner link returns.'}}}],
    updateEdges:[{id:'register',interfaceSpec:{verification:'Disconnect after commit and replay the original sample key.'}}],
    requirementCoverage:[{id:'once',sourceSlot:1,reference:'1. Registration',links:['Ledger']},{id:'once',sourceSlot:2,reference:'2. Recovery',links:['Ledger']}]};
   const bytes=strToU8(JSON.stringify(draft)),archive=zipSync({'architecture.canvas.json':bytes,'architecture.review.md':strToU8('Draft SHA-256: '+hash(bytes)),
    'specs/laboratory/plan.md':strToU8('# Scanner recovery\n\nKeep the existing ledger and accepted custody requirements.\n')});
   capture={archive,artifact:{id:'lab-update',runId:1,sha256:hash(archive),files:['architecture.canvas.json','architecture.review.md','specs/laboratory/plan.md'].map(path=>({path,kind:'file'}))}};result=job;
  }
  if(pathname==='/api/engineering/events')result={events:started?[{sequence:1,runId:1,kind:'accepted',text:started.text}]:[],session:job};
  if(pathname==='/api/engineering/artifacts')result={artifacts:capture?[capture.artifact]:[]};
  if(pathname==='/api/engineering/delivery'&&capture)result={relation:'matches_saved_design',savedFileSha256:context,artifact:capture.artifact,session:job,context:{sha256:context},sourceFigureEvidence:{artifactId:capture.artifact.id,contextSha256:context,deliveries:[]}};
  if(pathname==='/api/engineering/reconciliation')result={status:'proposal_missing'};
  if(pathname==='/api/engineering/download')return route.fulfill({body:Buffer.from(capture.archive),contentType:'application/zip',headers:{'X-Artifact-Sha256':capture.artifact.sha256}});
  if(pathname==='/api/architect')legacy++;
  await route.fulfill({json:result});
 });
 await page.goto(base);
 await page.locator('#chat-attachment-input').setInputFiles(file);
 try{await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').extensions?.architectureAmendments?.length===1);}catch(error){console.log({started:!!started,captured:!!capture,errors});console.log((await page.locator('body').innerText()).slice(-9000));await page.screenshot({path:'/tmp/atmem-amendment-failure.png'});throw error;}
 const current=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 assert.equal(current.nodes.length,2);assert.equal(current.edges.length,1);assert.equal(current.needs.length,1);
 assert.deepEqual(current.nodes.map(n=>n.id),original.nodes.map(n=>n.id));assert.deepEqual(current.nodes[1].position,original.nodes[1].position);
 assert.deepEqual(current.needs,original.needs);assert.deepEqual(current.decisions[0],original.decisions[0]);
 assert.match(current.nodes[1].data.buildSpec.failures,/scanner link returns/);assert.equal(current.nodes[1].data.buildSpec.behavior,buildSpec.behavior);
 assert.match(current.edges[0].interfaceSpec.verification,/Disconnect after commit/);assert.equal(current.edges[0].target,'Ledger');
 assert.equal(current.extensions.architectureDraftQuality.ready,true);assert.equal(current.extensions.architectureAmendments[0].coverage.length,2);
 assert.deepEqual(current.extensions.engineeringModel,engineeringModel);
 assert.equal(legacy,0);assert.deepEqual(errors,[]);
 await page.reload();await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').extensions?.architectureAmendments?.length===1);
 assert.deepEqual((await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')))).needs,original.needs);
 assert.deepEqual((await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')))).extensions.engineeringModel,engineeringModel);
 console.log('Captured typed class/schema model applied and survived reload. Service fixture; no native generation claim.');
 console.log('Second source automatically refined existing laboratory blocks and interfaces, preserved accepted scope and IDs, retained amendment receipts, and survived reload.');
}finally{await browser.close();}
