// Evaluation adapter: unchanged packaged UI, deliberately stalled configuration.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
const extracted=fs.mkdtempSync('/tmp/atmem-startup-oracle-');
execFileSync('/usr/bin/python3',['-c',`import pathlib,sys,zipfile
with zipfile.ZipFile('/work/source/dist/function.zip') as z:
 assert all(not pathlib.PurePosixPath(i.filename).is_absolute() and '..' not in pathlib.PurePosixPath(i.filename).parts for i in z.infolist())
 z.extractall(sys.argv[1])`,extracted]);
let release,configurationRequested,authorizationReached=false;
const pending=new Promise(resolve=>release=resolve),requested=new Promise(resolve=>configurationRequested=resolve);
const server=http.createServer(async(req,res)=>{
 const pathname=new URL(req.url,'http://fixture').pathname;
 if(pathname==='/config.json'){
  configurationRequested();await pending;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({clientId:'startupclient',authOrigin:'https://independent.auth.ap-southeast-2.amazoncognito.com'}));return;
 }
 const file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[pathname];
 if(!file){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',pathname.endsWith('.js')?'text/javascript':pathname.endsWith('.css')?'text/css':'text/html');
 res.end(fs.readFileSync(path.join(extracted,'app/web',file)));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,chromiumSandbox:true}),page=await browser.newPage();
try{
 await page.route('https://independent.auth.ap-southeast-2.amazoncognito.com/**',async route=>{
  const url=new URL(route.request().url());assert.equal(url.pathname,'/oauth2/authorize');assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('client_id'),'startupclient');authorizationReached=true;await route.fulfill({body:'Synthetic OAuth endpoint reached'});
 });
 await page.goto(`http://127.0.0.1:${server.address().port}/`,{waitUntil:'domcontentloaded'});await requested;
 const login=page.locator('#login');await login.waitFor({state:'visible'});
 const initiallyDisabled=await login.isDisabled();
 if(!initiallyDisabled)await login.click();
 release();
 if(initiallyDisabled){await login.waitFor({state:'visible'});await page.waitForFunction(()=>!document.querySelector('#login').disabled);await login.click();}
 await page.waitForFunction(()=>location.hostname==='independent.auth.ap-southeast-2.amazoncognito.com',null,{timeout:5000}).catch(()=>{});
 const status=await page.evaluate(()=>document.querySelector('#status')?.textContent??null);
 assert(authorizationReached,JSON.stringify({failure:'Action ran before asynchronous configuration was ready; immediate user intent did not reach sign-in after configuration resolved',initiallyDisabled,status}));
 console.log('INDEPENDENT_STARTUP_PREREQUISITE_PASSED');
}finally{
 release();await browser.close();await new Promise(resolve=>server.close(resolve));fs.rmSync(extracted,{recursive:true,force:true});
}
