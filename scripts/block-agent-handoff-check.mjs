import {verifyReceivingCapture} from './receiving-capture.mjs';
import {relativeLinkReport} from './receiving-links.mjs';
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {chromium} from '@playwright/test';import {unzipSync,strFromU8} from 'fflate';import {toProjectFile} from '../src/project-file.mjs';
// Real receiving-browser export of an existing design. No model/implementation starts.
const [sourceFile,blockId]=process.argv.slice(2);if(!sourceFile||!blockId)throw Error('Usage: block-agent-handoff-check.mjs <design.json> <block-id>');
const raw=JSON.parse(fs.readFileSync(sourceFile)),file=raw.format?raw:toProjectFile(raw),selected=file.design.nodes.find(node=>node.id===blockId);assert.ok(selected);
const output=process.env.ATMEM_BLOCK_HANDOFF_OUTPUT||'.local/block-agent-handoff-check';fs.mkdirSync(output,{recursive:true});
const hash=bytes=>createHash('sha256').update(bytes).digest('hex'),browser=await chromium.launch();let starts=0;
try{
 const page=await browser.newPage({viewport:{width:1500,height:1050}}),errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route(/\/api\/engineering\/(start|steer|work-orders\/block)$/,route=>{starts++;return route.abort();});
 await page.goto(process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5207');
 await page.locator('#project-file-input').setInputFiles({name:'receiving-design.atmem-ai-architect.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});
 await page.waitForFunction(id=>JSON.parse(localStorage.getItem('atforma-workspace-v3')||'{}').id===id,file.meta.id);
 if(file.design.nodes.some(node=>node.data.parentBlockId===blockId)){
  await page.getByRole('combobox',{name:'Architecture level'}).selectOption(blockId);
  const hideChat=page.getByRole('button',{name:'Hide chat',exact:true});if(await hideChat.isVisible())await hideChat.click();
  await page.waitForTimeout(350);await page.screenshot({path:path.join(output,'nested-canvas.png')});
 }
 const tree=page.getByRole('navigation',{name:'Component tree'});if(!await tree.isVisible())await page.getByRole('button',{name:'Toggle components and layers'}).click();
 await tree.getByRole('button',{name:selected.data.label,exact:true}).click();await page.getByText('Block Spec Kit',{exact:true}).click();
 await page.getByRole('button',{name:'Prepare agent handoff',exact:true}).click();const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Download agent handoff',exact:true}).click();
 const download=await pending;await download.saveAs(path.join(output,'handoff.zip'));
 const files=unzipSync(fs.readFileSync(await download.path())),manifest=JSON.parse(strFromU8(files['handoff-manifest.json'])),source=JSON.parse(strFromU8(files['source-context.json']));
 assert.equal(manifest.sourceSha256,hash(files['source-context.json']));assert.equal(source.meta.id,file.meta.id);assert.equal(manifest.blockId,blockId);
 for(const [name,receipt]of Object.entries(manifest.files)){assert.ok(files[name],name);assert.equal(hash(files[name]),receipt.sha256,name);assert.equal(files[name].length,receipt.bytes,name);}
 const scope=new Set([blockId]);let changed=true;while(changed){changed=false;for(const node of source.design.nodes)if(scope.has(node.data.parentBlockId)&&!scope.has(node.id)){scope.add(node.id);changed=true;}}
 assert.deepEqual(new Set(manifest.blockIds),scope);
 for(const id of scope){const prefix='spec-kit/blocks/block-'+Buffer.from(id).toString('hex')+'/';for(const name of ['spec.md','plan.md','tasks.json','testing.md','infrastructure-devops.md','WORK_ORDER.md'])assert.ok(files[prefix+name],prefix+name);}
 const receipt=JSON.parse(strFromU8(files['design-documents-receipt.json']));
 for(const item of receipt.files){assert.ok(files[item.exportPath],'Missing authored document '+item.exportPath);assert.equal(hash(files[item.exportPath]),item.sha256);const original=file.extensions.architectureDocuments.files.find(row=>row.path===item.path);assert.ok(original);assert.equal(hash(Buffer.from(original.content)),item.sha256);}
 const draftEvidence=JSON.parse(strFromU8(files['design-evidence.json']));assert.equal(draftEvidence.status,'verified');assert.equal(hash(files['architecture.canvas.json']),file.extensions.architectureDocuments.draftSha256);assert.equal(draftEvidence.contextSha256,file.extensions.architectureDocuments.contextSha256);
 const capturedEvidence=verifyReceivingCapture(files,file.extensions.architectureDocuments);
 const links=relativeLinkReport(files),relativeLinks=links.checked;assert.deepEqual(links.missing,[],'All relative document links must resolve in the receiving ZIP');
 const consistency=JSON.parse(strFromU8(files['spec-kit/architecture-consistency.json']));assert.equal(consistency.counts.errors,0);
 assert.equal(manifest.implementationExecuted,false);assert.equal(manifest.deploymentExecuted,false);assert.equal(starts,0);assert.deepEqual(errors,[]);
 await page.context().grantPermissions(['clipboard-read','clipboard-write']);await page.getByRole('button',{name:'Copy agent prompt',exact:true}).click();await page.getByText('Agent prompt copied. Give it the handoff ZIP.',{exact:true}).waitFor();assert.match(await page.evaluate(()=>navigator.clipboard.readText()),/architecture-consistency.json/);
 await page.getByRole('region',{name:'Module agent handoff'}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'module-handoff.png')});
 const result={projectId:manifest.projectId,blockId,assignedModules:manifest.blockIds.length,payloadFilesVerified:Object.keys(manifest.files).length,authoredDocumentsVerified:receipt.files.length,relativeLinksVerified:relativeLinks,reviewedDraftSha256:draftEvidence.draftSha256,capturedEvidence,sourceSha256:manifest.sourceSha256,behavior:consistency.counts,implementationStarts:starts,clipboardVerified:true,implementationExecuted:false,deploymentExecuted:false};fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{await browser.close();}
