// Independent evaluator: actual exported static files, native browser file reads.
import assert from 'node:assert/strict';import fs from 'node:fs';import http from 'node:http';import {pathToFileURL} from 'node:url';
const {chromium}=await import(process.env.ATMEM_PLAYWRIGHT_MODULE);
const browser=await chromium.launch({headless:true,chromiumSandbox:true});let count=0;
const errors=[],network=[];const page=await browser.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url());});
const url=pathToFileURL('/work/source/index.html').href;
const sample=(room='Independent room',samples=[-10,0,20,30])=>JSON.stringify({room,samples});
async function choose(content,name='readings.json'){await page.locator('#climate-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.isBuffer(content)?content:Buffer.from(content)});}
async function ready(){await page.locator('#results').waitFor({state:'visible'});}
async function invalid(content){await choose(content);await page.locator('#error').waitFor({state:'visible'});assert(await page.locator('#results').isHidden());assert.equal(await page.locator('#room').textContent(),'');assert.doesNotMatch(await page.locator('#error').innerText(),/PRIVATE_SOURCE_DATA/);count++;}
try{
 await page.goto(url);await page.waitForFunction(()=>!document.querySelector('#climate-file').disabled);
 await choose(sample());await ready();assert.equal(await page.locator('#room').textContent(),'Independent room');assert.equal(await page.locator('#count').textContent(),'4');assert.equal(await page.locator('#minimum').textContent(),'-10.0');assert.equal(await page.locator('#maximum').textContent(),'30.0');assert.equal(await page.locator('#mean').textContent(),'10.0');count++;
 await choose(sample('Boundaries',[-50,70]));await ready();assert.equal(await page.locator('#mean').textContent(),'10.0');assert.equal(await page.locator('#minimum').textContent(),'-50.0');assert.equal(await page.locator('#maximum').textContent(),'70.0');count++;
 await choose(sample('Full set',Array(1000).fill(2)));await ready();assert.equal(await page.locator('#count').textContent(),'1000');assert.equal(await page.locator('#mean').textContent(),'2.0');count++;
 await choose(sample('Rounding',[-1,-1,10]));await ready();assert.equal(await page.locator('#mean').textContent(),'2.7');count++;
 await choose(sample('😀'.repeat(80),[1]));await ready();assert.equal(await page.locator('#room').textContent(),'😀'.repeat(80));count++;
 await invalid(sample('😀'.repeat(81),[1]));
 await choose(sample('<img src=x onerror=window.__injected=1>',[1]));await ready();assert.equal(await page.locator('#room').textContent(),'<img src=x onerror=window.__injected=1>');assert.equal(await page.locator('#room img').count(),0);assert.equal(await page.evaluate(()=>window.__injected),undefined);count++;
 const valid=Buffer.from(sample('Byte boundary',[1]));await choose(Buffer.concat([valid,Buffer.alloc(65536-valid.length,32)]));await ready();count++;
 await invalid(Buffer.concat([valid,Buffer.alloc(65537-valid.length,32)]));
 for(const content of ['PRIVATE_SOURCE_DATA not JSON','null','[]',JSON.stringify({samples:[1]}),JSON.stringify({room:'x',samples:[1],extra:true}),sample(' ',[1]),sample('x'.repeat(81),[1]),sample('x',[]),sample('x',Array(1001).fill(1)),sample('x',[true]),sample('x',['1']),sample('x',[null]),sample('x',[-50.01]),sample('x',[70.01]),'{"room":"x","samples":[1e309]}','{"room":"x","room":"y","samples":[1]}',Buffer.from([123,255,125])])await invalid(content);
 await choose(sample('Recovered',[3]));await ready();await page.locator('#clear').click();assert(await page.locator('#results').isHidden());assert(await page.locator('#error').isHidden());assert.equal(await page.locator('#climate-file').inputValue(),'');assert.equal(await page.locator('#room').textContent(),'');count++;
 const storage=await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length}));assert.deepEqual(storage,{local:0,session:0});assert.deepEqual(network,[]);count++;
 await page.reload();await page.waitForFunction(()=>!document.querySelector('#climate-file').disabled);assert(await page.locator('#results').isHidden());assert.equal(await page.locator('#climate-file').inputValue(),'');count++;
 // The real FileReader still reads each supplied file. Only delivery of its
 // completion is delayed, with transport cancellation deliberately ignored.
 const delayed=await browser.newContext();await delayed.addInitScript(()=>{
  const Native=FileReader;
  globalThis.FileReader=class {
   static EMPTY=0;static LOADING=1;static DONE=2;
   constructor(){this.readyState=0;this.result=null;this.native=new Native();}
   readAsArrayBuffer(file){this.readyState=1;this.native.onload=()=>{const result=this.native.result;setTimeout(()=>{this.readyState=2;this.result=result;if(file.name==='unreadable.json')this.onerror?.(new Event('error'));else this.onload?.(new Event('load'));},file.name.startsWith('slow')?350:20);};this.native.onerror=()=>this.onerror?.(new Event('error'));this.native.readAsArrayBuffer(file);}
   abort(){/* Deliberately uncooperative completion; application generation must win. */}
  };
 });
 const late=await delayed.newPage();late.on('pageerror',error=>errors.push(error.message));await late.goto(url);await late.waitForFunction(()=>!document.querySelector('#climate-file').disabled);
 const upload=(name,room)=>late.locator('#climate-file').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(sample(room,[4,8]))});
 await upload('slow-clear.json','Old clear result');await late.locator('#clear').click();await late.waitForTimeout(500);assert(await late.locator('#results').isHidden());assert.equal(await late.locator('#room').textContent(),'');assert(await late.locator('#error').isHidden());count++;
 await upload('slow-old.json','Old result');await upload('new.json','Newest result');await late.locator('#results').waitFor({state:'visible'});assert.equal(await late.locator('#room').textContent(),'Newest result');await late.waitForTimeout(500);assert.equal(await late.locator('#room').textContent(),'Newest result');count++;
 await upload('unreadable.json','PRIVATE_SOURCE_DATA');await late.locator('#error').waitFor({state:'visible'});assert.equal(await late.locator('#climate-file').inputValue(),'');assert.doesNotMatch(await late.locator('#error').innerText(),/PRIVATE_SOURCE_DATA/);await upload('recovery.json','Recovered after IO');await late.locator('#results').waitFor({state:'visible'});assert.equal(await late.locator('#room').textContent(),'Recovered after IO');count++;await delayed.close();
 // A different prerequisite: delay the actual app script before initialization.
 let release;const gate=new Promise(resolve=>release=resolve);
 const server=http.createServer(async(req,res)=>{const asset={'/':'index.html','/app.js':'app.js','/climate.js':'climate.js','/styles.css':'styles.css'}[req.url];if(!asset){res.writeHead(404);res.end();return;}if(asset==='app.js')await gate;res.setHeader('Content-Type',asset.endsWith('.js')?'text/javascript':asset.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync('/work/source/'+asset));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const cold=await browser.newPage();
 try{await cold.goto(`http://127.0.0.1:${server.address().port}/`,{waitUntil:'commit'});await cold.locator('#climate-file').waitFor({state:'visible'});assert(await cold.locator('#climate-file').isDisabled());assert(await cold.locator('#clear').isDisabled());release();await cold.waitForFunction(()=>!document.querySelector('#climate-file').disabled);count++;}
 finally{release();await cold.close();await new Promise(resolve=>server.close(resolve));}
 assert.deepEqual(errors,[]);console.log('INDEPENDENT_FILE_VIEWER_PASSED',count);
}finally{await browser.close();}
