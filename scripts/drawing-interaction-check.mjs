import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {toProjectFile} from '../src/project-file.mjs';
const[url,file]=process.argv.slice(2),dir=process.env.INTERACTION_EVIDENCE||'/tmp/atmem-drawing-interaction';fs.mkdirSync(dir,{recursive:true});
const browser=await chromium.launch({channel:'chrome'}),results=[],errors=[];let saved;
try{
 const page=await browser.newPage({viewport:{width:1512,height:945}});page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/projects/save',r=>{saved=r.request().postDataJSON().file;return r.fulfill({json:{saved:true,sha256:'a'.repeat(64)}});});
 await page.route('**/api/engineering/**',r=>r.fulfill({json:{sessions:[],artifacts:[],checks:[]}}));
 await page.goto(url);await page.locator('#project-file-input').setInputFiles(file);
 await page.getByRole('tablist',{name:'Project stages'}).getByRole('tab',{name:'Board',exact:true}).click();
 for(const key of ['view/AViewcontext','view/AViewsequence','system/ComponentOverview','system/Sequence0','engineering/ViewExecution','board']){
  await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption(key);await page.waitForTimeout(350);
  const canvas=page.locator('.drawio-canvas:visible').last();
  const focus=page.getByLabel('Focus diagram element').filter({visible:true});
  const first=await focus.locator('option').nth(1).getAttribute('value');await focus.selectOption(first);await page.waitForTimeout(200);
  const shape=canvas.locator('[data-cell-kind=vertex][role=button]').filter({has:page.locator(':scope')});
  const target=canvas.locator(`[data-cell-kind=vertex][data-record-id="${first}"]`),before=await target.boundingBox();
  await page.mouse.move(before.x+before.width/2,before.y+before.height/2);await page.mouse.down();await page.mouse.move(before.x+before.width/2+70,before.y+before.height/2+35,{steps:8});await page.mouse.up();await page.waitForTimeout(300);
  const after=await target.boundingBox();assert.ok(after.x>before.x+40&&after.y>before.y+15,key+' drag moves the selected cell');
  // Exercise actual native handles as well as the accessible numeric controls.
  const resize=await canvas.locator('[data-transform-handle=resize-7]').boundingBox();assert.ok(resize,key+' resize handle');
  await page.mouse.move(resize.x+resize.width/2,resize.y+resize.height/2);await page.mouse.down();await page.mouse.move(resize.x+resize.width/2+50,resize.y+resize.height/2+30,{steps:6});await page.mouse.up();await page.waitForTimeout(180);
  const resized=await target.boundingBox();assert.ok(resized.width>after.width+30,key+' native resize handle changes geometry');
  const rotate=await canvas.locator('[data-transform-handle=rotate]').boundingBox();assert.ok(rotate,key+' rotation handle');
  await page.mouse.move(rotate.x+rotate.width/2,rotate.y+rotate.height/2);await page.mouse.down();await page.mouse.move(rotate.x+rotate.width/2+70,rotate.y+rotate.height/2+40,{steps:6});await page.mouse.up();await page.waitForTimeout(180);
  const rotated=await page.evaluate(()=>Object.values(localStorage).flatMap(v=>{try{return[JSON.parse(v)];}catch{return[];}}).find(p=>p?.extensions?.drawingLayouts&&p.nodes));
  assert.ok(rotated?.extensions?.drawingLayouts?.pages?.[key==='board'?await canvas.getAttribute('data-layout-key'):key]?.[first]?.rotation>0,key+' native rotation is persisted');
  const transforms=page.locator('.drawio-surface:visible').last().locator('.diagram-transform');await transforms.locator('summary').click();
  await transforms.getByLabel('Element width').fill('320');await transforms.getByLabel('Element height').fill('150');await transforms.getByLabel('Element rotation').fill('30');await transforms.getByRole('button',{name:'Apply transform'}).click();await page.waitForTimeout(300);
  // Save through the app, then inspect its serialized project rather than local native state.
  const save=page.getByRole('button',{name:/^Save project$|^Save$/}).filter({visible:true}).first();if(await save.count())await save.click();
  await page.waitForTimeout(250);
  const browserProject=await page.evaluate(()=>Object.values(localStorage).flatMap(v=>{try{return[JSON.parse(v)];}catch{return[];}}).find(p=>p?.extensions?.drawingLayouts&&p.nodes));
  if(browserProject)saved=toProjectFile(browserProject);
  const storedKey=key==='board'?await canvas.getAttribute('data-layout-key'):key;
  const geometry=saved?.extensions?.drawingLayouts?.pages?.[storedKey]?.[first];assert.ok(geometry,key+' geometry serialized');assert.equal(geometry.width,320);assert.equal(geometry.height,150);assert.equal(geometry.rotation,30);
  await transforms.locator('summary').click();
  const panBefore=await target.boundingBox(),box=await canvas.boundingBox();
  await page.mouse.move(box.x+box.width*.55,box.y+box.height*.6);await page.mouse.down({button:'middle'});await page.mouse.move(box.x+box.width*.55+80,box.y+box.height*.6+40,{steps:6});await page.mouse.up({button:'middle'});await page.waitForTimeout(100);
  const panAfter=await target.boundingBox();assert.ok(Math.abs(panAfter.x-panBefore.x-80)<3&&Math.abs(panAfter.y-panBefore.y-40)<3,key+' middle mouse pans the viewport');
  const spaceBefore=await target.boundingBox();await canvas.focus();await page.keyboard.down('Space');
  await page.mouse.move(spaceBefore.x+spaceBefore.width/2,spaceBefore.y+spaceBefore.height/2);await page.mouse.down();await page.mouse.move(spaceBefore.x+spaceBefore.width/2+40,spaceBefore.y+spaceBefore.height/2-20,{steps:5});await page.mouse.up();await page.keyboard.up('Space');
  const spaceAfter=await target.boundingBox();assert.ok(Math.abs(spaceAfter.x-spaceBefore.x-40)<3&&Math.abs(spaceAfter.y-spaceBefore.y+20)<3,key+' Space drag pans over an element');
  await page.screenshot({path:dir+'/'+key.replaceAll('/','-')+'.png'});
  results.push({page:key,drag:true,resize:true,rotate:true,middlePan:true,spacePan:true,nativeResizeHandle:true,nativeRotationHandle:true,persistedGeometry:geometry});
 }
 fs.writeFileSync(dir+'/edited-project.json',JSON.stringify(saved,null,2));assert.deepEqual(errors,[]);
 // A fresh import must retain all four page layouts.
 await page.reload();await page.locator('#project-file-input').setInputFiles(dir+'/edited-project.json');
 await page.getByRole('tablist',{name:'Project stages'}).getByRole('tab',{name:'Board',exact:true}).click();
 await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption('view/AViewcontext');await page.waitForTimeout(300);
 const reopened=page.getByLabel('Focus diagram element').filter({visible:true});await reopened.selectOption('Asystemwcs');
 const properties=page.locator('.drawio-surface:visible').last().locator('.diagram-transform');await properties.locator('summary').click();assert.equal(await properties.getByLabel('Element width').inputValue(),'320');assert.equal(await properties.getByLabel('Element height').inputValue(),'150');assert.equal(await properties.getByLabel('Element rotation').inputValue(),'30');
 const retained=await page.locator('.drawio-canvas:visible').last().locator('[data-cell-kind=vertex]').first().getAttribute('data-record-id');assert.ok(retained);
}finally{await browser.close();fs.writeFileSync(dir+'/results.json',JSON.stringify({results,errors},null,2));}
console.log(JSON.stringify({results,errors,evidence:dir}));
