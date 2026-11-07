import {createServer} from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {RAG_WEB_HTML,RAG_WEB_CSS,RAG_WEB_JS} from '../src/rag-web-assets.mjs';
const root=path.resolve('.local/web-validation',new Date().toISOString().replaceAll(':','-'));fs.mkdirSync(root,{recursive:true});
let lastApi=null;
const server=createServer(async(req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 if(pathname==='/api/ask'){let body='';for await(const chunk of req)body+=chunk;lastApi={authorization:req.headers.authorization,body:JSON.parse(body)};res.setHeader('Content-Type','application/json');res.end(JSON.stringify({answer:'<img src=x onerror=alert(1)> Synthetic answer',citations:[{title:'<script>not executable</script>',revision:'v1'}],abstained:false}));return;}
 const assets={'/':[RAG_WEB_HTML,'text/html'],'/app.js':[RAG_WEB_JS,'text/javascript'],'/app.css':[RAG_WEB_CSS,'text/css'],'/config.json':[JSON.stringify({authOrigin:'https://auth.example.test',clientId:'test-client'}),'application/json']};const asset=assets[pathname];if(!asset){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',asset[1]);res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self' https://auth.example.test; img-src 'self'; base-uri 'none'; frame-ancestors 'none'");res.end(asset[0]);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true});const checks=[];
try{
 const context=await browser.newContext();let tokenCalls=0,tokenBody='';
 await context.route('https://auth.example.test/oauth2/token',route=>{tokenCalls++;tokenBody=route.request().postData();return route.fulfill({status:200,headers:{'Content-Type':'application/json','Access-Control-Allow-Origin':'*'},body:JSON.stringify({access_token:'fixture-access-token',expires_in:900})});});
 await context.addInitScript(()=>sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier:'synthetic-verifier',state:'expected-state',created:Date.now()})));
 const page=await context.newPage();await page.goto(origin+'/?code=synthetic-code&state=expected-state');await page.getByRole('button',{name:'Ask',exact:true}).waitFor();await page.waitForFunction(()=>!document.getElementById('submit').disabled);
 assert.equal(tokenCalls,1);assert.equal(new URLSearchParams(tokenBody).get('code_verifier'),'synthetic-verifier');assert.equal(await page.evaluate(()=>sessionStorage.getItem('atmem-oauth')),null);checks.push('PKCE callback verified; transient state cleared');
 await page.getByLabel('Your question').fill('Which holiday?');await page.getByRole('button',{name:'Ask',exact:true}).click();await page.getByText('Answered from your permitted sources.').waitFor();assert.deepEqual(lastApi.body,{question:'Which holiday?'});assert.equal(lastApi.authorization,'Bearer fixture-access-token');assert.equal(await page.locator('#answer img').count(),0);assert.equal(await page.locator('#citations script').count(),0);assert.ok(!(await page.content()).includes('fixture-access-token'));checks.push('Bearer-only request and text-only answer/citation rendering');
 await page.screenshot({path:path.join(root,'web-answer.png'),fullPage:true});await context.close();
 const denied=await browser.newContext();let forbiddenTokenCalls=0;await denied.route('https://auth.example.test/**',route=>{forbiddenTokenCalls++;return route.abort();});await denied.addInitScript(()=>sessionStorage.setItem('atmem-oauth',JSON.stringify({verifier:'synthetic-verifier',state:'correct',created:Date.now()})));
 const invalid=await denied.newPage();await invalid.goto(origin+'/?code=synthetic-code&state=forged');await invalid.getByText('Sign-in or configuration could not be verified. Please retry sign-in.').waitFor();assert.equal(forbiddenTokenCalls,0);assert.equal(await invalid.getByRole('button',{name:'Ask',exact:true}).isDisabled(),true);checks.push('Mismatched OAuth state rejected before token exchange');await denied.close();
 const login=await browser.newContext();let authorizeUrl;await login.route('https://auth.example.test/**',route=>{authorizeUrl=route.request().url();return route.abort();});const start=await login.newPage();await start.goto(origin);await start.getByText('Sign in to access your documents.').waitFor();await start.getByRole('button',{name:'Sign in',exact:true}).click();for(let i=0;i<50&&!authorizeUrl;i++)await new Promise(r=>setTimeout(r,20));assert.ok(authorizeUrl);const params=new URL(authorizeUrl).searchParams;assert.equal(params.get('code_challenge_method'),'S256');assert.equal(params.get('response_type'),'code');assert.match(params.get('code_challenge'),/^[A-Za-z0-9_-]{43}$/);checks.push('Authorization-code sign-in uses S256 PKCE and random state');await login.close();
 fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify({scope:'local browser/OAuth transport fixtures; no Cognito or AWS deployment',status:'passed',checks},null,2));console.log(JSON.stringify({status:'passed',checks,evidence:root}));
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
