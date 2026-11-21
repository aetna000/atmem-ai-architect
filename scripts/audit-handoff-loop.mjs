import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import path from 'node:path';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {chromium} from 'playwright';
import {unzipSync,strFromU8} from 'fflate';
import {parseProjectFile} from '../src/project-file.mjs';
import {buildReview} from '../src/build-review.mjs';

const [url='http://127.0.0.1:5175/',...sources]=process.argv.slice(2);
if(!sources.length)throw Error('Supply the specification files after the local URL.');
const resumePath=sources[0]==='--resume'?sources[1]:null;
const baseline=resumePath?parseProjectFile(fs.readFileSync(resumePath,'utf8')).project:null;
const sourceCount=resumePath?JSON.parse(fs.readFileSync(resumePath)).extensions.designSources.length:sources.length;
const evidence=process.env.AUDIT_EVIDENCE||'/tmp/atmem-handoff-loop';
fs.mkdirSync(evidence,{recursive:true});
const inputFile=path.join(evidence,'inputs.json');
const expectedSources=resumePath
 ? (fs.existsSync(inputFile)?JSON.parse(fs.readFileSync(inputFile)):JSON.parse(fs.readFileSync(resumePath)).extensions.designSources.map(s=>({name:s.name,sha256:s.sha256})))
 : sources.map(file=>({name:path.basename(file),sha256:createHash('sha256').update(fs.readFileSync(file)).digest('hex')}));
