// Actual installed candidate HTTP/browser checks. No transport fixtures or inference.
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {fromProjectFile} from '../src/project-file.mjs';
import {chromium} from '@playwright/test';import {unzipSync,strFromU8} from 'fflate';
const base=process.env.ATMEM_CANDIDATE_URL||'http://127.0.0.1:5285';
const out=process.env.ATMEM_CANDIDATE_EVIDENCE;
const bulk=process.env.ATMEM_CANDIDATE_BULK;
assert(out&&bulk,'Choose fresh evidence and bulk artifact directories.');
assert(!fs.existsSync(out)&&!fs.existsSync(bulk),'Preserve previous evidence.');
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(bulk,{recursive:true});
const source='specs/029-general-purpose-engine/evidence/20261111-public-composition/composition-example.atmem-ai-architect.json';
const browser=await chromium.launch({headless:true});let page,submissions=0;
const errors=[],responses=[];
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}});page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(create|start|steer)$/.test(r.url()))submissions++;});
 page.on('response',async r=>{if(r.url().endsWith('/api/terraform/validate'))responses.push(await r.json());});
 // Exact user selection is local configuration, not a mocked service response.
 await page.addInitScript(()=>{if(!localStorage.getItem('atforma-connection-v1'))localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));});
 await page.goto(base);await page.locator('.react-flow').waitFor();
 assert.equal(await page.getByRole('tab',{name:'Design',exact:true}).getAttribute('aria-selected'),'true');
 await page.getByTitle('About AtMem AI Architect').click();await page.getByText('0.2.0-alpha.3',{exact:false}).first().waitFor();await page.getByRole('button',{name:'Close dialog',exact:true}).last().click();
 await page.locator('#project-file-input').setInputFiles(source);await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Terraform',exact:true}).click();
 const view=page.getByRole('region',{name:'Terraform',exact:true});await view.getByRole('button',{name:'Continue to Test Terraform →',exact:true}).click();
 await view.getByRole('button',{name:'Run Terraform checks',exact:true}).click();
 await view.getByRole('heading',{name:'Configuration validated',exact:true}).waitFor({timeout:180000});
 assert.equal(responses.length,1);const report=responses[0];assert.equal(report.status,'passed');
 const tests=report.checks.filter(c=>c.stage==='test');assert.equal(tests.length,2);assert(tests.every(c=>c.passed&&c.testsReported>0));
 fs.writeFileSync(path.join(out,'actual-http-validation.json'),JSON.stringify(report,null,2)+'\n');
 const downloading=page.waitForEvent('download');await view.getByRole('button',{name:'Download Terraform',exact:true}).click();const dl=await downloading,target=path.join(bulk,'validated-terraform.zip');await dl.saveAs(target);
 const files=Object.fromEntries(Object.entries(unzipSync(fs.readFileSync(target))).map(([n,b])=>[n,strFromU8(b)]));const receipt=JSON.parse(files['validation-receipt.json']);
 assert.equal(receipt.status,'passed');assert.equal(receipt.cloudPlan,'not_run');assert.equal(receipt.deployment,'not_run');
 for(const [n,digest]of Object.entries(report.fileDigests)){assert(Object.hasOwn(files,n),n);assert.equal(createHash('sha256').update(files[n]).digest('hex'),digest,n);}
 await page.screenshot({path:path.join(bulk,'desktop.png')});await page.setViewportSize({width:390,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(bulk,'mobile.png')});
 await page.reload();await page.locator('.react-flow').waitFor();assert.equal(await page.getByRole('tab',{name:'Design',exact:true}).getAttribute('aria-selected'),'true');
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));assert.equal(saved.nodes.length,4);assert.equal(saved.requirements,fromProjectFile(JSON.parse(fs.readFileSync(source))).project.requirements);
 assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-connection-v1'))),{provider:'codex',model:'gpt-6.1-sol',effort:'high'});
 assert.equal(submissions,0);assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({passed:true,base,version:'0.2.0-alpha.3',actualHttp:true,transportFixtures:false,unitMockRuns:tests.reduce((n,c)=>n+c.testsReported,0),modules:tests.map(c=>({id:c.moduleId,path:c.modulePath,tests:c.testsReported})),downloadSha256:createHash('sha256').update(fs.readFileSync(target)).digest('hex'),checkedFileCount:Object.keys(report.fileDigests).length,submissions,errors,bulkArtifacts:bulk,boundary:'Actual installed candidate HTTP service/native Terraform init/schema/unit mocks and digest-matched browser download/reload. No inference, supplied-image runtime, account plan or deployment.'},null,2)+'\n');
 console.log('Installed candidate actual HTTP, native Terraform, download identity and browser continuity passed.');
}catch(e){if(page){fs.writeFileSync(path.join(out,'failure.txt'),await page.locator('body').innerText());await page.screenshot({path:path.join(bulk,'failure.png'),fullPage:true});}throw e;}finally{await browser.close();}
