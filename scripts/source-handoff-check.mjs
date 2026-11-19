import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';
import {unzipSync,strFromU8} from 'fflate';
import {toProjectFile} from '../src/project-file.mjs';
// Real local service and retained evidence. No inference, commands, cloud or deployment.
const [file,blockId]=process.argv.slice(2);
if(!file||!blockId)throw Error('Usage: source-handoff-check.mjs <saved-design.json> <block-id>');
const raw=JSON.parse(fs.readFileSync(file)),projectFile=raw.format?raw:toProjectFile(raw);
const node=projectFile.design.nodes.find(node=>node.id===blockId);assert.ok(node);
const expected=(projectFile.extensions?.designSources||[]).flatMap(source=>(source.figureEvidence?.figures||[]).map(figure=>({source,figure}))).filter(({figure})=>figure.status==='available');
assert.ok(expected.length,'Acceptance requires retained source images');
const output=process.env.ATMEM_SOURCE_HANDOFF_OUTPUT||'.local/source-handoff-acceptance/results';fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch();let starts=0,reads=0,sessionLookups=0,saveAcknowledged=false;
try{
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',response=>{if(new URL(response.url()).pathname==='/api/projects/save'&&response.ok())saveAcknowledged=true;});
 page.on('request',request=>{if(new URL(request.url()).pathname==='/api/design-sources/figure'){assert.equal(saveAcknowledged,true,'Save must be acknowledged before scoped figure retrieval');reads++;}});
 await page.route('**/api/session',async route=>{sessionLookups++;await new Promise(resolve=>setTimeout(resolve,1800));return route.continue();});
 await page.route(/\/api\/engineering\/(start|work-orders\/block)$/,route=>{starts++;return route.abort();});
 await page.goto(process.env.ATMEM_SOURCE_HANDOFF_URL||'http://127.0.0.1:5217');
 await page.locator('#project-file-input').setInputFiles({name:'source-design.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(projectFile))});
 await page.waitForFunction(id=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').id===id,projectFile.meta.id);
 const tree=page.getByRole('navigation',{name:'Component tree'});if(!await tree.isVisible())await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await tree.getByRole('button',{name:node.data.label,exact:true}).click();
 await page.getByText('Block Spec Kit',{exact:true}).click();
 await page.getByRole('button',{name:'Prepare agent handoff',exact:true}).click();
 const downloading=page.waitForEvent('download',{timeout:120000});
 await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();
 const download=await Promise.race([downloading,page.getByRole('region',{name:'Module agent handoff'}).getByRole('alert').waitFor({timeout:120000}).then(async()=>{const message=await page.getByRole('region',{name:'Module agent handoff'}).getByRole('alert').innerText();await page.screenshot({path:path.join(output,'failure.png')});throw Error('Source handoff failed: '+message);})]);await download.saveAs(path.join(output,'handoff.zip'));
 const archive=unzipSync(fs.readFileSync(await download.path())),manifest=JSON.parse(strFromU8(archive['handoff-manifest.json'])),readiness=JSON.parse(strFromU8(archive['handoff-readiness.json']));
 for(const [name,receipt]of Object.entries(manifest.files)){assert.ok(archive[name],name);assert.equal(createHash('sha256').update(archive[name]).digest('hex'),receipt.sha256);assert.equal(archive[name].length,receipt.bytes);}
 assert.equal(readiness.sourceEvidence.embedded,expected.length);assert.equal(reads,expected.length);
 for(const {source,figure}of expected){
  const row=readiness.sourceFigures.find(row=>row.sourceSha256===source.sha256&&row.id===figure.id);assert.equal(row.exportStatus,'verified');assert.equal(row.embedded,true);assert.deepEqual(row.locations,figure.locations);assert.equal(row.manifestSha256,source.figureEvidence.manifestSha256);
  assert.equal(createHash('sha256').update(archive[row.path]).digest('hex'),figure.sha256);
  const dimensions=await page.evaluate(async base64=>{const response=await fetch('data:image/png;base64,'+base64),bitmap=await createImageBitmap(await response.blob());const size=[bitmap.width,bitmap.height];bitmap.close();return size;},Buffer.from(archive[row.path]).toString('base64'));
  assert.ok(dimensions[0]>0&&dimensions[1]>0);
 }
 assert.equal(starts,0);assert.equal(sessionLookups,1);assert.deepEqual(errors,[]);
 assert.equal(manifest.implementationExecuted,false);assert.equal(manifest.deploymentExecuted,false);
 const receipt={projectId:projectFile.meta.id,blockId,normalizedImagesVerified:expected.length,manifestFilesVerified:Object.keys(manifest.files).length,sourceSha256:manifest.sourceSha256,implementationStarts:starts,sessionLookups,saveAcknowledged,originalDocumentBytesEmbedded:false,architectureInterpretationProven:false};
 await page.getByRole('region',{name:'Module agent handoff'}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'handoff.png')});
 // A real architecture edit during save must reject the old export, while journal-only updates do not.
 await page.waitForTimeout(900);
 let releaseSave,held=false,extraDownloads=0;
 const released=new Promise(resolve=>{releaseSave=resolve;});
 await page.route('**/api/projects/save',async route=>{if(!held){held=true;await released;}return route.continue();});
 page.on('download',()=>extraDownloads++);
 const saving=page.waitForRequest(request=>new URL(request.url()).pathname==='/api/projects/save');
 await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();await saving;
 await page.getByRole('textbox',{name:'Block name',exact:true}).fill(node.data.label+' edited during export');
 await page.getByRole('textbox',{name:'Block name',exact:true}).blur();
 await page.waitForFunction(({blockId,label})=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').nodes?.find(node=>node.id===blockId)?.data.label===label,{blockId,label:node.data.label+' edited during export'});
 releaseSave();
 await page.getByRole('region',{name:'Module agent handoff'}).getByRole('alert').filter({hasText:'The design changed while preparing source images.'}).waitFor();
 assert.equal(reads,expected.length);assert.equal(extraDownloads,0);receipt.concurrentDesignChangeRejected=true;
 fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify(receipt));
}finally{await browser.close();}
