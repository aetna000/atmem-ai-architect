// Independent UI contract adapter. No project code is changed; only API/identity
// responses are fixtures. Length limits follow the delivered JSON Schema.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
const schema=JSON.parse(fs.readFileSync('/work/source/docs/response.schema.json','utf8'));
const limit=schema.properties.uncertainty.properties.reason.maxLength;
assert.equal(limit,300,'Observed public contract changed: review this evaluator adapter');
let result,origin,calls=0;
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://local');
 res.setHeader('Cache-Control','no-store');
 if(url.pathname==='/config'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({CLIENT_ID:'unicodefixture',AUTH_DOMAIN:'https://independent.auth.ap-southeast-2.amazoncognito.com',REDIRECT_URI:origin+'/'}));return;}
 if(url.pathname==='/suggest'){calls++;req.resume();res.setHeader('Content-Type','application/json');res.end(JSON.stringify(result));return;}
 const file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[url.pathname];
 if(!file){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync('/work/source/web/'+file));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));origin='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true,chromiumSandbox:true});
const checks=[];
try{
 for(const example of [{name:'BMP reason boundary',reason:'x'.repeat(limit),valid:true},{name:'Non-BMP valid reason',reason:'😀'.repeat(151),valid:true},{name:'Non-BMP reason boundary',reason:'😀'.repeat(limit),valid:true},{name:'Non-BMP reason over bound',reason:'😀'.repeat(limit+1),valid:false},{name:'Non-BMP valid summary',summary:'😀'.repeat(301),valid:true},{name:'Non-BMP summary over bound',summary:'😀'.repeat(601),valid:false}]){
  result={summary:example.summary??'Independent synthetic summary',topic:'technical',urgency:'normal',uncertainty:{level:'high',reason:example.reason??'Synthetic uncertainty'}};
  const page=await browser.newPage();page.setDefaultTimeout(5000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>sessionStorage.setItem('oauth',JSON.stringify({verifier:'synthetic-verifier',state:'synthetic-state',at:Date.now()})));
  await page.route('https://independent.auth.ap-southeast-2.amazoncognito.com/oauth2/token',route=>route.fulfill({contentType:'application/json',headers:{'access-control-allow-origin':origin},body:JSON.stringify({access_token:'synthetic-access-token',expires_in:300})}));
  await page.goto(origin+'/?code=synthetic-code&state=synthetic-state');await page.waitForFunction(()=>!document.querySelector('#suggest').disabled);
  await page.locator('#ticket').fill('Synthetic contract fixture');const before=calls;await page.locator('#suggest').click();
  await page.waitForFunction(()=>/Suggestion ready|No suggestion/.test(document.querySelector('#status').textContent));
  const state=await page.locator('#status').textContent(),visible=await page.locator('#result').isVisible();
  const diagnostic={case:example.name,expectedValid:example.valid,actualVisible:visible,status:state,reasonCodePoints:[...result.uncertainty.reason].length,reasonUtf16Units:result.uncertainty.reason.length,summaryCodePoints:[...result.summary].length,summaryUtf16Units:result.summary.length};
  assert.equal(calls,before+1);assert.deepEqual(errors,[]);assert.equal(visible,example.valid,JSON.stringify(diagnostic));
  if(example.valid){assert.equal(await page.locator('#summary').textContent(),result.summary);assert((await page.locator('#uncertainty').textContent()).endsWith(result.uncertainty.reason));}
  checks.push({...diagnostic,passed:true});await page.close();
 }
 console.log('INDEPENDENT_UNICODE_CONTRACT_PASSED',JSON.stringify(checks));
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
