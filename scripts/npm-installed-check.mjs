// Run from the repository against a clean npm prefix; no model inference or cloud calls.
import {execFileSync,spawn,spawnSync} from 'node:child_process';
import {createServer} from 'node:net';
import path from 'node:path';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';
const [prefixArg,homeArg]=process.argv.slice(2);if(!prefixArg||!homeArg)throw Error('Usage: npm-installed-check.mjs PREFIX DATA_HOME');
const prefix=path.resolve(prefixArg),home=path.resolve(homeArg),cli=path.join(prefix,'node_modules/@atmem/architect/cli/architect.mjs');assert.ok(fs.existsSync(cli));
const manifest=JSON.parse(fs.readFileSync(path.join(prefix,'node_modules/@atmem/architect/package.json')));
const bin=path.join(prefix,'node_modules/.bin/atmemai');
assert.equal(manifest.bin.atmemai,manifest.bin['atmem-architect']);
assert.ok(fs.existsSync(bin+(process.platform==='win32'?'.cmd':'')));
const launcher=process.platform==='win32'?process.execPath:bin;
const launcherArgs=process.platform==='win32'?[cli]:[];
const command=(args,options={})=>execFileSync(launcher,[...launcherArgs,...args,'--data-dir',home],{encoding:'utf8',...options});
assert.equal(command(['--version']).trim(),manifest.version);
const status=()=>JSON.parse(command(['status','--json']));
assert.equal(status().server.state,'stopped');
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
let browser,child;const logs=[];
try{
 child=spawn(launcher,[...launcherArgs,'--no-open','--port',String(port),'--data-dir',home],{stdio:['ignore','pipe','pipe'],windowsHide:true});child.stdout.on('data',data=>{logs.push(data.toString());process.stdout.write(data);});child.stderr.on('data',data=>{logs.push(data.toString());process.stderr.write(data);});
 const base=`http://127.0.0.1:${port}`;let session;
 for(let i=0;i<900;i++){if(child.exitCode!==null)throw Error('Installed launcher exited: '+logs.join('').slice(-2000));try{const response=await fetch(base+'/api/session');if(response.ok){session=await response.json();break;}}catch{}await new Promise(r=>setTimeout(r,1000));}
 assert.ok(session?.token,'installed app becomes ready');
 let running;
 for(let i=0;i<20;i++){
   running=status();
   if(running.server.state==='running')break;
   await new Promise(resolve=>setTimeout(resolve,250));
 }
 assert.equal(running.server.state,'running');
 assert.equal(running.server.url,base);
 assert.equal(running.paths.memoryDatabase,path.join(home,'memory','memories.db'));
 const duplicate=spawnSync(launcher,[...launcherArgs,'--no-open','--data-dir',home],{encoding:'utf8',stdio:['ignore','pipe','pipe']});
 assert.equal(duplicate.status,1);
 assert.match(duplicate.stderr,/requires confirmation/);
 assert.equal(status().server.pid,running.server.pid);

 const response=await fetch(base+'/api/memory/inspect',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:'npm-clean-install-test'})});const memory=await response.json();assert.equal(response.status,200);assert.notEqual(memory.status,'unavailable');assert.equal(memory.enabled,true);assert.match(memory.engine,/AtMem/i);
 browser=await chromium.launch({headless:true});const page=await browser.newPage();const errors=[],failures=[],modelCalls=[];page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>failures.push(r.url()));page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(create|start|steer)$/.test(r.url()))modelCalls.push(r.url());});
 await page.goto(base,{waitUntil:'networkidle',timeout:60000});await page.locator('.drawing-journey-menu>summary').click();assert.equal(await page.getByRole('tablist',{name:'Project stages'}).getByRole('tab').count(),5);await page.locator('.drawing-journey-menu>summary').click();await page.getByLabel('Architecture board',{exact:true}).waitFor();assert.equal(await page.locator('.drawio-canvas').count(),1);assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);assert.deepEqual(modelCalls,[]);
 await page.getByRole('button',{name:'Explore runnable AI example',exact:true}).click();
 await page.getByRole('button',{name:'Download example ZIP',exact:true}).waitFor();
 if(!await page.getByRole('tab',{name:'Delivery',exact:true}).isVisible())await page.locator('.drawing-journey-menu>summary').click();
 await page.getByRole('tab',{name:'Delivery',exact:true}).click();
 await page.locator('summary').filter({hasText:/^Bundled runtime evidence$/}).click();
 assert.equal(await page.locator('.ready-reference .check-complete').count(),8);
 const [reference]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download runnable example',exact:true}).click()]);
 const referenceReceipt=JSON.parse(fs.readFileSync(path.join(prefix,'node_modules/@atmem/architect/src/reference-example/receipt.json')));
 assert.equal(createHash('sha256').update(fs.readFileSync(await reference.path())).digest('hex'),referenceReceipt.sha256);
 assert.deepEqual(errors,[]);assert.deepEqual(modelCalls,[]);
 const savedFile=path.join(home,'installer-preservation-check.txt');fs.writeFileSync(savedFile,'preserve me');
 console.log(JSON.stringify({installedPrefix:prefix,platform:process.platform,arch:process.arch,version:JSON.parse(fs.readFileSync(path.join(prefix,'node_modules/@atmem/architect/package.json'))).version,memoryEngine:memory.engine,uiStages:5,errors,modelCalls}));
}finally{await browser?.close();if(child&&child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),new Promise(r=>setTimeout(r,10000))]);}}
