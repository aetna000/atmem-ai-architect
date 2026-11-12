// Evaluation-only adapter for observed handler.py/ticket/reviewers and actual DOM.
// Frozen22 requirements govern verdicts; no package source is changed.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ATMEM_PRODUCT_BROWSER_ORIGIN,out=process.env.ATMEM_PRODUCT_BROWSER_OUTPUT;
const browser=await chromium.launch({headless:true}),page=await browser.newPage();page.setDefaultTimeout(15000);
const errors=[],checks=[],responses=[];page.on('pageerror',e=>errors.push(e.message));
page.on('response',async r=>{if(r.url().endsWith('/suggest'))responses.push({status:r.status(),body:await r.text().catch(()=>'<aborted>')});});
await page.route('https://independent.auth.ap-southeast-2.amazoncognito.com/**',async route=>{
 const req=route.request(),url=new URL(req.url());const response=await page.request.fetch(base+url.pathname+url.search,{method:req.method(),data:req.postData()||undefined,headers:{'Content-Type':req.headers()['content-type']||'application/x-www-form-urlencoded'},maxRedirects:0});
 await route.fulfill({status:response.status(),headers:{...response.headers(),'access-control-allow-origin':base},body:await response.body()});
});
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS',name);}
async function waitText(text){await page.waitForFunction(t=>document.querySelector('#status')?.textContent.includes(t),text,{timeout:15000});}
async function submit(ticket){await page.locator('#ticket').fill(ticket);await page.locator('#suggest').click();}
async function signIn(){await page.locator('#signin').click();await waitText('Signed in');}
try{
 await check('Delayed prerequisite disables dependent actions and then recovers',async()=>{
  let release;const gate=new Promise(r=>release=r);await page.route('**/config',async route=>{await gate;await route.continue();});
  await page.goto(base,{waitUntil:'domcontentloaded'});assert(await page.locator('#signin').isDisabled());assert(await page.locator('#suggest').isDisabled());release();await page.unroute('**/config');await page.locator('#signin').waitFor();await page.waitForFunction(()=>!document.querySelector('#signin').disabled);
 });
 await check('Signed-out controls prevent API submission',async()=>{assert(await page.locator('#suggest').isDisabled());});
 await check('Cryptographic gateway rejects absent/forged/expired/wrong issuer/client/scope/token-kind',async()=>{
  for(const value of ['','forged.token.value',process.env.ATMEM_PRODUCT_BROWSER_EXPIRED_TOKEN,...JSON.parse(process.env.ATMEM_PRODUCT_BROWSER_INVALID_CLAIM_TOKENS)])assert.equal((await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+value},data:{ticket:'denied'}})).status(),401);
 });
 await check('Signed identity outside reviewer group is denied by packaged handler',async()=>{assert.equal((await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+process.env.ATMEM_PRODUCT_BROWSER_ROLE_TOKEN},data:{ticket:'unapproved'}})).status(),403);});
 await check('Mismatched OAuth state removes pending code/state without token exchange and allows retry',async()=>{
  let exchanges=0;const count=r=>{if(r.url().includes('/oauth2/token'))exchanges++;};page.on('request',count);
  await page.evaluate(()=>sessionStorage.setItem('oauth',JSON.stringify({verifier:'verifier',state:'expected',at:Date.now()})));
  await page.goto(base+'/?code=synthetic&state=wrong');await waitText('Setup or sign-in failed');assert.equal(exchanges,0);assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.getItem('oauth')),null);page.off('request',count);await page.locator('#retry').click();await waitText('Sign in to');
 });
 await check('Actual browser code/S256-PKCE exchange enables suggestions without token persistence',async()=>{await signIn();assert(await page.locator('#suggest').isEnabled());assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.length+localStorage.length),0);});
 await check('Connected success shows validated uncertainty/human review and clears processed paste',async()=>{
  await submit('SYNTHETIC-TRANSIENT-TICKET-CANARY');await waitText('Suggestion ready');assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#result').isVisible());assert.match(await page.locator('#uncertainty').innerText(),/HIGH/);assert.match(await page.locator('body').innerText(),/No reply has been sent. No customer record has changed./);assert.equal(await page.locator('#summary').textContent(),'Fixture: SYNTHETIC-TRANSIENT-TICKET-CANARY');
 });
 await check('Reviewer clear removes displayed suggestion fields',async()=>{await page.locator('#clear').click();assert(await page.locator('#result').isHidden());for(const id of ['summary','topic','urgency','uncertainty','json'])assert.equal(await page.locator('#'+id).textContent(),'');});
 await check('Empty and UTF-8 oversized browser input never reaches API',async()=>{let calls=0;const count=r=>{if(r.url().endsWith('/suggest'))calls++;};page.on('request',count);for(const input of [' ','x'.repeat(20481),'é'.repeat(10241)]){await submit(input);await waitText('1–20,480');}assert.equal(calls,0);page.off('request',count);});
 await check('Exact UTF-8 byte limit succeeds through all local connections',async()=>{await submit('é'.repeat(10240));await waitText('Suggestion ready');assert(await page.locator('#result').isVisible());});
 await check('Model failure is safe and subsequent request recovers',async()=>{await submit('model-timeout');await waitText('No suggestion');assert(await page.locator('#result').isHidden());assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE-SYNTHETIC/);await submit('recovery');await waitText('Suggestion ready');});
 await check('Malformed model object rejected by packaged handler',async()=>{await submit('unsafe-output');await waitText('No suggestion');assert(await page.locator('#result').isHidden());});
 await check('HTML-looking output is inert text with packaged CSP',async()=>{await submit('html-output');await waitText('Suggestion ready');assert.equal(await page.locator('#summary').textContent(),'<img src=x onerror=window.__oracleXss=1>');assert.equal(await page.locator('#summary img').count(),0);assert.equal(await page.evaluate(()=>window.__oracleXss),undefined);});
 await check('Schema-valid non-BMP Unicode output crosses Python/JSON/JavaScript without a unit mismatch',async()=>{await submit('unicode-output');await waitText('Suggestion ready');assert.match(await page.locator('#uncertainty').textContent(),new RegExp('😀'.repeat(151)));});
 await check('Clearing in-flight suggestion prevents late restoration',async()=>{await submit('slow-clear');await waitText('Preparing');await page.locator('#clear').click();await page.waitForTimeout(2500);assert(await page.locator('#result').isHidden());assert.equal(await page.locator('#summary').textContent(),'');await waitText('cleared');});
 await check('Clear-all also erases paste during in-flight work',async()=>{await submit('slow-clear');await waitText('Preparing');await page.locator('#erase').click();await page.waitForTimeout(2500);assert(await page.locator('#result').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'');});
 await check('Five simultaneous signed requests remain isolated through packaged handler',async()=>{await Promise.all(Array.from({length:5},async(_,i)=>{const ticket='parallel-review-'+i;const r=await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+process.env.ATMEM_PRODUCT_BROWSER_VALID_TOKEN},data:{ticket}});assert.equal(r.status(),200);assert.equal((await r.json()).summary,'Fixture: '+ticket);}));});
 await check('No browser storage/cookies and reload returns signed-out',async()=>{assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);assert.equal((await page.context().cookies()).length,0);await page.reload();assert(await page.locator('#suggest').isDisabled());assert(await page.locator('#result').isHidden());});
 await check('Immediate login after reload and explicit logout clear session/results',async()=>{await signIn();await submit('logout-example');await waitText('Suggestion ready');await page.locator('#signout').click();await waitText('Sign in to');assert(await page.locator('#suggest').isDisabled());assert(await page.locator('#result').isHidden());assert.equal(await page.locator('#summary').textContent(),'');assert.equal(await page.evaluate(()=>sessionStorage.length+localStorage.length),0);});
 await check('Expired token is rejected before a new request; re-login recovers',async()=>{assert.equal((await page.request.post(base+'/__oracle/session-duration',{data:{seconds:1}})).status(),200);await signIn();await page.waitForTimeout(1200);await submit('expired-ticket');await waitText('Session expired');assert(await page.locator('#suggest').isDisabled());assert(await page.locator('#result').isHidden());await page.request.post(base+'/__oracle/session-duration',{data:{seconds:300}});await signIn();await submit('expiry-recovery');await waitText('Suggestion ready');});
 await check('Config failure keeps actions disabled and explicit retry recovers without losing paste',async()=>{await page.route('**/config',route=>route.fulfill({status:503,body:'unavailable'}));await page.reload();await waitText('Setup or sign-in failed');assert(await page.locator('#signin').isDisabled());assert(await page.locator('#suggest').isDisabled());await page.locator('#ticket').fill('redacted retry');await page.unroute('**/config');await page.locator('#retry').click();await waitText('Sign in to');assert.equal(await page.locator('#ticket').inputValue(),'redacted retry');assert(await page.locator('#signin').isEnabled());});
 assert.deepEqual(errors,[]);await page.screenshot({path:path.join(out,'final-page.png'),fullPage:true});fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({passed:true,checks,pageErrors:errors},null,2)+'\n');
}finally{fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify({responses,errors,checks,url:page.url(),body:await page.locator('body').innerText().catch(()=>''),status:await page.evaluate(()=>document.querySelector('#status')?.textContent??null).catch(()=>null)},null,2)+'\n');await page.screenshot({path:path.join(out,'last-page.png'),fullPage:true}).catch(()=>{});await browser.close();}
