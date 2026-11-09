// Deterministic browser scenarios. All prices/rates are synthetic test inputs, not quotations.
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import { unzipSync, strFromU8 } from 'fflate';
import { toProjectFile } from '../src/project-file.mjs';
import { WORK_PHASES } from '../src/estimate.mjs';
const out='/tmp/forma-qa/delivery';fs.mkdirSync(out,{recursive:true});
const node=(id,label,kind,x)=>({id,type:'resource',position:{x,y:100},data:{label,kind,provider:'aws',description:label,origin:'proposed',config:{region:'ap-southeast-2',classification:'Internal',timeout:5000}}});
const project={id:'browser-delivery',version:1,revision:4,name:'AWS policy assistant',provider:'aws',requirements:'Answer staff policy questions',nodes:[node('files','Amazon S3','source',0),node('llm','Amazon Bedrock','agent',300),node('guard','Bedrock Guardrails','guard',600),node('api','AWS Lambda','tool',900)],edges:[['files','llm'],['llm','guard'],['guard','api']].map(([source,target],i)=>({id:`e${i}`,source,target,type:'smoothstep',label:'policy context'})),needs:[],assumptions:[],openQuestions:[{id:'region',question:'Confirm data retention with the customer',status:'open'}],decisions:[{id:'cloud',title:'Cloud',subject:'platform.cloud',decision:'aws',status:'Accepted'},{id:'location',title:'Region',subject:'cloud.region',decision:'ap-southeast-2',status:'Accepted'}]};
fs.writeFileSync(`${out}/input.atforma.json`,JSON.stringify(toProjectFile(project)));
let server, browser;
let base=process.env.ATMEM_ARCHITECT_DELIVERY_TEST_URL;
if(!base){
 const probe=createServer();await new Promise(resolve=>probe.listen(0,'127.0.0.1',resolve));
 const port=probe.address().port;await new Promise(resolve=>probe.close(resolve));base=`http://127.0.0.1:${port}`;
 server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:new URL('..',import.meta.url),stdio:'ignore'});
}
try {
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}if(i===99)throw Error('Delivery test server did not start');await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({...(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')?{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}:{}),headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{const u=new URL(r.url());if(['http:','https:'].includes(u.protocol)&&!['127.0.0.1','localhost'].includes(u.hostname))external.push(r.url());});
await page.addInitScript(()=>{localStorage.clear();localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'default'}));});
await page.route('**/api/session',r=>r.fulfill({json:{token:'test-token',status:'local-sidecar',providers:{'claude-code':{installed:true,available:true,signedIn:true}}}}));
await page.route('**/api/projects/*',r=>r.fulfill({json:{saved:true,projects:[],bin:[]}}));
await page.route('**/api/models',r=>r.fulfill({json:{models:[]}}));
await page.route('**/api/architect',r=>r.fulfill({json:{message:'Which usage assumption should we clarify first?',phase:'Estimate',proposal:null}}));
await page.route('**/api/memory/*',r=>r.fulfill({json:{status:'disabled'}}));
await page.route('**/api/pricing/*',r=>r.fulfill({json:{available:false,reason:'Synthetic test uses explicitly entered prices.'}}));
let validationCalls=0;await page.route('**/api/terraform/validate',r=>{validationCalls++;return r.fulfill({json:validationCalls===1?{status:'passed',message:'Configuration schema passed. No cloud plan was run.',checks:[{name:'Terraform schema validation',passed:true,output:'Fixture validation result'}]}:{status:'unavailable',message:'Terraform is not installed. No CLI validation was run.',checks:[]}});});
await page.goto(base);
await page.locator('#project-file-input').setInputFiles(`${out}/input.atforma.json`);
assert.equal(await page.locator('.journey-actions .primary').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(243, 162, 180)');
await page.getByText('Project opened.',{exact:true}).waitFor();
const state=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
const tab=(name)=>page.locator('.modes').getByRole('tab',{name}).click();
await page.getByRole('tab',{name:'Requirements',exact:true}).click();
await page.getByRole('button',{name:'Continue to cloud options →',exact:true}).click();
await page.waitForFunction(()=>!document.querySelector('.msg.working'));
await page.getByRole('button',{name:'Review this cloud design →',exact:true}).click();
await page.waitForFunction(()=>!document.querySelector('.msg.working'));
await page.getByRole('button',{name:'Estimate with the remaining risks recorded →',exact:true}).click();
await page.waitForFunction(()=>!document.querySelector('.msg.working'));
const delivery=async()=>{const button=page.getByRole('button',{name:'Prepare a delivery draft with cost gaps noted →',exact:true});if(await button.count()){await button.click();await page.waitForFunction(()=>!document.querySelector('.msg.working'));}else await tab('Delivery draft');};
const est=page.getByRole('region',{name:'Estimate',exact:true});
assert.match(await est.locator('.totals').first().innerText(),/Incomplete/);
await est.getByText('Inspect or edit estimate inputs and sources',{exact:true}).click();
await est.getByLabel('Data stored').fill('100');await est.getByLabel('Amazon S3 unit price').fill('0.02');
assert.match(await est.innerText(),/ROM/);assert.match(await est.locator('.totals').first().innerText(),/USD 2/);
const detail=est.getByLabel('Detailed cloud charges');await detail.locator('summary').click();
const charges=[['files','Storage',100,'GB-month',0.02],['llm','Input tokens',1200,'1k tokens',0.003],['llm','Output tokens',200,'1k tokens',0.015],['guard','Guard checks',1000,'requests',0.001],['api','Requests and runtime',1000,'requests',0.002]];
for(let i=0;i<charges.length;i++){
 const [component,desc,qty,unit,price]=charges[i],prefix=`Charge ${i+1}`;
 await detail.getByRole('button',{name:'Add cloud charge'}).click();
 await detail.getByLabel(`${prefix} component`,{exact:true}).selectOption(component);
 for(const [key,value] of [['charge description',desc],['monthly quantity',qty],['unit',unit],['unit price',price],['service or sku',desc],['price region','ap-southeast-2'],['price source or quote','Synthetic QA quote — not AWS prices']])await detail.getByLabel(`${prefix} ${key}`,{exact:true}).fill(String(value));
}
assert.match(await est.innerText(),/Detailed worksheet/);assert.match(await est.locator('.totals').first().innerText(),/Complete worksheet/);assert.match(await est.locator('.totals').first().innerText(),/USD 11\.6/);
// A currency mismatch never creates a cross-currency grand total.
await detail.getByLabel('Charge 2 currency',{exact:true}).fill('AUD');
assert.match(await est.locator('.totals').first().innerText(),/Mixed currencies/);
await detail.getByLabel('Charge 2 currency',{exact:true}).fill('USD');
const consulting=est.getByLabel('Consulting and build estimate');await consulting.locator('summary').click();
for(const [,label] of WORK_PHASES){
 for(const [key,value] of [['low days','1'],['expected days','2'],['high days','3'],['day rate','1000'],['basis','Synthetic work scope and rate; excludes support']])await consulting.getByLabel(`${label} ${key}`,{exact:true}).fill(value);
}
assert.match(await consulting.innerText(),/USD 10,000/);assert.match(await consulting.innerText(),/All work packages estimated/);
await page.screenshot({path:`${out}/estimates-desktop.png`,fullPage:true});
await delivery();await page.getByLabel('Cloud resource schedule').locator('summary').click();
await page.getByText('S3 foundation generated',{exact:false}).first().waitFor();
let dl=page.waitForEvent('download');await page.getByRole('button',{name:'Download delivery pack',exact:true}).click();let file=await dl.catch(async error=>{console.error(await page.locator('body').innerText(),errors);await page.screenshot({path:`${out}/export-failure.png`});throw error;});await file.saveAs(`${out}/pack.zip`);
const zip=unzipSync(fs.readFileSync(`${out}/pack.zip`)),read=(n)=>strFromU8(zip[n]);
const manifest=JSON.parse(read('manifest.json')),costs=JSON.parse(read('estimate.json'));
for(const name of ['specification.pdf','diagram.pdf','diagram.svg','diagram.png','spec-kit/implementation-spec.pdf']){
 assert.ok(zip[name]?.length>100,`${name} must have content`);
 assert.ok(manifest.files.includes(name),`${name} must be in the manifest`);
 fs.mkdirSync(`${out}/${name.split('/').slice(0,-1).join('/')}`,{recursive:true});fs.writeFileSync(`${out}/${name}`,zip[name]);
}
assert.equal(read('specification.pdf').slice(0,5),'%PDF-');assert.equal(read('diagram.pdf').slice(0,5),'%PDF-');
assert.deepEqual([...zip['diagram.png'].slice(0,8)],[137,80,78,71,13,10,26,10]);
assert.match(read('diagram.svg'),/Amazon S3/);
assert.match(read('START_HERE.md'),/coding agent/);assert.match(read('spec-kit/tasks.md'),/Implement AWS Lambda/);const kit=JSON.parse(read('spec-kit/tasks.json'));assert.equal(kit.snapshotId,manifest.snapshotId);assert.ok(kit.tasks.every(t=>t.status==='todo'));assert.match(read('spec-kit/implementation-spec.pdf').slice(0,5),/%PDF-/);

assert.equal(manifest.designRevision,4);assert.equal(costs.cloud.expected,11.6);assert.equal(costs.consulting.expected,10000);assert.match(read('specification.md'),/Answer staff policy questions/);assert.match(read('handoff.md'),/Confirm data retention/);assert.equal(Object.keys(JSON.parse(read('terraform/main.tf.json')).resource.aws_s3_bucket).length,1);
assert.deepEqual(JSON.parse(read('project.atmem-ai-architect.json')).estimate.details.length,5);
await page.screenshot({path:`${out}/delivery-desktop.png`,fullPage:true});
await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Outputs',exact:true}).click();
const outputs=page.getByRole('region',{name:'Outputs',exact:true});
await outputs.getByRole('heading',{name:'Implementation Spec Kit',exact:true}).waitFor();
await outputs.getByRole('complementary',{name:'Handoff readiness'}).waitFor();
await outputs.getByRole('button',{name:'Review handoff gaps',exact:true}).click();
await outputs.getByRole('heading',{name:'Handoff readiness',exact:true}).waitFor();
assert.match(await outputs.getByLabel('Output preview').innerText(),/cloudPlan: not_run/);
const readiness=JSON.parse(read('spec-kit/readiness.json'));
assert.equal(readiness.snapshotId,manifest.snapshotId);assert.equal(readiness.status,'engineering_required');
const directory=outputs.getByRole('navigation',{name:'Output files'});
await directory.getByRole('button',{name:'tasks.md',exact:true}).click();
await outputs.getByRole('heading',{name:'Detailed implementation tasks',exact:true}).waitFor();
await directory.getByRole('button',{name:'diagram.svg',exact:true}).click();
await outputs.getByRole('img',{name:'Preview diagram.svg'}).waitFor();
await page.waitForFunction(()=>document.querySelector('.output-image')?.naturalWidth>0);
await directory.getByRole('button',{name:'main.tf.json',exact:true}).click();
assert.match(await outputs.locator('.output-code').innerText(),/aws_s3_bucket/);
await directory.getByRole('button',{name:'implementation-spec.pdf',exact:true}).click();
await outputs.locator('iframe[title="Preview spec-kit/implementation-spec.pdf"]').waitFor();
await directory.getByRole('button',{name:'implementation-spec.md',exact:true}).click();
const reviewedSnapshot=await outputs.locator('.outputs-browser').getAttribute('data-snapshot-id');
const reviewedDownload=page.waitForEvent('download');await outputs.getByRole('button',{name:'Download reviewed ZIP',exact:true}).click();
await(await reviewedDownload).saveAs(`${out}/reviewed.zip`);
const reviewedZip=unzipSync(fs.readFileSync(`${out}/reviewed.zip`));
assert.equal(JSON.parse(strFromU8(reviewedZip['manifest.json'])).snapshotId,reviewedSnapshot);
await page.screenshot({path:`${out}/outputs-directory.png`,fullPage:true});
await page.setViewportSize({width:390,height:844});
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,right:el.getBoundingClientRect().right})))));
await page.setViewportSize({width:1440,height:1000});

