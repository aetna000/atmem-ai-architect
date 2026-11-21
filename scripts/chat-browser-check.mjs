// Isolated browser: real paste/upload/formatting UI; fixture model transport.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
const out=path.resolve('.local/chat-validation');fs.mkdirSync(out,{recursive:true});
const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));
const base=`http://127.0.0.1:${port}`,server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});let browser;
try{
 for(let i=0;i<100;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});const page=await context.newPage();const errors=[],sent=[];page.on('pageerror',e=>errors.push(e.message));
 const fixture=await context.newPage();await fixture.setContent('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="220"><rect width="640" height="220" fill="white"/><rect x="30" y="50" width="230" height="100" rx="12" fill="#F3A2B4"/><text x="60" y="105" font-size="30">RIVER42</text><path d="M260 100h90" stroke="black" stroke-width="4"/><rect x="350" y="50" width="250" height="100" rx="12" fill="#eeeeee"/><text x="380" y="105" font-size="26">Worker</text></svg>');const png=await fixture.locator('svg').screenshot({path:path.join(out,'vision-fixture.png')});await fixture.close();
 await page.addInitScript(()=>localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'default'})));
 await page.route('**/api/session',r=>r.fulfill({json:{token:'fixture',status:'local-sidecar',providers:{codex:{available:true,signedIn:true}}}}));
 await page.route('**/api/memory/**',r=>r.fulfill({json:{status:'disabled',enabled:false,pending:0,rejected:0,profile:[],project:[],history:[],skills:[]}}));
 await page.route('**/api/voice/prepare',r=>r.fulfill({json:{available:false}}));
 await page.route('**/api/projects/**',r=>r.fulfill({json:{projects:[],bin:[],folder:''}}));
 await page.route('**/api/architect',async r=>{const body=r.request().postDataJSON();sent.push(body);await r.fulfill({json:{message:'## What I understood\n\n**Which team will use this first?**\n\n- Support staff\n- Engineers\n\nFor example: `50 support staff`.\n\n<script>alert("not executable")</script>',proposal:null}});});
 await page.goto(base);await page.getByLabel('Your message',{exact:true}).waitFor();
 await page.locator('#chat-attachment-input').setInputFiles({name:'requirements.txt',mimeType:'text/plain',buffer:Buffer.from('Keep customer records in Australia. Monthly budget AUD 200.')});
 await page.locator('.attachment-chip').filter({hasText:'requirements.txt'}).waitFor();
 await page.evaluate(async data=>{const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));await navigator.clipboard.write([new ClipboardItem({'image/png':new Blob([bytes],{type:'image/png'})})]);},png.toString('base64'));
 await page.getByLabel('Your message',{exact:true}).focus();await page.keyboard.press('ControlOrMeta+v');
 await page.waitForFunction(()=>document.querySelectorAll('.attachment-chip').length===2);
 assert.equal(sent.length,0,'attachments do not auto-send');
 await page.getByLabel('Your message',{exact:true}).fill('Review the diagram and requirements.');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await page.getByRole('heading',{name:'What I understood',exact:true}).waitFor();await page.locator('.msg.user').filter({hasText:'Review the diagram and requirements.'}).waitFor();
 const bubble=page.locator('.msg.user').first();assert.equal(await bubble.evaluate(el=>getComputedStyle(el).color),'rgb(23, 32, 51)');assert.equal(await bubble.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(252, 236, 240)');assert.equal(sent.length,1);assert.equal(sent[0].attachments.length,2);assert.equal(sent[0].attachments[0].data,Buffer.from('Keep customer records in Australia. Monthly budget AUD 200.').toString('base64'));assert.equal(sent[0].attachments[1].mime,'image/png');
 assert.equal(await page.locator('.attachment-chip').count(),0);assert.equal(await page.locator('.chat-markdown script').count(),0);assert.equal(await page.locator('.msg.assistant .chat-markdown li').count(),2);assert.ok(await page.locator('.msg.assistant .chat-markdown strong').count());
 assert.ok(!JSON.stringify(await page.evaluate(()=>({...localStorage}))).includes(png.toString('base64')),'image bytes are not persisted');
 await page.getByLabel('Your message',{exact:true}).fill('Text-only follow up');await page.getByRole('button',{name:'Send message',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.msg.assistant h4').length===2);assert.ok(!('attachments' in sent[1]),'text-only request remains backward compatible');
 await page.reload();await page.locator('.msg.user').filter({hasText:'Text-only follow up'}).waitFor();assert.equal(await page.locator('.msg.assistant h4').count(),2);assert.equal(await page.locator('.sent-attachments figcaption').count(),2);
 for(const width of [1440,390]){await page.setViewportSize({width,height:1000});const text=await page.getByLabel('Your message',{exact:true}).boundingBox();for(const name of ['Send message','Start dictation','Attach images or documents']){const box=await page.getByRole('button',{name,exact:true}).boundingBox();assert.ok(box.y>=text.y+text.height,`${name} cannot overlap the text field`);}assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,`chat-${width}.png`),fullPage:true});}
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'Projects',exact:true}).click();const close=await page.getByRole('button',{name:'Close dialog',exact:true}).boundingBox();const fresh=await page.getByRole('dialog').getByRole('button',{name:'New project',exact:true}).boundingBox();assert.ok(close.y+close.height<=fresh.y||close.x+close.width<=fresh.x||fresh.x+fresh.width<=close.x,'close does not overlap New project');await page.screenshot({path:path.join(out,'projects-dialog.png')});
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({status:'passed',paste:'native clipboard Ctrl/Meta+V',upload:'document and image',formatting:true,noOverlap:true,transport:'fixture model; image content tested separately'},null,2));console.log('Chat passed: native image paste, document upload, explicit Send, multimodal request, safe Markdown, text-only compatibility, conversation restored after reload (no attachment bytes), mobile control spacing and dialog close spacing.');
}finally{await browser?.close();server.kill('SIGTERM');}
