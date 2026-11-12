// Real controls, synthetic check transports; proves action separation without executing cloud tools.
import{chromium}from'@playwright/test';import assert from'node:assert/strict';import fs from'node:fs';import{spawn}from'node:child_process';import{createServer}from'node:net';
const out='.local/project-checks-smoke';fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(out+'/index.html','<html><body><div id="root"></div><script type="module" src="/'+out+'/harness.jsx"></script></body></html>');
fs.writeFileSync(out+'/harness.jsx',`import React from'react';import{createRoot}from'react-dom/client';import{ProjectChecks}from'../../src/ProjectChecks.jsx';import{validateImport}from'../../src/core.mjs';import'../../src/atmem-tokens.css';import'../../src/atflow.css';import'../../src/journey-workspace.css';const p=validateImport({id:'check-actions-test',version:1,revision:1,name:'Synthetic checks',provider:'aws',requirements:'',nodes:[],edges:[]});createRoot(document.getElementById('root')).render(<ProjectChecks project={p} environment="staging" session={{token:'fixture',engineeringEnabled:true}}/>);`);
const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));const base=`http://127.0.0.1:${port}`,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:800}});let generated=false,terraform=0,application=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;
  if(path.endsWith('/terraform/validate')){terraform++;return route.fulfill({json:{status:'incomplete',message:'Synthetic Terraform result',checks:[]}})}
  if(path.endsWith('/delivery'))return route.fulfill({json:generated?{artifact:{id:'one'},session:{id:'session'}}:{artifact:null}});
  if(path.endsWith('/validators'))return route.fulfill({json:{validators:[{id:'node',label:'Node tests',contractSha256:'a'.repeat(64),available:true}]}});
  if(path.endsWith('/validation/start')){application++;return route.fulfill({json:{}})}
  if(path.endsWith('/validation/list'))return route.fulfill({json:{checks:application?[{id:'check',validatorId:'node',contractSha256:'a'.repeat(64),label:'Node tests',state:'finished',result:{status:'passed'}}]:[]}});
  return route.fulfill({json:{}});
 });
 await page.goto(base+'/'+out+'/index.html');const app=page.getByRole('button',{name:'Run application tests',exact:true});await app.waitFor();assert.equal(await app.isDisabled(),true);assert.equal(await app.getAttribute('title'),'Generate project files first.');await page.locator('.check-run-action[title="Generate project files first."]').hover();
 await page.getByRole('button',{name:'Run Terraform validation',exact:true}).click();await page.getByText('Incomplete',{exact:true}).waitFor();assert.equal(terraform,1);assert.equal(application,0);
 generated=true;await page.reload();await page.waitForFunction(()=>!document.querySelector('button[aria-label="Run application tests"]').disabled);
 await app.click();await page.getByText('Passed',{exact:true}).first().waitFor();assert.equal(application,1);assert.equal(terraform,1);assert.deepEqual(errors,[]);
 await page.screenshot({path:out+'/checks.png'});console.log('Separate Terraform/application Run buttons, generation prerequisite tooltip and isolated requests passed.');
}finally{await browser?.close();server.kill('SIGTERM')}
