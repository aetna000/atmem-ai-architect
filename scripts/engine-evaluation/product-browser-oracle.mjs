// Independent user journeys against unchanged emitted browser assets and application.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ATMEM_PRODUCT_BROWSER_ORIGIN,out=process.env.ATMEM_PRODUCT_BROWSER_OUTPUT;
const browser=await chromium.launch({headless:true});const page=await browser.newPage();
const responses=[];page.on('response',async response=>{if(response.url().endsWith('/api/suggest'))responses.push({status:response.status(),body:await response.text().catch(()=>'<aborted>')});});
const errors=[],checks=[];page.on('pageerror',error=>errors.push(error.message));
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS',name);}
async function waitText(id,text){await page.waitForFunction(({id,text})=>document.getElementById(id)?.textContent.includes(text),{id,text},{timeout:15000});}
async function submit(text){await page.locator('#ticket').fill(text);await page.locator('#suggest').click();}
try{
 await page.goto(base);
 await check('Signed out controls deny submission',async()=>{await page.locator('#signin:enabled').waitFor();assert(await page.locator('#ticket').isDisabled());assert(await page.locator('#suggest').isDisabled());});
 await check('No token and forged signature denied by local cryptographic gateway',async()=>{
  for(const value of ['', 'forged.token.value',process.env.ATMEM_PRODUCT_BROWSER_EXPIRED_TOKEN]){
   const response=await page.request.post(base+'/api/suggest',{headers:{authorization:'Bearer '+value},data:{ticket:'denied'}});assert.equal(response.status(),401);
  }
 });
 await check('Signed wrong-role identity denied by captured handler',async()=>{const response=await page.request.post(base+'/api/suggest',{headers:{authorization:'Bearer '+process.env.ATMEM_PRODUCT_BROWSER_ROLE_TOKEN},data:{ticket:'wrong role'}});assert.equal(response.status(),403);});
 await check('State mismatch never exchanges authorization code',async()=>{
  let exchanges=0;const count=request=>{if(request.url().includes('/oauth2/token'))exchanges++;};page.on('request',count);
  await page.evaluate(()=>sessionStorage.setItem('review.pkce',JSON.stringify({verifier:'verifier',state:'expected',created:Date.now()})));
  await page.goto(base+'/auth/callback?code=synthetic&state=wrong');await waitText('identity','unavailable');assert.equal(exchanges,0);assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.getItem('review.pkce')),null);page.off('request',count);
 });
 await check('Actual browser performs authorization-code S256 PKCE exchange',async()=>{await page.locator('#signin').click();await waitText('identity','Signed in');assert(await page.locator('#ticket').isEnabled());assert.equal(new URL(page.url()).search,'');assert.equal(await page.evaluate(()=>sessionStorage.length),0);assert.equal(await page.evaluate(()=>localStorage.length),0);});
 await check('Human review and explicit uncertainty displayed; ticket clears on submit',async()=>{
  await submit('SYNTHETIC-TRANSIENT-TICKET-CANARY');await waitText('status','Human review');assert.equal(await page.locator('#ticket').inputValue(),'');assert(await page.locator('#suggestion').isVisible());assert.match(await page.locator('#uncertainty').innerText(),/HIGH/);assert.match(await page.locator('body').innerText(),/No replies are sent/);
 });
 await check('Clear removes suggestion and transient text',async()=>{await page.locator('#clear').click();assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#summary').textContent(),'');assert.equal(await page.locator('#ticket').inputValue(),'');});
 await check('Invalid empty and oversize browser inputs never call API',async()=>{
  let calls=0;const count=request=>{if(request.url().endsWith('/api/suggest'))calls++;};page.on('request',count);
  await submit(' ');await waitText('status','non-empty');await submit('x'.repeat(20481));await waitText('status','non-empty');assert.equal(calls,0);page.off('request',count);
 });
 await check('Model failure is safe and subsequent request recovers',async()=>{
  await submit('model-timeout');await waitText('status','No suggestion');assert(await page.locator('#suggestion').isHidden());assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE-SYNTHETIC/);await submit('recovery');await waitText('status','Human review');
 });
 await check('Malformed model output rejected through browser and handler',async()=>{await submit('unsafe-output');await waitText('status','No suggestion');assert(await page.locator('#suggestion').isHidden());});
 await check('Clearing in-flight request prevents late suggestion restoration',async()=>{await submit('slow-clear');await waitText('status','Preparing');await page.locator('#clear').click();await page.waitForTimeout(2500);assert(await page.locator('#suggestion').isHidden());assert.equal(await page.locator('#ticket').inputValue(),'');await waitText('status','Cleared');});
 await check('No ticket or tokens persisted; reload signs out',async()=>{
  assert.equal(await page.evaluate(()=>localStorage.length),0);assert.equal(await page.evaluate(()=>sessionStorage.length),0);assert.equal((await page.context().cookies()).length,0);
  await page.reload();await waitText('identity','Sign in');assert(await page.locator('#ticket').isDisabled());assert(await page.locator('#suggestion').isHidden());
 });
 await page.screenshot({path:path.join(out,'signed-out.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({passed:true,checks,pageErrors:errors},null,2)+'\n');
}finally{const fetchBinding=await page.evaluate(async()=>{const {ReviewSession}=await import('/core.js');const s=new ReviewSession();let member,unbound;try{member=(await s.fetcher('/config.json')).status;}catch(error){member=error.message;}try{unbound=(await (0,s.fetcher)('/config.json')).status;}catch(error){unbound=error.message;}return {member,unbound};}).catch(error=>({diagnosticError:error.message}));fs.writeFileSync(path.join(out,'observed.json'),JSON.stringify({responses,errors,checks,fetchBinding,url:page.url(),body:await page.locator('body').innerText().catch(()=>''),status:await page.locator('#status').textContent().catch(()=>null)},null,2)+'\n');await page.screenshot({path:path.join(out,'last-page.png'),fullPage:true}).catch(()=>{});await browser.close();}
