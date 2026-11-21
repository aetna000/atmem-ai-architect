
import assert from 'node:assert/strict';
import {createApp} from '/work/source/server.mjs';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
const checks=[],slow=new Map();
async function check(name,fn){await fn();checks.push(name);}
const server=createApp({previewNote:async note=>{
 if(note==='oracle-failure')throw Error('SYNTHETIC-PRIVATE-DIAGNOSTIC');
 if(note.startsWith('oracle-slow-'))await new Promise(resolve=>slow.set(note,resolve));
 return note;
}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
async function request(body,headers={'Content-Type':'application/json'},route='/api/preview',method='POST'){
 const r=await fetch(origin+route,{method,headers,...(body===undefined?{}:{body})});return {status:r.status,body:await r.text(),cache:r.headers.get('cache-control')};
}
let browser;
try{
 await check('HTTP default preview preserves exact input and no-store',async()=>{const note='  Synthetic handover\nNext shift  ';const r=await request(JSON.stringify({note}));assert.equal(r.status,200);assert.deepEqual(JSON.parse(r.body),{preview:note});assert.equal(r.cache,'no-store');});
 for(const [label,body] of [['malformed','{'],['null','null'],['array','[]'],['missing','{}'],['wrong-type','{"note":3}'],['extra','{"note":"a","extra":true}'],['blank','{"note":"  "}'],['oversize',JSON.stringify({note:'x'.repeat(2001)})]])await check('HTTP reject '+label,async()=>assert.equal((await request(body)).status,400));
 await check('Declared 2000 UTF-16-unit boundary, ASCII and supplementary Unicode',async()=>{for(const note of ['x'.repeat(2000),'😀'.repeat(1000)]){const r=await request(JSON.stringify({note}));assert.equal(r.status,200);assert.deepEqual(JSON.parse(r.body),{preview:note});}});
 await check('Content-type, method and unknown action denial',async()=>{assert.equal((await request('{"note":"x"}',{'Content-Type':'text/plain'})).status,415);assert.equal((await request(undefined,{},'/api/preview','GET')).status,405);assert.equal((await request('{"note":"x"}',undefined,'/publish')).status,404);});
 await check('Server failure is safe and next request recovers',async()=>{const bad=await request('{"note":"oracle-failure"}');assert.equal(bad.status,500);assert(!bad.body.includes('SYNTHETIC-PRIVATE'));assert.equal((await request('{"note":"recovered"}')).status,200);});
 await check('Five parallel request values remain isolated',async()=>{await Promise.all(Array.from({length:5},async(_,i)=>{const note='parallel-'+i;const r=await request(JSON.stringify({note}));assert.deepEqual(JSON.parse(r.body),{preview:note});}));});
 browser=await chromium.launch({headless:true,chromiumSandbox:true});const context=await browser.newContext();const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(origin);
 async function submit(note){await page.locator('#note').fill(note);await page.locator('#submit').click();}
 async function ready(note){await page.waitForFunction(value=>document.querySelector('#preview').textContent===value&&!document.querySelector('#preview').hidden,note,{timeout:4000});}
 await check('Actual browser normal request and safe text rendering',async()=>{const note='<img src=x onerror="window.__oracleXss=1"> synthetic';await submit(note);await ready(note);assert.equal(await page.locator('#preview img').count(),0);assert.equal(await page.evaluate(()=>window.__oracleXss),undefined);});
 await check('Actual browser clear erases input and preview',async()=>{await page.locator('#clear').click();assert.equal(await page.locator('#note').inputValue(),'');assert.equal(await page.locator('#preview').textContent(),'');assert(await page.locator('#preview').isHidden());});
 await check('Actual browser empty input rejection and recovery',async()=>{await submit(' ');await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Enter a note'));await submit('valid after rejection');await ready('valid after rejection');});
 await check('Actual browser server failure then successful retry',async()=>{await submit('oracle-failure');await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Could not prepare'));assert(await page.locator('#preview').isHidden());assert(!(await page.locator('body').innerText()).includes('SYNTHETIC-PRIVATE'));await submit('browser recovered');await ready('browser recovered');});
 await check('No browser persistence and reload erases entered/displayed values',async()=>{assert.equal(await page.evaluate(()=>localStorage.length),0);assert.equal(await page.evaluate(()=>sessionStorage.length),0);assert.equal((await context.cookies()).length,0);await page.reload();assert.equal(await page.locator('#note').inputValue(),'');assert.equal(await page.locator('#preview').textContent(),'');});
 await context.close();
 for(const ignoreAbort of [false,true])await check('Actual late HTTP result cannot undo clear; ignored cancellation='+ignoreAbort,async()=>{
  const c=await browser.newContext();
  if(ignoreAbort)await c.addInitScript(()=>{const original=window.fetch.bind(window);window.fetch=(url,options)=>original(url,{...options,signal:undefined});});
  const p=await c.newPage();await p.goto(origin);const note='oracle-slow-'+ignoreAbort;await p.locator('#note').fill(note);await p.locator('#submit').click();
  for(let i=0;i<60&&!slow.has(note);i++)await new Promise(resolve=>setTimeout(resolve,25));assert(slow.has(note),'Real server must receive the delayed request before clear');
  await p.locator('#clear').click();const response=ignoreAbort?p.waitForResponse(r=>r.url()===origin+'/api/preview'&&r.request().method()==='POST',{timeout:4000}):null;slow.get(note)();slow.delete(note);if(response)await(await response).finished();await p.waitForTimeout(200);
  assert.equal(await p.locator('#note').inputValue(),'');assert.equal(await p.locator('#preview').textContent(),'');assert(await p.locator('#preview').isHidden());
  await p.locator('#note').fill('after clear');await p.locator('#submit').click();await p.waitForFunction(()=>document.querySelector('#preview').textContent==='after clear');await c.close();
 });
 assert.deepEqual(errors,[]);console.log('INDEPENDENT_NOTE_PREVIEW_PASSED');console.log(JSON.stringify({checks,checkCount:checks.length,browserVersion:browser.version(),node:process.version,boundary:'Actual unchanged HTTP service/static assets in Chromium; only preview dependency timing/failure and one browser transport ignoring cancellation are explicit test fixtures. No generated tests or emitted source were modified or used as the oracle. Not an architecture holdout, hosted isolation, cloud integration or 28-case acceptance.'}));
}finally{if(browser)await browser.close();for(const resolve of slow.values())resolve();await new Promise(resolve=>server.close(resolve));server.closeAllConnections();}
