// Real emulation HTTP endpoint + real generated code, in an isolated test browser.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {createHash} from 'node:crypto';
import {unzipSync} from 'fflate';
import {chromium} from '@playwright/test';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'.local/emulation-browser',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(out,{recursive:true});
async function port(){const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const p=server.address().port;await new Promise(r=>server.close(r));return p;}
const ui=await port(),api=await port(),base=`http://127.0.0.1:${ui}`;
const env={PATH:process.env.PATH,HOME:out,ATMEM_ARCHITECT_HOME:path.join(out,'home'),ATMEM_ARCHITECT_PORT:String(ui),ATMEM_ARCHITECT_SIDECAR_PORT:String(api)};
const log=fs.openSync(path.join(out,'services.log'),'a');const children=[];let browser;const results=[];
function start(bin,args){children.push(spawn(bin,args,{cwd:root,env,stdio:['ignore',log,log]}));}
try{
 start(path.join(root,'.venv/bin/python'),['-m','uvicorn','server.app:app','--host','127.0.0.1','--port',String(api),'--no-access-log']);
 start(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(ui),'--strictPort']);
 for(const url of [base,`http://127.0.0.1:${api}/api/session`])for(let i=0;i<200;i++){try{if((await fetch(url)).ok)break;}catch{}if(i===199)throw Error('Service failed to start');await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'default'})));
 await page.route('**/api/architect',r=>r.fulfill({json:{message:'UI test: no model call.',proposal:null}}));
 await page.route('**/api/memory/**',r=>r.fulfill({json:{status:'disabled'}}));
 await page.goto(base);
 const scenario='07-enterprise-connectors';await page.locator('input[type=file]').setInputFiles(path.join(root,'examples/aws',scenario,'project.atmem-ai-architect.json'));
 await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Outputs',exact:true}).click();
 const panel=page.getByRole('complementary',{name:'AWS emulation'});await panel.getByRole('button',{name:'Emulate locally',exact:true}).click();
 await panel.getByRole('heading',{name:'Local emulation checks passed',exact:true}).waitFor({timeout:115000});
 assert.match(await panel.innerText(),/IAM enforcement/);assert.match(await panel.innerText(),/not.*model-quality/);
 const download=page.waitForEvent('download');await panel.getByRole('button',{name:'Download emulation report'}).click();const file=await download;await file.saveAs(path.join(out,'report.json'));
 const report=JSON.parse(fs.readFileSync(path.join(out,'report.json'),'utf8'));assert.equal(report.backend,'moto');assert.equal(report.status,'passed');assert.equal(report.cloudOperations,false);assert.ok(report.emulatorPatches.length);assert.ok(report.fileDigests['main.tf.json']);
 const zipDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download reviewed ZIP',exact:true}).click();await (await zipDownload).saveAs(path.join(out,'delivery.zip'));
 const exported=unzipSync(fs.readFileSync(path.join(out,'delivery.zip')));
 for(const [name,digest] of Object.entries(report.fileDigests)){assert.ok(exported['terraform/'+name],name);assert.equal(createHash('sha256').update(exported['terraform/'+name]).digest('hex'),digest,name);}
 results.push('Emulation report hashes match every Terraform/runtime file in the downloaded delivery ZIP');
 await page.screenshot({path:path.join(out,'emulation.png'),fullPage:true});results.push('Real API emulates emitted connector/RAG code before ZIP download');results.push('Downloadable report includes artifact hashes and unverified boundaries');
 // A different project must not inherit an old emulation pass.
 await page.getByRole('button',{name:'More',exact:true}).click();const chooser=page.waitForEvent('filechooser');await page.getByRole('menuitem',{name:'Open project file',exact:true}).click();await (await chooser).setFiles(path.join(root,'examples/aws/02-document-compute/project.atmem-ai-architect.json'));
 await page.getByRole('region',{name:'Architecture journey'}).getByRole('button',{name:'Outputs',exact:true}).click();
 assert.equal(await page.getByRole('heading',{name:'Local emulation checks passed',exact:true}).count(),0);results.push('Changing the project clears old results');assert.deepEqual(errors,[]);
 console.log(JSON.stringify({status:'passed',checks:results,evidence:out}));
}finally{await browser?.close();for(const child of children)child.kill('SIGTERM');fs.closeSync(log);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({checks:results,cloudOperations:false},null,2)+'\n');}