await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Terraform',exact:true}).click();
const tf=page.getByRole('region',{name:'Terraform',exact:true});
await tf.getByRole('heading',{name:'Resource coverage'}).waitFor();assert.match(await tf.innerText(),/Implementation needed/);
assert.match(await tf.getByLabel('main.tf.json',{exact:true}).innerText(),/aws_s3_bucket/);
await tf.getByRole('button',{name:'Continue to Test Terraform →',exact:true}).click();
await tf.getByRole('button',{name:'Run Terraform checks',exact:true}).click();
await tf.getByRole('heading',{name:'Configuration validated',exact:true}).waitFor();
assert.match(await tf.innerText(),/Incomplete/);
assert.equal(await tf.getByRole('button',{name:'Run cloud plan (under development)',exact:true}).isDisabled(),true);
await page.screenshot({path:`${out}/terraform-tests.png`,fullPage:true});
await tf.getByRole('button',{name:'Run Terraform checks',exact:true}).click();
await tf.getByRole('heading',{name:'Terraform validation not run',exact:true}).waitFor();
assert.equal(await tf.getByRole('heading',{name:'Configuration validated',exact:true}).count(),0);

// Change an entered charge and regenerate: outputs follow the project, not an edited document.
await tab('Estimate');await est.getByLabel('Detailed cloud charges').locator('summary').click(); // view remounts collapsed
await est.getByLabel('Charge 1 monthly quantity',{exact:true}).fill('200');
await delivery();dl=page.waitForEvent('download');await page.getByRole('button',{name:'Download delivery pack',exact:true}).click();file=await dl;await file.saveAs(`${out}/pack-revised.zip`);
const revised=unzipSync(fs.readFileSync(`${out}/pack-revised.zip`));assert.equal(JSON.parse(strFromU8(revised['estimate.json'])).cloud.expected,13.6);assert.notEqual(JSON.parse(strFromU8(revised['manifest.json'])).snapshotId,manifest.snapshotId);
await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Outputs',exact:true}).click();
await outputs.getByRole('heading',{name:'Implementation Spec Kit',exact:true}).waitFor();
assert.notEqual(await outputs.locator('.outputs-browser').getAttribute('data-snapshot-id'),reviewedSnapshot);
await outputs.getByRole('navigation',{name:'Output files'}).getByRole('button',{name:'estimate.json',exact:true}).click();
assert.equal(JSON.parse(await outputs.locator('.output-code').innerText()).cloud.expected,13.6);
await outputs.getByRole('button',{name:'Back to architecture',exact:true}).click();