fs.writeFileSync(inputFile,JSON.stringify(expectedSources,null,2));
const checks=[],events=[];let completed=false;
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({acceptDownloads:true,viewport:{width:1512,height:945}});
await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.2-sol',effort:'low'})));
page.on('pageerror',e=>{events.push({error:e.message});console.log('BROWSER ERROR',e.message);});
page.on('response',async response=>{
 if(new URL(response.url()).pathname==='/api/projects/save'){
  const file=response.request().postDataJSON().file;
  if(file?.meta)fs.writeFileSync(path.join(evidence,'project.json'),JSON.stringify(file,null,2));
 }
});
function check(name,passed,detail){checks.push({name,passed,detail});console.log(JSON.stringify(checks.at(-1)));}
try{
 await page.goto(url);
 fs.writeFileSync(path.join(evidence,'candidate.json'),JSON.stringify({url,startedAt:new Date().toISOString(),scripts:await page.locator('script[type=module][src]').evaluateAll(nodes=>nodes.map(n=>new URL(n.src).pathname))},null,2));
 if(resumePath)await page.locator('#project-file-input').setInputFiles(resumePath);
 else await page.locator('#requirements-file-input').setInputFiles(sources);
 if(resumePath&&sources.includes('--repair')){
  await page.getByRole('tab',{name:'Review',exact:true}).click();
  const form=page.locator('form:has(#engineering-intent)');await form.waitFor({timeout:60000});
  await form.locator('summary').click();
  const saved=parseProjectFile(fs.readFileSync(resumePath,'utf8')).project,review=buildReview(saved);
  const gaps=review.requirements.filter(r=>!review.cases.some(c=>c.requirementIds.length===1&&c.requirementIds[0]===r.id)).map(r=>({id:r.id,statement:r.statement}));
  await page.locator('#engineering-intent').fill('Repair this existing source-based architecture. Every requirement needs a dedicated case with only that requirement ID; shared integration cases cannot substitute. Check all case setup/input/action/expected for semantic consistency. '+(process.env.AUDIT_REPAIR_NOTES?fs.readFileSync(process.env.AUDIT_REPAIR_NOTES,'utf8'):'')+'  Preserve every requirement ID, statement, contract, page and owner decision. Preserve valid case behavior and IDs while correcting faulty fixtures and assertions. Add concrete module verificationCases for all missing IDs: '+JSON.stringify(gaps)+'. Use the full original sources and maintain source coverage. Include independently observable setup/input/action/expected/evidence. Recompute the exact Draft SHA-256 line in architecture.review.md for the final canvas. No implementation, site access or deployment.');
  await form.getByRole('button',{name:'Refine architecture',exact:true}).click();await page.waitForTimeout(3000);
 }
 let capture,last='',started=Date.now(),settledRun=null,settledAt=null;
 while(Date.now()-started<75*60*1000){
  await page.waitForTimeout(5000);
  const filePath=path.join(evidence,'project.json');
  if(!fs.existsSync(filePath))continue;
  const raw=JSON.parse(fs.readFileSync(filePath));const {project}=parseProjectFile(JSON.stringify(raw));
  const state=await page.evaluate(async projectId=>{
   const session=await(await fetch('/api/session')).json();
   const result=await(await fetch('/api/engineering/list',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({projectId})})).json();
   return result.sessions?.at(-1);
  },project.id);
  const progress=JSON.stringify({state,blocks:project.nodes.length,requirements:project.needs.length,types:project.extensions?.architectureDiagrams?.views.length||0});
  if(progress!==last){console.log(progress);last=progress;await page.screenshot({path:path.join(evidence,'live.png')});}
  fs.writeFileSync(path.join(evidence,'live-ui.txt'),await page.locator('body').innerText());
  fs.writeFileSync(path.join(evidence,'generation-ui.txt'),(await page.locator('.engineering-panel,.engineering-workspace-panel').allTextContents()).join('\n'));
  if(!state&&Date.now()-started>120000){check('queued request reaches a durable job',false,(await page.locator('[role=alert]:visible').allTextContents()));throw Error('No durable job accepted within two minutes. See live-ui.txt and live.png.');}
  const readyPreview=page.locator('.preview-bar:visible').getByRole('button',{name:'Apply',exact:true});
  if(state?.state==='idle'&&await readyPreview.count()&&await readyPreview.isEnabled()){await readyPreview.click();await page.waitForTimeout(2000);continue;}
  let settledArtifact=null;
  if(state?.state==='idle'){
   settledArtifact=await page.evaluate(async projectId=>{
    const session=await(await fetch('/api/session')).json();
    const response=await fetch('/api/engineering/delivery',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({projectId})});
    if(!response.ok)return {error:(await response.json()).detail||'Delivery rejected the saved project'};const report=await response.json();
    return report.artifact?{id:report.artifact.id,run:report.artifact.runId}:null;
   },project.id);
   if(settledArtifact?.error){check('settled delivery remains readable',false,settledArtifact.error);throw Error(settledArtifact.error);}
   if(settledArtifact?.run!==state.run)continue;
  }
  if(project.nodes.length&&state?.state==='idle'&&project.extensions?.architectureDocuments?.artifactId===settledArtifact?.id){capture=project;break;}
  if(state?.state==='idle'&&state.last_status){
   if(settledRun!==state.run){settledRun=state.run;settledAt=Date.now();}
   if(Date.now()-settledAt<60000)continue;
   await page.waitForTimeout(12000);
   const live=await page.evaluate(async projectId=>{
    const session=await(await fetch('/api/session')).json();
    const result=await(await fetch('/api/engineering/list',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({projectId})})).json();
    return result.sessions?.at(-1);
   },project.id);
   if(live?.state==='running'||live?.state==='starting'||live?.run!==state.run)continue;
   await page.getByRole('tab',{name:/Review/}).first().click();
   await page.waitForTimeout(4000);
   const open=page.getByRole('button',{name:'Open architecture',exact:true});
   await open.waitFor({timeout:60000}).catch(()=>{});
   if(await open.count()&&await open.isEnabled()){await open.click();await page.locator('.preview-bar:visible').waitFor({timeout:90000}).catch(()=>{});}
   const apply=page.locator('.preview-bar:visible').getByRole('button',{name:'Apply',exact:true});
   if(await apply.count()&&await apply.isEnabled()){await apply.click();await page.waitForTimeout(3000);}
   const updated=parseProjectFile(fs.readFileSync(filePath,'utf8')).project;
   if(updated.nodes.length&&updated.extensions?.architectureDocuments?.artifactId===settledArtifact?.id){capture=updated;break;}
   fs.writeFileSync(path.join(evidence,'failed-review.txt'),await page.locator('body').innerText());
   await page.screenshot({path:path.join(evidence,'failed-review.png')});
   check('generated architecture reaches the Board',false,await page.locator('[role=alert]:visible').allTextContents());break;
  }
 }
 if(!capture)throw Error('Generation did not produce an applied project. See evidence.');
 const review=buildReview(capture);
 if(baseline){
  const changed=[];
  for(const need of baseline.needs){const after=capture.needs.find(r=>r.id===need.id);if(!after||Object.entries(need).some(([k,v])=>k!=='links'&&!isDeepStrictEqual(v,after[k]))||(need.links||[]).some(id=>!after.links?.includes(id)))changed.push('requirement:'+need.id);}
  for(const node of baseline.nodes){const after=capture.nodes.find(n=>n.id===node.id);if(!after||['label','provider','origin','service','deploymentMode','config'].some(k=>!isDeepStrictEqual(node.data[k],after.data[k])))changed.push('component:'+node.id);}
  for(const edge of baseline.edges){const after=capture.edges.find(e=>e.id===edge.id);if(!after||['source','target','label'].some(k=>!isDeepStrictEqual(edge[k],after[k])))changed.push('interface:'+edge.id);}
  for(const q of baseline.openQuestions||[]){const after=capture.openQuestions?.find(r=>r.id===q.id);if(!after||['question','owner','answer','status','decisionBy','interim'].some(k=>!isDeepStrictEqual(q[k],after[k]))||['links','requirementIds','interfaceIds'].some(k=>(q[k]||[]).some(id=>!after[k]?.includes(id))))changed.push('owner-gate:'+q.id);}
  for(const d of baseline.decisions||[])if(!isDeepStrictEqual(d,capture.decisions?.find(row=>row.id===d.id)))changed.push('recorded-decision:'+d.id);
  check('refinement preserves saved scope and ownership',changed.length===0,{requirements:baseline.needs.length,components:baseline.nodes.length,interfaces:baseline.edges.length,changed});
 }
 check('exact captured architecture passes every required design gate',capture.extensions?.architectureDraftQuality?.ready===true,capture.extensions?.architectureDraftQuality?.gates);
 check('dedicated fixtures are distinct',review.caseSpecificityIssues.length===0,review.caseSpecificityIssues);
 check('all submitted sources retained',capture.extensions.designSources.length===sourceCount&&expectedSources.every(expected=>capture.extensions.designSources.some(s=>s.name===expected.name&&s.sha256===expected.sha256)),expectedSources);
 check('project-specific work applied',capture.nodes.length>0&&capture.edges.length>0&&capture.needs.length>0);
 check('all 28 diagram types populated',review.counts.types===28,{types:review.counts.types});
 const missingFields=review.diagrams.flatMap(type=>type.pages.flatMap(p=>p.findings.filter(f=>f.includes('· Missing ')).map(f=>type.id+' / '+f)));
 check('required diagram fields defined',missingFields.length===0,missingFields);
 check('all requirements have dedicated verification cases',review.counts.dedicatedCovered===review.requirements.length,{cases:review.cases.length,requirements:review.requirements.length});
 check('every interface documented',review.interfaces.every(r=>!r.missing.length),{missing:review.interfaces.filter(r=>r.missing.length).map(r=>r.id)});
 await page.getByRole('tab',{name:/Board/}).first().click();
 const visual=[];
 for(const view of capture.extensions.architectureDiagrams?.views||[]){
  await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption('view/'+view.id);
  await page.waitForTimeout(180);
  const cells=await page.locator('.drawio-canvas:visible').last().locator('[role=button]').count();
  visual.push({id:view.id,kind:view.kind,cells});
  if(['erd','api','sequence','recovery'].includes(view.kind))await page.screenshot({path:path.join(evidence,view.kind+'.png')});
 }
 fs.writeFileSync(path.join(evidence,'visual.json'),JSON.stringify(visual,null,2));
 check('all typed drawings render',visual.length===28&&visual.every(row=>row.cells>0),visual);
 for(const name of ['Board','Requirements','Choices','Review','Delivery']){
  console.log('Inspecting stage: '+name);
  await page.getByRole('tab',{name:new RegExp(name)}).first().click();await page.waitForTimeout(700);
  fs.writeFileSync(path.join(evidence,name+'-text.txt'),await page.locator('body').innerText());
  await page.screenshot({path:path.join(evidence,name+'.png'),timeout:15000,animations:'disabled'});
 }
 console.log('Downloading the canonical project handoff');
 await page.getByRole('button',{name:'Download project ZIP',exact:true}).first().waitFor({timeout:60000});
 const download=Promise.race([page.waitForEvent('download',{timeout:180000}),
  page.locator('.outputs-view [role=alert]').waitFor({state:'visible',timeout:180000}).then(async()=>{throw Error(await page.locator('.outputs-view [role=alert]').innerText());})]);
 await page.getByRole('button',{name:'Download project ZIP',exact:true}).first().click();
 const archive=path.join(evidence,'handoff.zip');await(await download).saveAs(archive);
 const files=unzipSync(fs.readFileSync(archive));
 const decode=name=>JSON.parse(strFromU8(files[name]));
 const captureReceipt=decode('captured-evidence.json'),draftReceipt=decode('design-evidence.json'),sourceFigures=decode('source-figures.json');
 check('captured proposal, source images and history verified',captureReceipt.status==='verified'&&draftReceipt.status==='verified'&&sourceFigures.complete===true&&captureReceipt.artifactId===capture.extensions.architectureDocuments.artifactId&&draftReceipt.artifactId===capture.extensions.architectureDocuments.artifactId,
  {capture:captureReceipt.status,draft:draftReceipt.status,figures:sourceFigures.embedded,referenced:sourceFigures.referenced});
 const snapshot=decode('project.atmem-ai-architect.json'),tasks=decode('spec-kit/tasks.json').tasks;
 check('download contains applied revision',snapshot.meta.id===capture.id&&snapshot.design.nodes.length===capture.nodes.length);
 check('tasks derived from actual modules and interfaces',tasks.length>12&&tasks.some(t=>t.phase==='Contracts')&&tasks.some(t=>t.phase==='Components'),{tasks:tasks.length});
 check('every page has an SVG',Object.keys(files).filter(n=>n.startsWith('diagrams/')&&n.endsWith('.svg')).length>=1+(capture.extensions.architectureDiagrams?.views.length||0)+(capture.extensions.systemModel?.diagrams.length||0)+(capture.extensions.engineeringModel?.diagrams.length||0));
 const manifest=decode('manifest.json');
 const digests=Object.entries(manifest.fileDigests);
 check('every payload matches its digest',digests.length===Object.keys(files).filter(n=>!n.endsWith('/')&&n!=='manifest.json').length&&digests.every(([name,record])=>files[name]&&files[name].byteLength===record.bytes&&createHash('sha256').update(files[name]).digest('hex')===record.sha256),{payloads:digests.length});
 const receiving=path.resolve(evidence,'qualification-run');fs.mkdirSync(receiving,{recursive:true});
 for(const [name,bytes] of Object.entries(files)){if(name.endsWith('/'))continue;const dest=path.resolve(receiving,name);assert.ok(dest.startsWith(receiving+path.sep),'Archive path escaped its receiving folder');fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,bytes);}
 const qualification=spawnSync('python3',['qualification/check_handoff.py'],{cwd:receiving,encoding:'utf8'});
 check('offline checker validates source bindings',qualification.status===0,{exit:qualification.status,stdout:qualification.stdout,stderr:qualification.stderr});
 const requirementsPath=path.join(receiving,'qualification/requirements.json'),original=fs.readFileSync(requirementsPath);
 const altered=JSON.parse(original);altered[0].interfaceIds=['nonexistent-interface'];fs.writeFileSync(requirementsPath,JSON.stringify(altered));
 const tampered=spawnSync('python3',['qualification/check_handoff.py'],{cwd:receiving,encoding:'utf8'});fs.writeFileSync(requirementsPath,original);
 check('offline checker rejects changed trace links',tampered.status!==0,{exit:tampered.status,stderr:tampered.stderr});
 const interfacesPath=path.join(receiving,'qualification/interfaces.json'),originalInterfaces=fs.readFileSync(interfacesPath),contracts=JSON.parse(originalInterfaces);
 if(contracts.some(row=>row.pending.length)){
  for(const row of contracts)row.pending=[];
  fs.writeFileSync(interfacesPath,JSON.stringify(contracts));
  const falseQualification=spawnSync('python3',['qualification/check_handoff.py'],{cwd:receiving,encoding:'utf8'});fs.writeFileSync(interfacesPath,originalInterfaces);
  check('offline checker rejects false contract qualification',falseQualification.status!==0,{exit:falseQualification.status,stderr:falseQualification.stderr});
 }
 check('browser has no uncaught failures',events.length===0,events);
 fs.writeFileSync(path.join(evidence,'review.json'),JSON.stringify(review,null,2));
 completed=true;
}catch(error){
 check('audit reaches completion',false,error.message);
 fs.writeFileSync(path.join(evidence,'audit-failure.txt'),await page.locator('body').innerText().catch(()=>error.message));
 await page.screenshot({path:path.join(evidence,'audit-failure.png'),timeout:15000}).catch(()=>{});
 throw error;
}finally{
 fs.writeFileSync(path.join(evidence,'audit.json'),JSON.stringify({checks,events,completed,passed:completed&&checks.length>5&&checks.every(c=>c.passed)},null,2));
 await browser.close();
}
assert.ok(checks.length>5&&checks.every(c=>c.passed),'Audit failed. Repair the engine and repeat this command against a fresh project.');
