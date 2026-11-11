// Actual UI/session service; opening and drafting in Build must submit no inference.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ATMEM_ENGINEERING_PREVIEW_URL||'http://127.0.0.1:5274',out=path.resolve(process.env.ATMEM_ENGINEERING_EVIDENCE_DIR||'.local/engine-product/native-intake-no-inference');if(fs.existsSync(out))throw Error('Preserve previous evidence; select a new output.');fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true});const errors=[],mutations=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\/api\/engineering\/(create|start|steer)$/.test(r.url()))mutations.push(r.url());});
 const project={id:'native-draft-'+Date.now(),version:1,revision:1,name:'Inventory conversion',provider:'tools',requirements:'Normalize measurement units without changing the warehouse service.',nodes:[],edges:[]};
 await page.addInitScript(project=>{if(!localStorage.getItem('atforma-workspace-v3'))localStorage.setItem('atforma-workspace-v3',JSON.stringify(project));localStorage.setItem('atforma-connection-v1',JSON.stringify({provider:'codex',model:'gpt-6.1-sol',effort:'high'}));},project);
 await page.goto(base);await page.getByRole('heading',{name:'Build your project',exact:true}).waitFor();const input=page.getByLabel('What should we build or repair?',{exact:true});await input.fill('Normalize inventory units without changing the warehouse service.');await page.screenshot({path:path.join(out,'draft.png')});
 await page.getByRole('tab',{name:'Design',exact:true}).click();await page.reload();await page.getByRole('tab',{name:'Build',exact:true}).click();await input.waitFor();assert.equal(await input.inputValue(),'Normalize inventory units without changing the warehouse service.');assert.deepEqual(mutations,[]);assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({passed:true,projectId:project.id,nativeCreateStartSteerRequests:0,draftRetained:true,viewSwitchAndReload:true,cloudOperations:false,errors,boundary:'Actual browser and authenticated local session service. Build opens and preserves a draft across Design navigation/reload without native session creation or inference. Generation/policy/tools/output are qualified separately.'},null,2)+'\n');console.log('Passed actual Build/draft/reload with zero inference submissions.');
}finally{await browser.close();}
