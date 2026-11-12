// Browser-to-unchanged-image journeys; native cloud transports are synthetic.
import fs from 'node:fs';import assert from 'node:assert/strict';
import {chromium}from '/opt/atmem/playwright-core/index.mjs';
const inputs=JSON.parse(fs.readFileSync(0,'utf8')),base=inputs.origin,control='http://app.test:9090',checks=[],contexts=[],errors=[];
const browser=await chromium.launch({headless:true,chromiumSandbox:true});
async function mode(value='good',identity='good'){const r=await fetch(control+'/mode',{method:'POST',body:JSON.stringify({mode:value,identity})});assert(r.ok);}
async function state(){return(await fetch(control+'/state')).json();}
async function signedPage(oid=inputs.reviewers[0],expected=true){
 const context=await browser.newContext({ignoreHTTPSErrors:true});contexts.push(context);const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 page.on('requestfailed',request=>console.error(JSON.stringify({failedUrl:request.url().split('?')[0],error:request.failure()?.errorText})));
 const selected=await fetch(control+'/next-user',{method:'POST',body:JSON.stringify({oid})});assert(selected.ok);
 await page.goto(base);await page.locator('#login').waitFor({state:'visible'});await page.locator('#login').click();await page.locator('#fixture-consent').click();
 if(expected)await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Ready.'));
 else{
  try{await page.waitForURL(url=>url.pathname==='/auth/callback');}
  catch(error){console.error(JSON.stringify({stage:'denied-login',url:page.url(),body:(await page.locator('body').innerText()).slice(0,300)}));throw error;}
  assert.match(await page.locator('body').innerText(),/denied|assigned staff/i);
 }
 return{page,context};
}
async function submit(page,text){await page.locator('#ticket').fill(text);await page.locator('#submit').click();}
try{
 const unsigned=await browser.newContext({ignoreHTTPSErrors:true});contexts.push(unsigned);
 const denied=await unsigned.request.post(base+'/api/suggest',{data:{ticket:'anonymous'},headers:{Origin:base,'X-Review-Request':'1'}});assert.equal(denied.status(),403);
 await unsigned.close();
 checks.push('unauthenticated application submission denied');
 for(const identity of ['nonce','issuer','role','expired','audience','signature','malformed']){await mode('good',identity);const denied=await signedPage(inputs.reviewers[0],false);await denied.context.close();}
 await mode();const unassigned=await signedPage('90000000-0000-4000-8000-999999999999',false);await unassigned.context.close();
 checks.push('actual OAuth state/nonce/PKCE, signed RS256 identity and assigned reviewer gates reject invalid nonce/issuer/role/expiry/audience/signature, malformed token and unenrolled staff');
 const {page,context}=await signedPage();assert.match(await page.locator('aside').innerText(),/human review|need human review|review/i);
 await submit(page,'SYNTHETIC-SUCCESS-ONE');await page.locator('#suggestion').waitFor({state:'visible'});
 assert.equal(await page.locator('#summary').innerText(),'Reviewed SYNTHETIC-SUCCESS-ONE');assert.equal(await page.locator('#ticket').inputValue(),'');
 assert.match(await page.locator('#uncertainty').innerText(),/HIGH uncertainty.*human review/i);
 await page.locator('#clear').click();assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#summary').innerText(),'');
 checks.push('real browser sign-in, readiness, suggestion contract/uncertainty, human notice, successful input clearing and displayed-result clearing');
 const boundary='🙂'.repeat(5000);await submit(page,boundary);await page.locator('#suggestion').waitFor({state:'visible'});assert.equal(await page.locator('#ticket').inputValue(),'');
 await page.locator('#ticket').fill('🙂'.repeat(5121));assert(await page.locator('#submit').isDisabled());await page.locator('#clear-ticket').click();
 for(const body of [{},{ticket:null},{ticket:false},{ticket:1},{ticket:{}},{ticket:[]},{ticket:''},{ticket:'x'.repeat(20481)},{ticket:'valid',account:'override'}]){
  const r=await context.request.post(base+'/api/suggest',{data:body,headers:{Origin:base,'X-Review-Request':'1'}});assert([400,413].includes(r.status()),JSON.stringify(body).slice(0,40)+' '+r.status());assert(!JSON.stringify(await r.json()).includes('Reviewed'));
 }
 const duplicate=await context.request.post(base+'/api/suggest',{data:'{"ticket":"a","ti\\u0063ket":"b"}',headers:{Origin:base,'X-Review-Request':'1','Content-Type':'application/json'}});assert.equal(duplicate.status(),400);
 const foreignOrigin=await context.request.post(base+'/api/suggest',{data:{ticket:'origin-denial'},headers:{Origin:'https://foreign.invalid','X-Review-Request':'1'}});assert.equal(foreignOrigin.status(),403);
 checks.push('20000 UTF8-byte browser input succeeds; oversize UI/request, duplicate JSON, wrong types/extra controls and foreign origin fail safely');
 for(const failure of ['refusal','malformed','truncated','denial','timeout']){
  await mode(failure);await submit(page,'PRIVATE-FAILURE-'+failure);
  await page.waitForFunction(()=>!document.querySelector('#submit').disabled&&document.querySelector('#status').textContent.includes('No suggestion'),null,{timeout:40000});
  assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'PRIVATE-FAILURE-'+failure);
  assert(!(await page.locator('#status').innerText()).includes('PRIVATE-'));assert(!(await page.locator('body').innerText()).includes('PRIVATE-UPSTREAM-BODY'));
  await mode();await page.locator('#submit').click();await page.locator('#suggestion').waitFor({state:'visible'});assert.equal(await page.locator('#ticket').inputValue(),'');
 }
 checks.push('real30000ms model transport timeout plus refusal/malformed/truncated/provider denial fail safely and each recovers without hidden retry or ticket loss');
 for(const policy of ['foreign-region','logging','missing-logging','global-sku']){
  const before=(await state()).calls;await mode(policy);await submit(page,'POLICY-BOUNDARY');await page.locator('#retry').waitFor({state:'visible'});
  assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'POLICY-BOUNDARY');assert.equal((await state()).calls,before);
  await mode();await page.locator('#retry').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Ready.'));await page.locator('#clear-ticket').click();
 }
 checks.push('foreign region, enabled/unknown content logging and global SKU block readiness/inference with no fallback; explicit retry recovers');
 await mode('delay');await submit(page,'CANCELLED-RESULT');await page.locator('#clear').click();await page.waitForTimeout(1000);assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#summary').innerText(),'');await page.locator('#clear-ticket').click();
 await submit(page,'CHANGED-RESULT');await page.locator('#ticket').fill('NEW-UNSUBMITTED');await page.waitForTimeout(1000);assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'NEW-UNSUBMITTED');await page.locator('#clear-ticket').click();
 checks.push('late cleared/cancelled/changed-input responses cannot restore a stale result');
 await mode('markup');await submit(page,'MARKUP-DATA');await page.locator('#suggestion').waitFor({state:'visible'});assert.equal(await page.locator('#summary img').count(),0);assert.equal(await page.evaluate(()=>globalThis.injected),undefined);await page.locator('#clear').click();
 checks.push('model-supplied markup is displayed as text, never executed');
 await mode('barrier');const five=[{page,context}];for(const oid of inputs.reviewers.slice(1))five.push(await signedPage(oid));
 const loads=five.map((_,i)=>('CONCURRENT-'+i+' ').padEnd(20480,'x'));
 await Promise.all(five.map(({page},i)=>submit(page,loads[i])));await Promise.all(five.map(({page})=>page.locator('#suggestion').waitFor({state:'visible'})));
 for(const[{page},i]of five.map((v,i)=>[v,i])){assert.equal(await page.locator('#summary').innerText(),'Reviewed '+loads[i].slice(0,80));assert.equal(await page.locator('#ticket').inputValue(),'');}
 assert.equal((await state()).maxActive,5);
 checks.push('five actual signed-in browser sessions each submit20480 UTF8 bytes concurrently without response or identity mixing');
 for(const {page}of five){assert.deepEqual(await page.evaluate(()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage)})),{local:[],session:[]});await page.locator('#clear-ticket').click();await page.reload();assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#suggestion').isHidden());}
 checks.push('no local/session storage or reload-restored ticket/result history');
 await page.locator('#logout').click();await page.locator('#login').waitFor({state:'visible'});assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#suggestion').isHidden());
 assert.deepEqual(errors,[]);const observed=await state();assert.equal(observed.unknownUrls,0);
 console.log(JSON.stringify({passed:true,checks,providerFixture:observed,cloudOperations:false,
  boundary:'Real Chromium/TLS/browser/unchanged Node26.13 AMD64 app, actual OAuth/PKCE/RS256/native Azure request constructors with synthetic in-process provider transports and explicit fixture TLS certificate exception. No real Entra login, ARM account verification/model inference, provider retention or deployment acceptance.'}));
}finally{for(const context of contexts)await context.close();await browser.close();}
