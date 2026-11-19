import {verifyReceivingCapture} from './receiving-capture.mjs';
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {chromium} from '@playwright/test';import {unzipSync,strFromU8} from 'fflate';import {toProjectFile} from '../src/project-file.mjs';import {relativeLinkReport} from './receiving-links.mjs';
const [sourceFile]=process.argv.slice(2);if(!sourceFile)throw Error('Usage: project-evidence-check.mjs <saved-design.json>');
const raw=JSON.parse(fs.readFileSync(sourceFile)),file=raw.format?raw:toProjectFile(raw),output=process.env.ATMEM_PROJECT_EVIDENCE_OUTPUT||'.local/project-evidence-check';fs.mkdirSync(output,{recursive:true});
const hash=bytes=>createHash('sha256').update(bytes).digest('hex'),browser=await chromium.launch();let starts=0,page;const observations=[];
try{
 page=await browser.newPage({viewport:{width:1500,height:1050}});const errors=[];page.on('response',response=>{const path=new URL(response.url()).pathname;if(['/api/design-evidence/draft','/api/projects/save','/api/session'].includes(path))observations.push({path,status:response.status()});});page.on('pageerror',error=>errors.push(error.message));
 const engineeringUnavailable=process.env.ATMEM_ENGINEERING_UNAVAILABLE==='1';
 await page.route('**/api/engineering/**',route=>{
  const action=new URL(route.request().url()).pathname;
  if(/\/(start|steer|work-orders\/block)$/.test(action)){starts++;return route.abort();}
  return engineeringUnavailable?route.fulfill({status:503,json:{detail:'Engineering service unavailable for the export-independence probe.'}}):route.continue();
 });
 await page.goto(process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5207');await page.locator('#project-file-input').setInputFiles({name:'project.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});
 await page.waitForFunction(id=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').id===id,file.meta.id);
 await page.getByRole('tab',{name:'Delivery',exact:true}).click();const button=page.getByRole('button',{name:'Download project ZIP',exact:true});await button.waitFor({timeout:60000});
 const pending=page.waitForEvent('download',{timeout:120000});await button.click();const download=await Promise.race([pending,page.getByRole('region',{name:'Outputs',exact:true}).getByRole('alert').waitFor({timeout:120000}).then(async()=>{throw Error(await page.getByRole('region',{name:'Outputs',exact:true}).getByRole('alert').innerText());})]);await download.saveAs(path.join(output,'project.zip'));
 const archive=unzipSync(fs.readFileSync(await download.path())),prefix=archive['design-documents/manifest.json']?'design-documents/':'',files=Object.fromEntries(Object.entries(archive).filter(([name])=>name.startsWith(prefix)).map(([name,body])=>[name.slice(prefix.length),body]));
 const projectManifest=JSON.parse(strFromU8(files['manifest.json']));for(const [name,receipt]of Object.entries(projectManifest.fileDigests)){assert.equal(hash(files[name]),receipt.sha256);assert.equal(files[name].length,receipt.bytes);}
 const evidence=JSON.parse(strFromU8(files['design-evidence.json']));assert.equal(evidence.status,'verified');assert.equal(hash(files['architecture.canvas.json']),file.extensions.architectureDocuments.draftSha256);assert.equal(evidence.contextSha256,file.extensions.architectureDocuments.contextSha256);
 const authored=JSON.parse(strFromU8(files['design-documents-receipt.json']));for(const item of authored.files){assert.ok(files[item.exportPath]);assert.equal(hash(files[item.exportPath]),item.sha256);}
 const capturedEvidence=verifyReceivingCapture(files,file.extensions.architectureDocuments);
 const links=relativeLinkReport(files);assert.deepEqual(links.missing,[]);
 let sourceImages=0;const expected=(file.extensions.designSources||[]).flatMap(source=>(source.figureEvidence?.figures||[]).filter(figure=>figure.status==='available').map(figure=>({source,figure})));
 if(expected.length){const images=JSON.parse(strFromU8(files['source-figures.json']));assert.equal(images.complete,true);for(const {source,figure}of expected){const row=images.figures.find(row=>row.sourceSha256===source.sha256&&row.id===figure.id);assert.equal(row.exportStatus,'verified');assert.equal(hash(files[row.path]),figure.sha256);sourceImages++;}}
 const contents=archive['package-contents.json']?JSON.parse(strFromU8(archive['package-contents.json'])):null;
 if(contents)for(const row of contents.documents){assert.equal(hash(archive[row.path]),row.sha256);assert.equal(archive[row.path].length,row.bytes);}
 assert.equal(starts,0);assert.deepEqual(errors,[]);
 await page.screenshot({path:path.join(output,'delivery.png')});
 const snapshot=files['project.atmem-ai-architect.json'];assert.ok(snapshot,'Whole-project editable snapshot is present');
 const replay=engineeringUnavailable?Promise.resolve():page.waitForResponse(async response=>{if(!response.url().endsWith('/api/engineering/events'))return false;try{return (await response.json()).events?.some(event=>event.artifactId===file.extensions.architectureDocuments.artifactId&&event.kind.startsWith('finalization_'));}catch{return false;}},{timeout:60000});
 await page.reload();await replay;
 await page.locator('#project-file-input').setInputFiles({name:'downloaded.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(snapshot)});
 await page.getByText('Project opened.',{exact:true}).waitFor();
 await page.waitForFunction(({id,revision})=>{const p=JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}');return p.id===id&&p.revision===revision;},{id:file.meta.id,revision:file.meta.revision});
 await page.getByRole('tab',{name:'Review',exact:true}).click();await page.waitForTimeout(300);
 if(!engineeringUnavailable)assert.equal(await page.locator('.review-generation .engineering-error').count(),0,'An already applied draft must reopen without spurious assessment errors');
 assert.equal(starts,0);assert.deepEqual(errors,[]);await page.screenshot({path:path.join(output,'reopened-review.png')});
 const receipt={projectId:file.meta.id,documentPrefix:prefix,projectFiles:Object.keys(files).length,projectFileDigestsVerified:Object.keys(projectManifest.fileDigests).length,combinedFileDigestsVerified:contents?.documents.length||0,authoredDocumentsVerified:authored.files.length,relativeLinksVerified:links.checked,reviewedDraftSha256:evidence.draftSha256,capturedEvidence,sourceImagesVerified:sourceImages,implementationStarts:starts,engineeringUnavailableSimulated:engineeringUnavailable,implementationExecuted:false,deploymentExecuted:false,projectReopened:true};fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt,null,2));
}catch(error){if(page){await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});const state=await page.evaluate(()=>({text:document.querySelector('.outputs-view')?.innerText||document.body.innerText,projectId:JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').id})).catch(()=>null);fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({message:error.message,observations,state},null,2)+'\n');}throw error;}finally{await browser.close();}
