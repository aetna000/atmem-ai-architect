// Actual browser/native/API/artifact round trip. Design consultation is an explicit
// fixture response; requirement editing, saved state and all native work are real.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';
import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';import {chromium} from '@playwright/test';
import {validateImport} from '../src/core.mjs';import {deliveryPack} from '../src/delivery.mjs';import {artifactWorkProjection} from '../src/artifact-work.mjs';
const base=process.env.ATMEM_ENGINEERING_PREVIEW_URL||'http://127.0.0.1:5282',out=path.resolve(process.env.ATMEM_ARCHITECT_WORK_EVIDENCE||'.local/engine-product/native-artifact-reconciliation');
if(fs.existsSync(out))throw Error('Preserve previous evidence; choose a new output directory.');fs.mkdirSync(out,{recursive:true});
const endpoint='unix:///Users/javadtaghia/.colima/architect-qualification/docker.sock',sha=value=>createHash('sha256').update(value).digest('hex');
const sourcePaths=execFileSync('git',['ls-files','server','src','agent-skills'],{encoding:'utf8'}).trim().split('\n'),source=Object.fromEntries(sourcePaths.map(name=>[name,sha(fs.readFileSync(name))]));
const commit=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();fs.writeFileSync(path.join(out,'source.json'),JSON.stringify({commit,files:source},null,2)+'\n');
const requirement=unit=>`Provide independent CommonJS readings.cjs exporting normalize(millimetres) and unit. Accept every finite nonnegative number primitive, reject all other values with TypeError, and return rainfall in ${unit==='cm'?'centimetres (divide by10)':'metres (divide by1000)'}. Export unit as ${unit}. Preserve the client-owned rain gauge and archive catalogue. Keep Unicode labels such as 🛰️ in documentation. No network or cloud dependencies.`;
const node=(id,label,origin,x)=>({id,position:{x,y:0},data:{kind:'resource',provider:'tools',origin,label,description:'Explicit local responsibility: '+label+'.',config:{region:'Local'}}});
const project=validateImport({id:'orchard-work-'+Date.now(),version:1,revision:1,name:'Orchard rainfall readings',provider:'tools',requirements:'An independent local reading converter. Keep the existing rain gauge and unrelated archive catalogue unchanged.',nodes:[node('gauge','Existing rain gauge','existing',0),node('viewer','Local reading viewer','new',300),node('archive','Archive catalogue','existing',600)],edges:[{id:'readings',source:'gauge',target:'viewer',label:'Read-only rainfall readings'}],needs:[{id:'conversion',kind:'functional',priority:'must',status:'open',source:'user',statement:requirement('cm'),links:['viewer']},{id:'archive',kind:'functional',priority:'must',status:'open',source:'user',statement:'Preserve the existing archive catalogue without changing its implementation or ownership.',links:['archive']}],decisions:[]});
const intent='Build or reconcile the local project from its current saved design. Preserve existing systems and accepted constraints, run meaningful local tests, and report remaining limits. Keep the final reply concise.';
const browser=await chromium.launch({headless:true});let page,receipt={passed:false,sourceCommit:commit,projectId:project.id,model:'gpt-6.1-sol',effort:'high',cloudOperations:false};const errors=[],devReloads=[],submissions=[],prepared=[],artifacts=[];let designConsultations=0;
try{
 page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));
 page.on('websocket',socket=>socket.on('framereceived',frame=>{try{const value=JSON.parse(frame.payload);if(['update','full-reload'].includes(value.type))devReloads.push(value.type);}catch{}}));
 page.on('request',r=>{if(/\/api\/engineering\/(start|steer)$/.test(r.url())){submissions.push({action:r.url().split('/').at(-1),body:r.postDataJSON()});fs.writeFileSync(path.join(out,'submissions.json'),JSON.stringify(submissions,null,2)+'\n');}});
 page.on('response',async response=>{if(/\/api\/engineering\/(create|start|steer)$/.test(response.url())&&!response.ok())fs.appendFileSync(path.join(out,'submission-errors.log'),response.status()+' '+await response.text()+'\n');});
 page.on('response',async response=>{if(response.url().endsWith('/api/engineering/reconciliation')&&response.ok())prepared.push(await response.json());});
 await page.addInitScript(p=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(p));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},project);
 await page.route('**/api/architect',route=>{designConsultations++;return route.fulfill({json:{message:'Edited requirement retained. Native work must be regenerated against it.',phase:'Architecture Review',componentReview:{componentId:'viewer',summary:'Check the changed unit against the implementation.',questions:[]}}});});
 await page.goto(base);await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();
 const state=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
 async function api(action,fields={}){return page.evaluate(async({action,fields,projectId})=>{const session=await(await fetch('/api/session')).json(),r=await fetch('/api/engineering/'+action,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({projectId,...fields})});if(!r.ok)throw Error(await r.text());return r.json();},{action,fields,projectId:project.id});}
 async function settled(){
  const deadline=Date.now()+900000;
  while(Date.now()<deadline){
   const jobs=(await api('list')).sessions,job=jobs.at(-1);
   if(job){
    if(job.state==='idle'&&!job.last_status&&await page.getByRole('alert').count())throw Error('The session is idle and the UI reported a rejected submission: '+await page.getByRole('alert').allTextContents());
    assert.equal(job.model,'gpt-6.1-sol');assert.equal(job.effort,'high');receipt.sessionId=job.id;
    const finals=(await api('finalizations',{sessionId:job.id})).finalizations,last=finals.find(f=>f.runId===job.run);
    if(job.state==='idle'&&job.last_status==='completed'&&last&&['local_checks_passed','needs_attention'].includes(last.state))return job;
    if(job.state==='idle'&&['failed','interrupted'].includes(job.last_status))throw Error('Native work did not complete: '+job.last_status);
   }
   await new Promise(r=>setTimeout(r,1000));
  }
  throw Error('Actual native fixture exceeded its explicit wait bound; no replay.');
 }
 for(const unit of ['cm','m']){
  if(unit==='m'){
   await page.getByRole('tab',{name:'Design',exact:true}).click();await page.getByRole('button',{name:/Review Local reading viewer:/}).click();
   const article=page.getByRole('article',{name:'Requirement conversion',exact:true});await article.getByRole('button',{name:'Edit requirement',exact:true}).click();await article.getByRole('textbox',{name:'Requirement text',exact:true}).fill(requirement('m'));await article.getByRole('button',{name:'Save & re-evaluate',exact:true}).click();
   await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).needs.find(r=>r.id==='conversion').statement.includes('metres (divide by1000)'));
   assert.equal(artifactWorkProjection(await state()).mappings[0].contextStatus,'changed');
   await page.locator('.detail-core .architecture-work > summary').click();await page.getByText('Design changed; regenerate mappings',{exact:true}).waitFor();
   await page.screenshot({path:path.join(out,'changed-design.png'),fullPage:true});await page.getByRole('tab',{name:'Build',exact:true}).click();
  }
  await page.getByLabel('What should we build or repair?',{exact:true}).fill(intent);await page.getByRole('button',{name:'Start work',exact:true}).click();
  const job=await settled();console.log('Actual native '+unit+' generation completed.');
  const capture=page.waitForResponse(r=>r.url().endsWith('/api/engineering/capture')&&r.ok());await page.getByRole('button',{name:'Capture package',exact:true}).click();const manifest=await(await capture).json();assert.equal(manifest.runId,job.run);artifacts.push(manifest);
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download package',exact:true}).click();await(await download).saveAs(path.join(out,'artifact-'+unit+'.zip'));assert.equal(sha(fs.readFileSync(path.join(out,'artifact-'+unit+'.zip'))),manifest.sha256);
  fs.writeFileSync(path.join(out,'artifact-'+unit+'.json'),JSON.stringify(manifest,null,2)+'\n');
  const linkedResponse=page.waitForResponse(r=>r.url().endsWith('/api/engineering/reconciliation')&&r.ok());await page.getByRole('button',{name:'Link proposed mappings',exact:true}).click();const bound=await(await linkedResponse).json();assert.equal(bound.status,'prepared');
  await page.waitForFunction(count=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.architectureWork.artifactMappings.length===count,unit==='cm'?1:2);
  const current=await state(),model=artifactWorkProjection(current);assert.equal(model.mappings.at(-1).contextStatus,'current');assert.deepEqual(current.nodes.map(n=>n.data.origin),project.nodes.map(n=>n.data.origin));assert.deepEqual(current.edges,project.edges);
  const mapped=model.mappings.at(-1);assert(mapped.records.some(r=>r.kind==='implementation'&&r.data.files.includes('readings.cjs')));assert(mapped.records.every(r=>r.source==='agent'&&r.agreement==='proposed'));
  fs.writeFileSync(path.join(out,'mapping-'+unit+'.json'),JSON.stringify(bound,null,2)+'\n');fs.writeFileSync(path.join(out,'project-'+unit+'.json'),deliveryPack(current)['project.atmem-ai-architect.json']);
  execFileSync('.venv/bin/python',['scripts/engine-evaluation/check-reading-library.py','--artifact',path.join(out,'artifact-'+unit+'.zip'),'--unit',unit,'--endpoint',endpoint,'--output',path.join(out,'independent-'+unit+'.json')],{stdio:'pipe'});
  const checked=JSON.parse(fs.readFileSync(path.join(out,'independent-'+unit+'.json'),'utf8'));assert.equal(checked.status,'passed');assert.equal(checked.independentAssertions,20);console.log('Independent '+unit+' contract:20 checks passed; actual mappings linked.');
 }
 execFileSync('.venv/bin/python',['scripts/engine-evaluation/check-reading-library.py','--artifact',path.join(out,'artifact-cm.zip'),'--unit','m','--endpoint',endpoint,'--output',path.join(out,'old-artifact-new-contract.json')],{stdio:'pipe'});assert.equal(JSON.parse(fs.readFileSync(path.join(out,'old-artifact-new-contract.json'),'utf8')).status,'failed');
 const final=await state(),view=artifactWorkProjection(final);assert.deepEqual(view.mappings.map(m=>m.contextStatus),['superseded','current']);
 assert(view.mappings[0].records.some(old=>old.kind==='implementation'&&view.mappings[1].records.some(r=>r.id===old.id&&r.kind==='implementation')),'native work retains implementation mapping identity across the requirement update');
 const pack=deliveryPack(final);assert.deepEqual(JSON.parse(pack['spec-kit/artifact-mappings.json']),view);assert.deepEqual(JSON.parse(pack['architecture-artifact-mappings.json']),view);
 fs.writeFileSync(path.join(out,'final-artifact-mappings.json'),pack['architecture-artifact-mappings.json']);fs.writeFileSync(path.join(out,'generation-quality.json'),pack['generation-quality.json']);
 await page.reload();await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();await page.getByText('Work completed · gpt-6.1-sol · high',{exact:true}).waitFor({timeout:60000});await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')).extensions.architectureWork.artifactMappings.length===2);await page.locator('.engineering-panel .architecture-work > summary').click();await page.getByText('Earlier artifact retained',{exact:true}).waitFor();
 await page.screenshot({path:path.join(out,'linked-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'linked-mobile.png'),fullPage:true});
 assert.equal(submissions.length,2);assert(submissions.every(s=>s.action==='start'&&s.body.text===intent));assert.deepEqual(errors,[]);assert.deepEqual(devReloads,[]);assert.equal(designConsultations,1);
 const changed=sourcePaths.filter(name=>sha(fs.readFileSync(name))!==source[name]);assert.deepEqual(changed,[]);
 receipt={...receipt,passed:true,artifactSha256s:artifacts.map(a=>a.sha256),nativeRequests:2,mappingVersions:2,independentChecksPerArtifact:20,oldArtifactFailsChangedRequirement:true,reloadWithoutReplay:true,sourceChangedDuringRun:[],errors,devReloads,boundary:'Actual browser requirement edits/save/Build/native/API/immutable artifact linking, retained mapping revisions, independent isolated module behavior, stale old-package counterexample and reload. Only the legacy Design consultation response is a declared fixture. Evaluator-authored orchard domain, not a blinded holdout, original28 acceptance, complete cloud system or deployment evidence.'};
 console.log('Actual native shared-work-model round trip passed.');
}catch(error){if(page){fs.writeFileSync(path.join(out,'failure.txt'),await page.locator('body').innerText());await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});}throw error;}
finally{fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');fs.writeFileSync(path.join(out,'submissions.json'),JSON.stringify(submissions,null,2)+'\n');await browser.close();}
