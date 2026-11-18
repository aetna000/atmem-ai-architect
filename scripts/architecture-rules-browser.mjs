// Actual Architect UI -> authenticated backend -> pinned AtMem SDK -> reviewer.
// Run against an owned local installation; no model or cloud deployment calls.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import {template} from '../src/core.mjs';
const base=process.env.ATMEM_RULES_URL||'http://127.0.0.1:5197';
const out=process.env.ATMEM_RULES_EVIDENCE||'.local/review-hook';
const project={...template('aws'),id:randomUUID(),createdAt:new Date().toISOString(),name:'Native rules qualification'};
project.nodes=project.nodes.slice(0,1);project.edges=[];
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[],modelCalls=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/\/api\/architect$|\/engineering\/(create|start|steer)$/.test(r.url()))modelCalls.push(r.url());});
 await page.addInitScript(p=>localStorage.setItem('atforma-workspace-v3',JSON.stringify(p)),project);
 await page.goto(base);await page.getByRole('tab',{name:'Review',exact:true}).click();
 const panel=page.getByRole('region',{name:'Architecture rules',exact:true});await panel.waitFor();
 const save=panel.getByRole('button',{name:'Save rules to AtMem',exact:true});await save.waitFor();
 await page.waitForResponse(r=>r.url().endsWith('/api/memory/architecture/status')&&r.status()===200,{timeout:30000});
 await save.click();await panel.getByText(/Approved [a-f0-9]{8}/).waitFor();
 const run=panel.getByRole('button',{name:'Review design against rules',exact:true});await run.click();
 await panel.getByRole('status').filter({hasText:'Passed'}).waitFor({timeout:30000});
 assert.equal(await panel.getByRole('list',{name:'Rules review activity'}).getByRole('listitem').count(),4);
 await panel.getByText('Edit rules',{exact:true}).click();
 await panel.getByRole('button',{name:'More rule options',exact:true}).click();
 const editor=panel.getByRole('textbox',{name:'Architecture policy',exact:true});
 const approved=await editor.inputValue();await editor.fill(approved.replace('"must_equal": true','"must_equal": false'));
 await save.click();await run.click();await panel.getByRole('status').filter({hasText:'Blocked'}).waitFor({timeout:30000});
 await panel.getByText('PRIVATE-STORAGE',{exact:true}).waitFor();
 await page.screenshot({path:out+'/native-rules-blocked.png',fullPage:true});
 // The same screen restores exact policy and history from AtMem after reopening.
 await page.reload();await page.getByRole('tab',{name:'Review',exact:true}).click();
 await panel.getByRole('status').filter({hasText:'Blocked'}).waitFor({timeout:30000});
 await panel.getByText('Edit rules',{exact:true}).click();await editor.fill(approved);await save.click();await run.click();
 await panel.getByRole('status').filter({hasText:'Passed'}).waitFor({timeout:30000});
 // A second editor changes the approved policy while this editor has a draft.
 // Polling must not replace the draft's original compare-and-swap revision.
 await panel.getByRole('button',{name:'More rule options',exact:true}).click();
 await editor.fill(approved.replace('"must_equal": true','"must_equal": false'));
 const concurrent=await page.evaluate(async({id,content})=>{const session=await(await fetch('/api/session')).json();const headers={'Content-Type':'application/json',Authorization:'Bearer '+session.token};const current=await(await fetch('/api/memory/architecture/status',{method:'POST',headers,body:JSON.stringify({projectId:id})})).json();const response=await fetch('/api/memory/architecture/rules',{method:'POST',headers,body:JSON.stringify({projectId:id,content,expectedRevision:current.policy.revision})});if(!response.ok)throw Error('Concurrent fixture edit was rejected');return response.json();},{id:project.id,content:approved+'\nConcurrent editor recorded this revision.\n'});
 await panel.getByText(new RegExp('Approved '+concurrent.revision.slice(0,8))).waitFor();
 await save.click();await panel.getByRole('alert').filter({hasText:'Rules changed.'}).waitFor();
 await panel.getByRole('button',{name:'Reload saved rules',exact:true}).click();await editor.fill(approved);await save.click();await run.click();
 await panel.getByRole('status').filter({hasText:'Passed'}).waitFor({timeout:30000});
 await page.setViewportSize({width:390,height:844});
 assert.ok(await panel.evaluate(el=>el.getBoundingClientRect().width)<=390);
 await run.scrollIntoViewIfNeeded();
 const buttonBox=await run.boundingBox();assert.ok(buttonBox&&buttonBox.y>=0&&buttonBox.y+buttonBox.height<=844);
 await page.screenshot({path:out+'/native-rules-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);assert.deepEqual(modelCalls,[]);
 await fs.writeFile(out+'/native-browser.json',JSON.stringify({status:'passed',transport:'real_browser_backend_atmem_reviewer',policyRoundtrip:true,passThenFailThenPass:true,persistedAfterReload:true,concurrentEditRejected:true,mobileWidth:390,modelCalls:0,cloudDeployment:false},null,2)+'\n');
 console.log('Native rules browser qualification passed.');
}finally{await browser.close();}
