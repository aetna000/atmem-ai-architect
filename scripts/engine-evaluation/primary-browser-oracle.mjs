// Independent journeys for the exposed primary-Build package, never production dispatch.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ATMEM_PRODUCT_BROWSER_ORIGIN,out=process.env.ATMEM_PRODUCT_BROWSER_OUTPUT;
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const errors=[],checks=[],responses=[];page.on('pageerror',error=>errors.push(error.message));
page.on('response',async response=>{if(response.url().endsWith('/suggest'))responses.push({status:response.status(),body:await response.text().catch(()=>'<aborted>')});});
// The packaged app validates its regional Cognito origin. Keep that configuration
// and every packaged asset unchanged; route only that exact synthetic HTTPS origin
// into the independent local OAuth emulator, including explicit response CORS.
await page.route('https://independent.auth.ap-southeast-2.amazoncognito.com/**',async route=>{
 const request=route.request(),url=new URL(request.url());
 const response=await page.request.fetch(base+url.pathname+url.search,{method:request.method(),data:request.postData()||undefined,headers:{'Content-Type':request.headers()['content-type']||'application/x-www-form-urlencoded'},maxRedirects:0});
 await route.fulfill({status:response.status(),headers:{...response.headers(),'access-control-allow-origin':base},body:await response.body()});
});
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS',name);}
async function waitText(text){await page.waitForFunction(text=>document.querySelector('#status')?.textContent.includes(text),text,{timeout:15000});}
async function submit(text){await page.locator('#ticket').fill(text);await page.locator('#submit').click();}
try{
 await page.goto(base);
 await check('Signed-out controls prohibit submission',async()=>{await page.locator('#login:visible').waitFor();assert(await page.locator('#ticket').isDisabled());assert(await page.locator('#submit').isDisabled());});
 await check('No token, forged signature and expired signed token denied by cryptographic emulator',async()=>{
  for(const value of ['', 'forged.token.value',process.env.ATMEM_PRODUCT_BROWSER_EXPIRED_TOKEN,...JSON.parse(process.env.ATMEM_PRODUCT_BROWSER_INVALID_CLAIM_TOKENS)]){
   const response=await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+value},data:{text:'denied'}});assert.equal(response.status(),401);
  }
 });
 await check('Valid signature with an unapproved staff subject denied by packaged handler',async()=>{
  const response=await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+process.env.ATMEM_PRODUCT_BROWSER_ROLE_TOKEN},data:{text:'unapproved'}});assert.equal(response.status(),403);
 });
 await check('OAuth state mismatch never exchanges the code and removes pending state',async()=>{
  let exchanges=0;const count=request=>{if(request.url().includes('/oauth2/token'))exchanges++;};page.on('request',count);
  await page.evaluate(()=>sessionStorage.setItem('oauth',JSON.stringify({verifier:'verifier',state:'expected',at:Date.now()})));
  await page.goto(base+'/?code=synthetic&state=wrong');await waitText('Sign-in unavailable');assert.equal(exchanges,0);assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.getItem('oauth')),null);page.off('request',count);
 });
 await check('Actual browser performs code/S256-PKCE exchange and enables the tool',async()=>{
  await page.locator('#login').click();await waitText('Signed in');assert(await page.locator('#ticket').isEnabled());assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.length),0);assert.equal(await page.evaluate(()=>localStorage.length),0);
 });
 await check('Browser-to-packaged-handler suggestion shows uncertainty and human review',async()=>{
  await submit('SYNTHETIC-TRANSIENT-TICKET-CANARY');await waitText('Uncertain suggestion');assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#suggestion').isVisible());assert.match(await page.locator('#uncertainty').innerText(),/HIGH/);assert.match(await page.locator('body').innerText(),/cannot send replies or change customer records/);assert.equal(await page.locator('#summary').textContent(),'Fixture: SYNTHETIC-TRANSIENT-TICKET-CANARY');
 });
 await check('Reviewer clear removes all transient fields and review checkbox',async()=>{
  await page.locator('#reviewed').check();await page.locator('#clear').click();assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#summary').textContent(),'');assert.equal(await page.locator('#ticket').inputValue(),'');assert(!(await page.locator('#reviewed').isChecked()));
 });
 await check('Empty and UTF-8-oversized browser input never reaches the API',async()=>{
  let calls=0;const count=request=>{if(request.url().endsWith('/suggest'))calls++;};page.on('request',count);
  await submit(' ');await waitText('1–20,480');await submit('x'.repeat(20481));await waitText('1–20,480');await submit('é'.repeat(10241));await waitText('1–20,480');assert.equal(calls,0);page.off('request',count);
 });
 await check('Exact UTF-8 byte limit succeeds through the connected journey',async()=>{await submit('é'.repeat(10240));await waitText('Uncertain suggestion');assert(await page.locator('#suggestion').isVisible());});
 await check('Model failure safely clears suggestions and a subsequent request recovers',async()=>{
  await submit('model-timeout');await waitText('No suggestion');assert(await page.locator('#suggestion').isHidden());assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE-SYNTHETIC/);await submit('recovery');await waitText('Uncertain suggestion');
 });
 await check('Malformed model object is rejected by the actual handler',async()=>{await submit('unsafe-output');await waitText('No suggestion');assert(await page.locator('#suggestion').isHidden());});
 await check('HTML-looking model output renders inert text with real CSP',async()=>{
  await submit('html-output');await waitText('Uncertain suggestion');assert.equal(await page.locator('#summary').textContent(),'<img src=x onerror=window.__oracleXss=1>');assert.equal(await page.locator('#summary img').count(),0);assert.equal(await page.evaluate(()=>window.__oracleXss),undefined);
 });
 await check('Clearing an in-flight request prevents late suggestion restoration',async()=>{
  await submit('slow-clear');await waitText('Preparing');await page.locator('#clear').click();await page.waitForTimeout(2500);assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'');await waitText('cleared');
 });
 await check('Five simultaneous requests stay isolated through the signed gateway and packaged handler',async()=>{
  await Promise.all(Array.from({length:5},async(_,i)=>{const text='parallel-review-'+i;const response=await page.request.post(base+'/suggest',{headers:{authorization:'Bearer '+process.env.ATMEM_PRODUCT_BROWSER_VALID_TOKEN},data:{text}});assert.equal(response.status(),200);assert.equal((await response.json()).summary,'Fixture: '+text);}));
 });
 await check('No ticket/token persistence and reload returns to signed-out state',async()=>{
  assert.equal(await page.evaluate(()=>localStorage.length),0);assert.equal(await page.evaluate(()=>sessionStorage.length),0);assert.equal((await page.context().cookies()).length,0);
  await page.reload();await page.locator('#login:visible').waitFor();assert(await page.locator('#ticket').isDisabled());assert(await page.locator('#submit').isDisabled());assert(await page.locator('#suggestion').isHidden());
 });
 await check('Explicit logout clears the session and visible result',async()=>{
  await page.locator('#login').click();await waitText('Signed in');await submit('logout-example');await waitText('Uncertain suggestion');await page.locator('#logout').click();await page.locator('#login:visible').waitFor();assert(await page.locator('#ticket').isDisabled());assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#summary').textContent(),'');assert.equal(await page.evaluate(()=>sessionStorage.length+localStorage.length),0);
 });
 await check('Token response expiry clears transient content and requires sign-in again',async()=>{
  const configured=await page.request.post(base+'/__oracle/session-duration',{data:{seconds:1}});assert.equal(configured.status(),200);
  await page.locator('#login').click();await waitText('Signed in');await page.locator('#ticket').fill('must clear at expiry');await waitText('Session expired');assert(await page.locator('#ticket').isDisabled());assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#suggestion').isHidden());
 });
 await page.screenshot({path:path.join(out,'signed-out.png'),fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({passed:true,checks,pageErrors:errors},null,2)+'\n');
}finally{
 fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify({responses,errors,checks,url:page.url(),body:await page.locator('body').innerText().catch(()=>''),status:await page.locator('#status').textContent().catch(()=>null)},null,2)+'\n');
 await page.screenshot({path:path.join(out,'last-page.png'),fullPage:true}).catch(()=>{});await browser.close();
}
