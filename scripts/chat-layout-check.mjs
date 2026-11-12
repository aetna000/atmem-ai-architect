import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
import assert from 'node:assert/strict';
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));const base=process.env.ATMEM_UI_BASE||`http://127.0.0.1:${port}`;
const server=process.env.ATMEM_UI_BASE?null:spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 for(let i=0;i<60;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(12000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'fixture',effort:'high'})));
 let releaseAnswer;const pending=new Promise(r=>releaseAnswer=r);
 await page.route('**/api/**',async route=>{const url=route.request().url();if(url.endsWith('/api/architect')){await pending;return route.fulfill({json:{message:'I have received your design request. We can use your existing catalogue and preserve its records. Which actions need a person to approve them first?',contextUsed:[]}});}return route.fulfill({json:url.endsWith('/session')?{token:'fixture',status:'local-sidecar',architectureActivityEnabled:true,engineeringEnabled:true,providers:{codex:{installed:true,available:true,signedIn:true}}}:url.endsWith('/architect/activity')?{...route.request().postDataJSON(),id:route.request().postDataJSON().activityId,events:[],state:'running'}:{status:'disabled',enabled:false,projects:[],bin:[]}});});
 await page.goto(base);const chat=page.getByRole('complementary',{name:'Chat',exact:true});await chat.waitFor();const before=(await chat.boundingBox()).width;
 await page.getByRole('button',{name:'Widen chat',exact:true}).click();const wide=(await chat.boundingBox()).width;assert.ok(wide>before+100);
 const divider=page.getByRole('separator',{name:'Resize chat panel'});const box=await divider.boundingBox();await page.mouse.move(box.x+box.width/2,box.y+100);await page.mouse.down();await page.mouse.move(box.x+box.width/2+120,box.y+100,{steps:6});await page.mouse.up();const dragged=(await chat.boundingBox()).width;assert.ok(dragged<wide-80);
 await divider.focus();await page.keyboard.press('ArrowLeft');const keyboard=(await chat.boundingBox()).width;assert.ok(keyboard>dragged+20);
 await page.reload();await chat.waitFor();assert.ok(Math.abs((await chat.boundingBox()).width-keyboard)<2);
 await page.locator('.model .led.on').waitFor();
 await page.getByRole('textbox',{name:'Your message',exact:true}).fill('Help me design a local catalogue.');await page.getByRole('button',{name:'Send message',exact:true}).click();
 const brain=page.locator('.turn-state-icon .brain-activity.is-active');await brain.waitFor();assert.equal(await brain.evaluate(el=>getComputedStyle(el).animationName),'brain-breathe');
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await brain.evaluate(el=>getComputedStyle(el).animationName),'none');await page.emulateMedia({reducedMotion:'no-preference'});
 releaseAnswer();await page.getByText('Which actions need a person to approve them first?',{exact:true}).waitFor();assert.equal(await brain.count(),0);
 const details=page.getByRole('button',{name:'More details',exact:true});await details.waitFor();assert.equal(await details.getAttribute('aria-expanded'),'false');await details.click();const less=page.getByRole('button',{name:'Less details',exact:true});assert.equal(await less.getAttribute('aria-expanded'),'true');assert.ok(await page.getByText('I have received your design request.',{exact:false}).isVisible());assert.equal(await page.locator('.concise-answer .help-note').count(),0);await less.click();assert.equal(await details.getAttribute('aria-expanded'),'false');await page.getByRole('button',{name:'Clear chat view',exact:true}).click();assert.equal(await page.locator('.message-list .msg').count(),0);await page.getByRole('button',{name:'Restore chat history',exact:true}).click();assert.ok(await page.locator('.message-list .msg').count()>0);
 await page.setViewportSize({width:390,height:950});assert.equal(await divider.isVisible(),false);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
 console.log(JSON.stringify({base,before,wide,dragged,keyboard,persisted:true,workingBrain:true,reducedMotion:true,sendWorks:true,inlineDetails:true,clearAndRestoreChat:true,mobileNoOverflow:true,errors}));
}finally{await browser?.close();server?.kill('SIGTERM');}
