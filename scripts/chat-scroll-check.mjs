// Fixture model/session: exercise real scrolling without spending model calls.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium} from '@playwright/test';
const browser=await chromium.launch({...(process.env.ATMEM_ARCHITECT_BROWSER_BIN?{executablePath:process.env.ATMEM_ARCHITECT_BROWSER_BIN}:{})});
try{
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:900},reducedMotion:process.env.ATMEM_ARCHITECT_REDUCED_MOTION||'no-preference'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'claude-code',model:'default'})));
  let resolveRequest;let request=new Promise(r=>resolveRequest=r);
  await page.route('**/api/**',route=>{
   const url=route.request().url();
   if(url.endsWith('/api/architect')){resolveRequest(route);return;}
   return route.fulfill({json:url.endsWith('/api/session')?{token:'fixture',status:'local-sidecar',providers:{'claude-code':{installed:true,available:true,signedIn:true}}}:{status:'disabled',projects:[],bin:[],models:[],saved:true}});
  });
  await page.goto(process.env.ATMEM_ARCHITECT_BROWSER_URL||'http://127.0.0.1:5190');
  const fixture=JSON.parse(fs.readFileSync('tests/fixtures/generator/architect-website-r13.json'));
  fixture.extensions={conversation:{version:1,messages:Array.from({length:24},(_,i)=>({role:i%2?'user':'assistant',text:`Earlier message ${i}. `+'Architecture context to read. '.repeat(15)}))}};
  await page.locator('#project-file-input').setInputFiles({name:'scroll-fixture.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture))});
  const pane=page.locator('.messages');await page.waitForFunction(()=>{const p=document.querySelector('.messages');return p&&p.scrollHeight>p.clientHeight+100&&p.scrollHeight-p.clientHeight-p.scrollTop<2});
  await page.getByRole('textbox',{name:'Your message'}).fill('Please explain the implementation.');await page.getByRole('button',{name:'Send message',exact:true}).click();let route=await request;
  await pane.hover();await page.mouse.wheel(0,-600);await page.waitForTimeout(150);
  const before=await pane.evaluate(p=>({top:p.scrollTop,page:window.scrollY}));
  const reply='Response while reading older messages. '+'More architecture details. '.repeat(90);
  await route.fulfill({json:{message:reply,phase:'Design',proposal:null}});await page.getByText(reply,{exact:true}).waitFor({state:'attached'});await page.waitForTimeout(150);
  const after=await pane.evaluate(p=>({top:p.scrollTop,page:window.scrollY}));assert.ok(Math.abs(before.top-after.top)<2,JSON.stringify({width,before,after}));assert.ok(Math.abs(before.page-after.page)<2,'Reply scrolled the surrounding page');
  await pane.evaluate(p=>{p.scrollTop=p.scrollHeight;p.dispatchEvent(new Event('scroll'));});
  request=new Promise(r=>resolveRequest=r);
  await page.getByRole('textbox',{name:'Your message'}).fill('Continue with the next step.');await page.getByRole('button',{name:'Send message',exact:true}).click();route=await request;
  const pageY=await page.evaluate(()=>window.scrollY);
  await route.fulfill({json:{message:'Latest response. '+'New details. '.repeat(90),phase:'Design',proposal:null}});
  await page.waitForFunction(()=>{const p=document.querySelector('.messages');return !document.querySelector('.working')&&p.scrollHeight-p.clientHeight-p.scrollTop<2});
  assert.ok(Math.abs(pageY-await page.evaluate(()=>window.scrollY))<2,'Following a response scrolled the page');
  await pane.evaluate(p=>{const late=document.createElement('div');late.style.height='140px';p.querySelector('.message-list').append(late);});
  await page.waitForFunction(()=>{const p=document.querySelector('.messages');return p.scrollHeight-p.clientHeight-p.scrollTop<2});
  assert.deepEqual(errors,[]);console.log(width,'reader position preserved; new messages and late layout stay pinned locally; page stays still');await page.close();
 }
}finally{await browser.close()}
