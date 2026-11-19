// Synthetic UI mechanics, not generated architecture or execution evidence.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium}from '@playwright/test';
import {unzipSync,strFromU8}from 'fflate';
import {toProjectFile}from '../src/project-file.mjs';
const base=process.argv[2]||'http://127.0.0.1:5207',out=process.argv[3]||'.local/verification-cases-ui';fs.mkdirSync(out,{recursive:true});
const specification={id:'exclusive-slot',name:'Two clients claim one slot',category:'integration',requirementIds:['one-winner'],environment:'Local implementation with two concurrent clients.',setup:'Resource A has one unclaimed slot and an empty receipt ledger.',input:'Independent keys K1 and K2 target the same slot.',action:'Release both requests from a barrier, then read the committed schedule.',expected:'One accepted receipt, one conflict and one confirmed reservation.',evidence:'Both outcomes, receipt IDs and committed reservation rows.',operationId:'reserve-operation'};
const project={version:1,revision:1,name:'Verification case UI example',provider:'tools',nodes:[{id:'scheduler',type:'resource',position:{x:0,y:0},data:{label:'Scheduler',kind:'resource',provider:'tools',parentBlockId:'system',buildSpec:{verificationCases:[specification],scenarios:[{name:'Reserve slot',steps:[{sender:'Scheduling system',receiver:'Scheduler',action:'Reserve a slot',messageKind:'command',senderBlockId:'system',receiverBlockId:'scheduler',operationId:'reserve-operation',requirementIds:['one-winner']}]}]}}},{id:'system',type:'resource',position:{x:0,y:0},data:{label:'Scheduling system',kind:'resource',provider:'tools'}}],edges:[],needs:[{id:'one-winner',statement:'Only one request can confirm a resource slot.',links:['scheduler']}]};
project.extensions={engineeringModel:{format:'atmem.engineering-model',version:1,id:'scheduling-model',name:'Scheduling model',elements:[
 {id:'audit',name:'ReservationAudit',kind:'class',basis:'proposed',blockId:'scheduler'},
 {id:'reservation-service',name:'ReservationService',kind:'class',basis:'proposed',blockId:'scheduler',operations:[{id:'reserve-operation',name:'reserve',parameters:[],preconditions:['The requested resource slot exists.'],postconditions:['Exactly one request confirms the slot.']}]}
 ],relationships:[],diagrams:[{id:'audit-view',name:'Reservation audit',kind:'class',placements:[{elementId:'audit',x:0,y:0}],relationships:[]},{id:'operations-view',name:'Scheduler operations',kind:'class',placements:[{elementId:'reservation-service',x:900,y:1050}],relationships:[]}]}};
const file=toProjectFile(project),browser=await chromium.launch();
try{
 const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);
 await page.locator('#project-file-input').setInputFiles({name:'verification-example.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});
 await page.getByText('Project opened.',{exact:true}).waitFor();
 const tree=page.getByRole('navigation',{name:'Component tree'});if(!await tree.isVisible())await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await tree.getByRole('button',{name:'Scheduler',exact:true}).click();
 const specTab=page.getByRole('tab',{name:'Block Spec Kit',exact:true});
 const overviewTab=page.getByRole('tab',{name:'Overview',exact:true});
 const nesting=page.getByRole('combobox',{name:'Nest under',exact:true});
 assert.equal(await specTab.getAttribute('aria-selected'),'true');
 assert.ok(await page.getByRole('tabpanel',{name:'Block Spec Kit',exact:true}).isVisible());
 assert.equal(await nesting.inputValue(),'system');
 await specTab.focus();
 await specTab.press('ArrowLeft');
 assert.equal(await overviewTab.getAttribute('aria-selected'),'true');
 await page.getByLabel('Block name',{exact:true}).waitFor();
 assert.deepEqual(await nesting.locator('option').evaluateAll(options=>options.map(option=>option.value)),['','system']);
 await nesting.selectOption('');
 const hierarchy=page.getByRole('navigation',{name:'Block hierarchy'});
 assert.equal(await hierarchy.getByRole('button',{name:'Scheduling system',exact:true}).count(),0);
 await nesting.selectOption('system');
 await hierarchy.getByRole('button',{name:'Scheduling system',exact:true}).waitFor();
 await page.waitForFunction(()=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').nodes?.find(node=>node.id==='scheduler')?.data.parentBlockId==='system');
 await specTab.click();
 await page.screenshot({path:out+'/visible-spec-kit.png'});
 await page.getByRole('button',{name:'Diagrams',exact:true}).click();
 await page.getByText('Reserve slot',{exact:true}).click();
 await page.getByRole('button',{name:'Inspect operation reserve',exact:true}).click();
 const model=page.getByRole('region',{name:'Detailed engineering model'});
 await model.getByRole('img',{name:'Scheduler operations',exact:true}).waitFor();
 assert.equal(await model.getByRole('button',{name:'Inspect ReservationService',exact:true}).getAttribute('aria-pressed'),'true');
 await model.getByText('Exactly one request confirms the slot.',{exact:true}).waitFor();
 const visible=await model.locator('.engineering-model-scroll').evaluate(el=>{const selected=el.querySelector('[data-selected="true"] rect');const a=selected.getBoundingClientRect(),b=el.getBoundingClientRect();return a.left>=b.left&&a.right<=b.right&&a.top>=b.top&&a.bottom<=b.bottom;});assert.equal(visible,true,'Navigation must reveal the offscreen owning class.');
 await model.screenshot({path:out+'/operation-navigation.png'});
 await page.getByRole('button',{name:'Test cases',exact:true}).click();
 const panel=page.getByRole('region',{name:'Module verification cases'});
 await panel.getByText(specification.name+' · integration',{exact:true}).click();
 await panel.getByText(specification.expected,{exact:true}).waitFor();
 assert.match(await panel.innerText(),/Execution not run/);
 await panel.screenshot({path:out+'/specified-case.png'});
 await page.getByRole('button',{name:'Prepare agent handoff',exact:true}).click();
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();const download=await pending;await download.saveAs(out+'/handoff.zip');
 const files=unzipSync(fs.readFileSync(out+'/handoff.zip')),key=Object.keys(files).find(name=>name.endsWith('/verification-cases.json'));assert.ok(key);
 const cases=JSON.parse(strFromU8(files[key]));assert.equal(cases.execution,'not_run');assert.deepEqual(cases.cases,[specification]);const scenarios=Object.keys(files).find(name=>name.endsWith('/scenarios.md'));assert.match(strFromU8(files[scenarios]),/1\. reserve-operation/);assert.deepEqual(errors,[]);
 console.log('Specified case rendered with exact expected outcomes; normal module download retains the case and not_run execution status. Linked scenario operation opened the owning class in another view and expanded its postconditions. Synthetic fixture.');
}finally{await browser.close();}