// Undo/redo and a branching edit: redo cannot reapply a discarded branch.
await tab('Design');const count=(await state()).nodes.length;
await page.getByRole('button',{name:'Clear board',exact:true}).click();assert.equal((await state()).nodes.length,0);
await page.getByRole('button',{name:'Undo',exact:true}).click();assert.equal((await state()).nodes.length,count);
await page.getByRole('button',{name:'Redo',exact:true}).click();assert.equal((await state()).nodes.length,0);
await page.getByRole('button',{name:'Undo',exact:true}).click();await page.getByRole('button',{name:'Auto-arrange',exact:true}).click();assert.equal(await page.getByRole('button',{name:'Redo',exact:true}).isDisabled(),true);
// Start-over is cancellable and offers a downloadable copy; the new engagement has no old costs.
await page.getByRole('button',{name:'Start over',exact:true}).click();await page.getByRole('button',{name:'Keep working',exact:true}).click();assert.equal((await state()).nodes.length,count);
await page.getByRole('button',{name:'Start over',exact:true}).click();dl=page.waitForEvent('download');await page.getByRole('button',{name:'Save project and start over',exact:true}).click();file=await dl;await file.saveAs(`${out}/before-reset.atforma.json`);
assert.equal(JSON.parse(fs.readFileSync(`${out}/before-reset.atforma.json`)).estimate.details.length,5);assert.equal((await state()).nodes.length,0);assert.equal((await state()).estimate,undefined);assert.equal(await page.getByRole('button',{name:'Undo',exact:true}).isDisabled(),true);assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-connection-v1')).provider),'claude-code');
await page.locator('#project-file-input').setInputFiles(`${out}/before-reset.atforma.json`);await page.getByText('Project opened.',{exact:true}).waitFor();assert.equal((await state()).estimate.details.length,5);
await page.setViewportSize({width:390,height:844});await tab('Estimate');await est.getByLabel('Detailed cloud charges').locator('summary').click();await page.screenshot({path:`${out}/estimate-mobile.png`,fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,right:el.getBoundingClientRect().right})))));
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);await browser.close();
console.log('Delivery scenarios passed: ROM → detailed charges, mixed currencies, consulting effort, AWS inventory, ZIP contents, regenerate after edit, undo/redo/branch, cancel/reset/save/reopen, mobile, no external requests. Synthetic prices and provider session only.');

} finally { await browser?.close();server?.kill('SIGTERM'); }
