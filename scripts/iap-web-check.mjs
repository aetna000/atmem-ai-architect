// Browser transport/security fixture; not a real IAP session or Google model test.
import http from 'node:http';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {gcpStructuredProject} from '../tests/fixtures/gcp-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
const p=gcpStructuredProject();p.nodes[1].data.config.outputContract.fields.push({name:'summary',type:'string',description:'Summary',maxLength:1000});
const files=terraformSketch(p),prefix=Object.keys(files).find(k=>k.endsWith('/web/index.html')).replace('index.html','');
const fields=p.nodes[1].data.config.outputContract.fields;
let calls=0,mode='valid',release=null,captured;
const server=http.createServer(async(req,res)=>{
 if(req.url==='/config.json'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({maxInputBytes:20000,requestDeadlineMs:28000,fieldsBase64:Buffer.from(JSON.stringify(fields)).toString('base64')}));}
 if(req.url==='/api/ask'){
  let body='';for await(const chunk of req)body+=chunk;calls++;captured={headers:req.headers,body:JSON.parse(body)};
  if(mode==='held')await new Promise(resolve=>{release=resolve;});
  res.setHeader('Content-Type','application/json');
  if(mode==='denied'){res.statusCode=401;return res.end('{"error":"access_denied"}');}
  return res.end(JSON.stringify({result:{topic:'other',uncertain:true,summary:'<img src=x onerror="window.injected=true">'},requiresHumanReview:true}));
 }
 const name={'/':'index.html','/app.js':'app.js','/app.css':'app.css'}[req.url];
 if(!name){res.statusCode=404;return res.end();}
 res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html');res.end(files[prefix+name]);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true,...(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{})});
const checks=[];
try{
 const page=await browser.newPage();await page.goto(origin);await page.waitForFunction(()=>!document.getElementById('question').disabled);
 await page.locator('#question').fill('Synthetic ticket');await page.locator('#submit').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Result prepared'));
 assert.equal(captured.body.text,'Synthetic ticket');assert.equal(captured.headers.origin,origin);assert.equal(captured.headers.authorization,undefined);assert.equal(captured.headers['x-goog-iap-jwt-assertion'],undefined);
 assert.match(await page.locator('#answer').textContent(),/<img src=x/);assert.equal(await page.locator('#answer img').count(),0);assert.equal(await page.evaluate(()=>window.injected),undefined);
 checks.push('Same-origin JSON submission carries no browser-forged IAP identity; output stays text.');
 const before=calls;await page.locator('#question').fill('é'.repeat(10001));await page.locator('#submit').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('UTF-8 bytes'));assert.equal(calls,before);
 checks.push('UTF-8 byte limit blocks oversize input before network submission.');
 // Deliberately ineffective fetch cancellation: the epoch must also suppress late output.
 await page.addInitScript(()=>{const fetchOriginal=window.fetch;window.fetch=(input,options)=>String(input).includes('/api/ask')?fetchOriginal(input,{...options,signal:undefined}):fetchOriginal(input,options);});
 await page.reload();await page.waitForFunction(()=>!document.getElementById('question').disabled);mode='held';
 await page.locator('#question').fill('Synthetic late input');await page.locator('#submit').click();
 for(let i=0;i<100&&!release;i++)await new Promise(resolve=>setTimeout(resolve,10));assert.ok(release);
 await page.locator('#clear').click();const late=page.waitForResponse(response=>response.url().endsWith('/api/ask'));release();await (await late).finished();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(await page.locator('#answer').textContent(),'');assert.equal(await page.locator('#question').inputValue(),'');
 checks.push('Clear removes private input/output and suppresses late output even without transport cancellation.');
 mode='denied';await page.locator('#question').fill('Synthetic expired session');await page.locator('#submit').click();await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Reopen this workspace'));
 assert.equal(await page.locator('#question').inputValue(),'');assert.equal(await page.locator('#question').isDisabled(),true);
 checks.push('Denied identity clears private data and requires reopening the protected session.');
 console.log(JSON.stringify({passed:true,checks,cloudOperations:false,boundary:'Exact emitted browser assets, local HTTP fixture acting after IAP; no live Google authentication, authorization or model proof.'},null,2));
}finally{if(release)release();await browser.close();server.closeAllConnections();server.close();}
