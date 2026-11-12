// Reopen this isolated active project and observe its existing work; no inference.
import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium}from '@playwright/test';
const base='http://127.0.0.1:5298',out='.local/external-artifacts/ui-native-handoff/v1',live=JSON.parse(fs.readFileSync(out+'/live.json')),auth=await(await fetch(base+'/api/session')).json();
const response=await fetch(base+'/api/projects/get',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.token},body:JSON.stringify({id:live.projectId})});assert(response.ok);const file=await response.json();
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];let starts=0,creates=0;
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{const p=new URL(r.url()).pathname;if(p==='/api/engineering/start')starts++;if(p==='/api/engineering/create')creates++});
await page.addInitScript(()=>{localStorage.setItem('atforma-draw-live','off');localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}))});
try{
 await page.goto(base+'/');await page.locator('#project-file-input').setInputFiles({name:'existing-project.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.getByRole('tab',{name:'Implementation',exact:true}).click();
 const conversation=page.getByRole('log',{name:'Project conversation',exact:true});await conversation.getByText(/I’m using the composition skill/).waitFor();
 assert.match(await page.locator('.engineering-panel').innerText(),/gpt-6.1-sol · high/);
 await page.screenshot({path:out+'/restored-native-progress.png',fullPage:true});
 await page.reload();await page.getByRole('tab',{name:'Implementation',exact:true}).click();await conversation.getByText(/I’m using the composition skill/).waitFor();
 assert.equal(starts,0);assert.equal(creates,0);assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/restore-browser.json',JSON.stringify({projectId:live.projectId,sessionId:live.context.sessionId,starts,creates,restoredActualNativeConversation:true,reloadWithoutReplay:true,pageErrors:errors,cloudOperations:false},null,2)+'\n');
}finally{await browser.close()}
