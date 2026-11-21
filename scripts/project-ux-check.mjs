// Read-only rendering audit of a saved project. Jobs and project writes are
// stubbed so inspecting a captured client project cannot trigger native work.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';

const [url,file]=process.argv.slice(2);
if(!url||!file)throw Error('Supply a local app URL and an exported project JSON.');
const dir=process.env.UX_EVIDENCE||'/tmp/atmem-project-ux';
fs.mkdirSync(dir,{recursive:true});
const browser=await chromium.launch({channel:'chrome'}),results=[];
try{
 for(const width of [1512,390]){
  const page=await browser.newPage({viewport:{width,height:945}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/projects/save',r=>r.fulfill({json:{saved:true,sha256:'a'.repeat(64)}}));
  await page.route('**/api/engineering/**',r=>r.fulfill({json:{sessions:[],artifacts:[],artifact:null,canPackage:false,checks:[]}}));
  await page.goto(url);
  await page.locator('#project-file-input').setInputFiles(file);
  await page.waitForTimeout(700);
  const stages=page.getByRole('tablist',{name:'Project stages'});
  const tabs=stages.getByRole('tab');
  assert.equal(await tabs.count(),5);
  const bounds=await tabs.evaluateAll(ns=>ns.map(n=>({name:n.textContent,selected:n.getAttribute('aria-selected'),left:n.getBoundingClientRect().left,right:n.getBoundingClientRect().right})));
  assert.ok(bounds.every(r=>r.left>=0&&r.right<=width),'Every stage must fit the viewport');
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  for(const section of ['Overview','Traceability','Scenarios']){
   if(section!=='Overview')await page.getByRole('button',{name:section,exact:true}).click();
   if(section==='Scenarios')await page.locator('.project-overview details summary').first().click();
   await page.screenshot({path:path.join(dir,`${width}-${section}.png`)});
   fs.writeFileSync(path.join(dir,`${width}-${section}.txt`),await page.locator('body').innerText());
  }
  for(const stage of ['Board','Requirements','Choices','Review','Delivery']){
   await tabs.filter({hasText:stage}).click();await page.waitForTimeout(700);
   assert.equal(await tabs.evaluateAll(ns=>ns.filter(n=>n.getAttribute('aria-selected')==='true').length),1);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width,stage+' overflow');
   const unnamed=await page.locator('button:visible').evaluateAll(ns=>ns.filter(n=>!n.textContent.trim()&&!n.getAttribute('aria-label')&&!n.title).length);
   assert.equal(unnamed,0,stage+' accessible control names');
   if(stage==='Board'){
    const overlay=await page.locator('.drawing-board>.board-overlays').boundingBox();
    for(const name of ['Undo','Redo','Zoom in','Zoom out','Fit']){
     const button=await page.locator('.board-controls').getByRole('button',{name,exact:true}).boundingBox();
     assert.ok(button&&button.y>=overlay.y&&button.y+button.height<=overlay.y+overlay.height+1,name+' must be inside the visible toolbar');
    }
    if(width===390){
     assert.ok(overlay.height<210,'Mobile tools must leave room for the drawing');
     await page.getByRole('button',{name:'More actions',exact:true}).click();
     assert.equal(await page.getByRole('button',{name:'Reset board and context',exact:true}).isVisible(),true);
     await page.getByRole('button',{name:'Fewer actions',exact:true}).click();
    }
   }
   if(stage==='Review'){
    const cases=page.getByRole('button').filter({hasText:'Test definitions'});
    assert.match(await cases.innerText(),/Execution not recorded/);
    const contracts=page.locator('.handoff-review>details').filter({hasText:'Contracts requiring review'});
    if(await contracts.count()){
     await contracts.locator('summary').click();await contracts.getByRole('button').first().click();
     assert.notEqual(await page.getByLabel('Search handoff records').inputValue(),'');
     assert.ok(await page.locator('.handoff-records>details').count()>0,'Named contract link must open its record');
    }
    await cases.click();assert.equal(await page.getByLabel('Search handoff records').inputValue(),'');
    await page.getByRole('button').filter({hasText:'catalogue types with content'}).click();
   }
   await page.screenshot({path:path.join(dir,`${width}-${stage}.png`)});
   fs.writeFileSync(path.join(dir,`${width}-${stage}.txt`),await page.locator('body').innerText());
  }
  assert.deepEqual(errors,[]);
  results.push({width,project:path.basename(file),stages:5,allStageLabelsFit:true,oneSelectedStage:true,overflow:false,unnamedButtons:0,pageErrors:errors.length});
  await page.close();
 }
}finally{await browser.close();fs.writeFileSync(path.join(dir,'project-ux-results.json'),JSON.stringify(results,null,2));}
console.log(JSON.stringify(results));
