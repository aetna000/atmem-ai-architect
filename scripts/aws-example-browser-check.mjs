// Isolated UI import tests. No real model, cloud or user browser is used.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import {chromium} from '@playwright/test';
import {parseProjectFile} from '../src/project-file.mjs';
import {verifyExamples} from './aws-example-check.mjs';
const root=path.resolve(import.meta.dirname,'..'),manifest=verifyExamples();
const out=path.join(root,'.local/example-browser',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(out,{recursive:true});
const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:root,stdio:'ignore'});
let browser;const results=[];let failure;
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}if(i===99)throw Error('Test UI did not start');await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});
 for(const example of manifest.scenarios){
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),errors=[];
  page.setDefaultTimeout(15000);
  await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'default'})));
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/**',r=>{
   const url=new URL(r.request().url());
   if(url.pathname==='/api/session')return r.fulfill({json:{token:'example-test',status:'local-sidecar',providers:{'claude-code':{installed:true,available:true,signedIn:true}}}});
   if(url.pathname==='/api/architect')return r.fulfill({json:{message:'Import test: no model call.',proposal:null}});
   return r.fulfill({json:{projects:[],bin:[],saved:true,status:'disabled',models:[]}});
  });
  await page.goto(base);
  const filename=path.join(root,'examples/aws',example.project),expected=parseProjectFile(fs.readFileSync(filename,'utf8')).project;
  await page.getByRole('button',{name:'More',exact:true}).click();
  const chooser=page.waitForEvent('filechooser');await page.getByRole('menuitem',{name:'Open project file',exact:true}).click();await (await chooser).setFiles(filename);
  await page.getByText('Project opened.',{exact:true}).waitFor();
  await page.waitForFunction(count=>document.querySelectorAll('.react-flow__node').length===count,expected.nodes.length);
  const actual=await page.evaluate(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')));
  assert.deepEqual(actual.nodes.map(n=>({id:n.id,data:n.data})),expected.nodes.map(n=>({id:n.id,data:n.data})));
  assert.deepEqual(actual.edges,expected.edges);assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(out,example.id+'.png'),fullPage:true});
  results.push({id:example.id,status:'passed',nodes:actual.nodes.length,edges:actual.edges.length,checks:['menu-file-import','canvas-render','node-contract-preservation','edge-contract-preservation','no-page-errors']});
  await context.close();console.log(example.id+': import/render passed');
 }
}catch(error){failure=error.message.replaceAll(root,'<repository>');throw error;}finally{
 await browser?.close();server.kill('SIGTERM');
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({kind:'isolated-browser-import',status:failure?'failed':results.length===7?'passed':'incomplete',...(failure?{error:failure}:{}),cloudOperations:false,realModelCalls:false,results},null,2)+'\n');
 console.log('Evidence: '+out);
}
