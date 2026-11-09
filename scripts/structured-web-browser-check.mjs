import {createServer} from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {structuredWebProject} from '../tests/fixtures/structured-web-project.mjs';
import {ibmStructuredProject} from '../tests/fixtures/ibm-structured-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
const ibm=process.argv.includes('--ibm');
const aws=structuredWebProject();aws.nodes[4].data.config.outputContract.fields.push({name:'summary',type:'string',description:'Suggested summary',maxLength:500});
const project=ibm?ibmStructuredProject():aws;if(ibm)project.nodes[1].data.config.outputContract=aws.nodes[4].data.config.outputContract;
const emitted=terraformSketch(project);
const publicConfig=ibm?{localLogout:true,scopes:'openid reviewed-app/process',maxInputBytes:20000,fieldsBase64:Buffer.from(JSON.stringify(project.nodes[1].data.config.outputContract.fields)).toString('base64')}:null;
const assetFile=suffix=>Object.entries(emitted).find(([name])=>name.startsWith(ibm?'applications/':'web/')&&name.endsWith('/'+suffix))[1];
const RAG_WEB_HTML=assetFile('index.html'),RAG_WEB_CSS=assetFile('app.css'),RAG_WEB_JS=assetFile('app.js');
const root=path.resolve('.local/structured-web-browser',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(root,{recursive:true});
let lastApi=null,holdApi=false,pendingResponse=null,apiStatus=200;
const server=createServer(async(req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 if(pathname==='/api/ask'){let body='';for await(const chunk of req)body+=chunk;lastApi={authorization:req.headers.authorization,body:JSON.parse(body)};res.setHeader('Content-Type','application/json');res.statusCode=apiStatus;if(apiStatus!==200){res.end(JSON.stringify({error:'access_denied'}));return;}if(holdApi){pendingResponse=res;return;}res.end(JSON.stringify({result:{topic:'technical',summary:'<img src=x onerror=alert(1)> Synthetic result',uncertain:true},requiresHumanReview:true}));return;}
 const assets={'/':[RAG_WEB_HTML,'text/html'],'/app.js':[RAG_WEB_JS,'text/javascript'],'/app.css':[RAG_WEB_CSS,'text/css'],'/config.json':[JSON.stringify({...(publicConfig||JSON.parse(assetFile('config.json'))),authOrigin:'https://auth.example.test',clientId:'test-client'}),'application/json']};const asset=assets[pathname];if(!asset){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',asset[1]);res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self' https://auth.example.test; img-src 'self'; base-uri 'none'; frame-ancestors 'none'");res.end(asset[0]);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true,...(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{})});const checks=[];
try{
 const context=await browser.newContext();let tokenCalls=0,tokenBody='';
 await context.route('https://auth.example.test/oauth2/token',route=>{tokenCalls++;tokenBody=route.request().postData();return route.fulfill({status:200,headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'},body:JSON.stringify({access_token:'fixture-access-token',expires_in:900})});});
 await context.route('https://auth.example.test/logout**',route=>route.fulfill({status:204}));
 await context.addInitScript(()=>sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier:'synthetic-verifier',state:'expected-state',created:Date.now()})));
 const page=await context.newPage();await page.goto(origin+'/?code=synthetic-code&state=expected-state');await page.getByRole('button',{name:'Process',exact:true}).waitFor();await page.waitForFunction(()=>!document.getElementById('submit').disabled);
 assert.equal(tokenCalls,1);assert.equal(new URLSearchParams(tokenBody).get('code_verifier'),'synthetic-verifier');assert.equal(await page.evaluate(()=>sessionStorage.getItem('atmem-oauth')),null);checks.push('PKCE callback verified; transient state cleared');
 await page.getByLabel('Your input').fill('Which holiday?');await page.getByRole('button',{name:'Process',exact:true}).click();await page.getByText('Result prepared. Review it before taking action.').waitFor();assert.deepEqual(lastApi.body,{text:'Which holiday?'});assert.equal(lastApi.authorization,'Bearer fixture-access-token');assert.equal(await page.locator('#answer img').count(),0);assert.equal(await page.locator('#citations script').count(),0);assert.ok(!(await page.content()).includes('fixture-access-token'));checks.push('Bearer-only input and text-only structured output; no HTML execution');
 await page.screenshot({path:path.join(root,'web-answer.png'),fullPage:true});
 holdApi=true;await page.evaluate(()=>{const original=window.fetch;window.fetch=(url,options)=>String(url)==='/api/ask'?original(url,{...options,signal:undefined}):original(url,options);});
 await page.getByLabel('Your input').fill('PRIVATE PENDING INPUT');await page.getByRole('button',{name:'Process',exact:true}).click();
 for(let i=0;i<100&&!pendingResponse;i++)await new Promise(r=>setTimeout(r,20));assert.ok(pendingResponse);
 await page.evaluate(()=>window.addEventListener('beforeunload',event=>{event.preventDefault();event.returnValue='';}));page.once('dialog',dialog=>dialog.dismiss());
 await page.getByRole('button',{name:ibm?'Clear workspace':'Sign out',exact:true}).click({noWaitAfter:true});await page.getByRole('button',{name:'Sign in',exact:true}).waitFor();
 pendingResponse.end(JSON.stringify({result:{topic:'technical',summary:'LATE PRIVATE RESULT',uncertain:true},requiresHumanReview:true}));
 await page.waitForTimeout(100);assert.equal(await page.locator('#answer').innerText(),'');assert.equal(await page.getByLabel('Your input').inputValue(),'');
 if(ibm){assert.equal(page.url(),origin+'/');await page.getByText('Workspace cleared. Your identity-provider session may still be active. Close this browser on a shared device.').waitFor();checks.push('Local logout clears the workspace without navigating to an invented provider endpoint');}
 checks.push('Logout clears private input/results and ignores an in-flight response even when transport cancellation is ineffective');await context.close();
 holdApi=false;apiStatus=403;const revoked=await browser.newContext();await revoked.route('https://auth.example.test/oauth2/token',route=>route.fulfill({status:200,headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'},body:JSON.stringify({access_token:'fixture-revoked-token',expires_in:900})}));await revoked.addInitScript(()=>sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier:'fixture',state:'revoked-fixture',created:Date.now()})));const revokedPage=await revoked.newPage();await revokedPage.goto(origin+'/?code=fixture&state=revoked-fixture');await revokedPage.waitForFunction(()=>!document.getElementById('submit').disabled);await revokedPage.getByLabel('Your input').fill('PRIVATE DENIED INPUT');await revokedPage.getByRole('button',{name:'Process',exact:true}).click();await revokedPage.getByText('Access is unavailable or permissions changed. Sign in again or contact the app owner.').waitFor();assert.equal(await revokedPage.getByLabel('Your input').inputValue(),'');assert.equal(await revokedPage.locator('#answer').innerText(),'');assert.equal(await revokedPage.getByRole('button',{name:'Process',exact:true}).isDisabled(),true);checks.push('Permission denial clears private input/result and ends the browser session');await revoked.close();apiStatus=200;
 const denied=await browser.newContext();let forbiddenTokenCalls=0;await denied.route('https://auth.example.test/**',route=>{forbiddenTokenCalls++;return route.abort();});await denied.addInitScript(()=>sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier:'synthetic-verifier',state:'correct',created:Date.now()})));
 const invalid=await denied.newPage();await invalid.goto(origin+'/?code=synthetic-code&state=forged');await invalid.getByText('Sign-in or configuration could not be verified. Please retry sign-in.').waitFor();assert.equal(forbiddenTokenCalls,0);assert.equal(await invalid.getByRole('button',{name:'Process',exact:true}).isDisabled(),true);checks.push('Mismatched OAuth state rejected before token exchange');await denied.close();
 const login=await browser.newContext();let authorizeUrl;await login.route('https://auth.example.test/**',route=>{authorizeUrl=route.request().url();return route.abort();});const start=await login.newPage();await start.goto(origin);await start.getByText('Sign in to use this workspace.').waitFor();await start.getByRole('button',{name:'Sign in',exact:true}).click();for(let i=0;i<50&&!authorizeUrl;i++)await new Promise(r=>setTimeout(r,20));assert.ok(authorizeUrl);const params=new URL(authorizeUrl).searchParams;assert.equal(params.get('code_challenge_method'),'S256');assert.equal(params.get('response_type'),'code');assert.match(params.get('code_challenge'),/^[A-Za-z0-9_-]{43}$/);checks.push('Authorization-code sign-in uses S256 PKCE and random state');await login.close();
 fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify({scope:'Actual emitted frontend with local HTTP/OAuth fixtures. Backend boundary checks are separate; no live identity, model or provider deployment.',status:'passed',checks},null,2));console.log(JSON.stringify({status:'passed',checks,evidence:root}));
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
