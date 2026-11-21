// Read-only, rendered audit: inspect every page, not merely catalogue counts.
import fs from 'node:fs';
import path from 'node:path';
import {chromium} from 'playwright';
import {parseProjectFile} from '../src/project-file.mjs';
import {drawioPages} from '../src/drawio-handoff.mjs';
import {boardGraph} from '../src/drawio-model.mjs';
import {nestedCanvas,preferredNestedScope} from '../src/nested-canvas.mjs';
const [url,file]=process.argv.slice(2);
if(!url||!file)throw Error('Supply URL and saved project.');
const dir=process.env.READABILITY_EVIDENCE||'/tmp/atmem-diagram-readability-audit';fs.mkdirSync(dir,{recursive:true});
const project=parseProjectFile(fs.readFileSync(file,'utf8')).project,scenes=drawioPages(project);
fs.writeFileSync(path.join(dir,'review.json'),JSON.stringify({status:'running',passed:false}));let completed=false;
const browser=await chromium.launch({channel:'chrome'}),results=[],errors=[];
try{
 for(const width of [1512,390]){
  const page=await browser.newPage({viewport:{width,height:945}});page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/projects/save',r=>r.fulfill({json:{saved:true,sha256:'a'.repeat(64)}}));
  await page.route('**/api/engineering/**',r=>r.fulfill({json:{sessions:[],artifacts:[],checks:[]}}));
  await page.goto(url);await page.locator('#project-file-input').setInputFiles(file);
  await page.getByRole('tablist',{name:'Project stages'}).getByRole('tab',{name:'Board',exact:true}).click();
  for(const [i,fullScene]of scenes.entries()){
   const boardScope=nestedCanvas(project,preferredNestedScope(project));
   const scene=i===0?{...fullScene,...boardGraph(boardScope.nodes,boardScope.edges)}:fullScene;
   const id=i===0?'board':scene.id.startsWith('system/')||scene.id.startsWith('engineering/')?scene.id:'view/'+scene.id;
   await page.locator('.drawing-pagebar:visible').getByLabel('Go to page').selectOption(id);
   await page.locator('.drawio-canvas:visible').last().filter({has:page.locator('[role=button]')}).waitFor();
   await page.waitForFunction(name=>{const h=[...document.querySelectorAll('.drawio-canvas')].find(n=>n.getClientRects().length&&n.dataset.renderedPage===name&&n.dataset.readabilityStatus!=='deferred');return!!h;},scene.name);
   await page.waitForTimeout(80);
   const metrics=await page.locator('.drawio-canvas:visible').last().evaluate((host,scene)=>{
    const roots=[...host.querySelectorAll('[role=button]')];
    const expected=scene.vertices.filter(v=>v.selectable!==false);
    const shapeRoots=roots.filter(root=>root.dataset.cellKind?root.dataset.cellKind==='vertex':expected.some(v=>v.name===root.getAttribute('aria-label')));
    const vertices=shapeRoots.map(root=>expected.find(v=>v.id===root.dataset.recordId)||expected.find(v=>v.name===root.getAttribute('aria-label')));
    const edgeRoots=roots.filter(root=>!shapeRoots.includes(root));
    const rect=n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height};};
    const intersects=(a,b)=>a.x<b.x+b.w-1&&a.x+a.w>b.x+1&&a.y<b.y+b.h-1&&a.y+a.h>b.y+1;
    const nodeBoxes=shapeRoots.map(rect),overflow=[],nodeOverlaps=[],edgeNodeOverlaps=[],edgeOverlaps=[],wireNodeCrossings=[];
    shapeRoots.forEach((root,i)=>{
     const box=nodeBoxes[i];
     for(const t of root.nextElementSibling?.querySelectorAll('text')||[]){
      const r=rect(t);if(r.x<box.x-2||r.x+r.w>box.x+box.w+2||r.y<box.y-2||r.y+r.h>box.y+box.h+2)overflow.push({id:vertices[i]?.id,text:t.textContent});
     }
     for(let j=0;j<i;j++)if(intersects(box,nodeBoxes[j]))nodeOverlaps.push([vertices[j]?.id,vertices[i]?.id]);
    });
    for(const root of edgeRoots){
     const edge=scene.wires.find(w=>(w.recordId||w.id)===root.dataset.recordId)||scene.wires.find(w=>w.name===root.getAttribute('aria-label'));
     const path=[...root.querySelectorAll('path')].find(p=>p.getAttribute('fill')==='none'&&p.getAttribute('visibility')!=='hidden');
     if(!path||!edge)continue;const length=path.getTotalLength(),matrix=path.getScreenCTM(),crossed=new Set();
     for(let at=8;at<length-8;at+=6){const point=path.getPointAtLength(at),screen=new DOMPoint(point.x,point.y).matrixTransform(matrix);
      nodeBoxes.forEach((box,i)=>{if([edge.source,edge.target].includes(vertices[i]?.id))return;if(screen.x>box.x+3&&screen.x<box.x+box.w-3&&screen.y>box.y+3&&screen.y<box.y+box.h-3)crossed.add(vertices[i]?.id);});
     }
     for(const id of crossed)wireNodeCrossings.push([edge.id,id]);
    }
    const edgeLabels=edgeRoots.map(root=>({id:root.getAttribute('data-record-id')||root.getAttribute('aria-label'),texts:[...root.nextElementSibling?.querySelectorAll('text')||[]]}));
    const boxes=[];for(const edge of edgeLabels)for(const t of edge.texts){const box=rect(t);boxes.push({id:edge.id,box});for(let j=0;j<nodeBoxes.length;j++)if(intersects(box,nodeBoxes[j]))edgeNodeOverlaps.push([edge.id,vertices[j]?.id]);}
    for(let i=0;i<boxes.length;i++)for(let j=0;j<i;j++)if(intersects(boxes[i].box,boxes[j].box))edgeOverlaps.push([boxes[i].id,boxes[j].id]);
    const fonts=[...shapeRoots.flatMap(root=>[...root.nextElementSibling?.querySelectorAll('text')||[]])].map(t=>parseFloat(getComputedStyle(t).fontSize));
    return{renderedNodes:shapeRoots.length,expectedNodes:expected.length,missingIds:expected.filter(v=>!vertices.some(n=>n?.id===v.id)).map(v=>v.id),overflow,nodeOverlaps,edgeNodeOverlaps,edgeOverlaps,wireNodeCrossings,minNodeFont:Math.min(...fonts)};
   },scene);
   const controls=await page.evaluate(()=>{
    const roots=[...document.querySelectorAll('.studio-library,.architecture-header,.architecture-viewbar,.system-model-header,.system-model-tools,.drawing-pagebar,.studio-library-toggle,.diagram-navigation,.diagram-references,.diagram-layout-issues,.drawio-board-source,.system-model-inspector')].filter(n=>n.getClientRects().length);
    const nodes=[...new Set(roots.flatMap(n=>n.matches('button')?[n]:[...n.querySelectorAll('button,summary,input:not([type=hidden])')]))].filter(n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden'&&!n.closest('details:not([open])>div'));
    const pairs=[];for(let i=0;i<nodes.length;i++)for(let j=0;j<i;j++){
     const a=nodes[i],b=nodes[j];if(a.contains(b)||b.contains(a))continue;
     const clipped=n=>{const r=n.getBoundingClientRect(),box={left:r.left,right:r.right,top:r.top,bottom:r.bottom};for(let p=n.parentElement;p;p=p.parentElement){if(/auto|scroll|hidden/.test(getComputedStyle(p).overflow)){const pr=p.getBoundingClientRect();box.left=Math.max(box.left,pr.left);box.right=Math.min(box.right,pr.right);box.top=Math.max(box.top,pr.top);box.bottom=Math.min(box.bottom,pr.bottom);}}return box;};
     const ar=clipped(a),br=clipped(b);if(ar.left>=ar.right||ar.top>=ar.bottom||br.left>=br.right||br.top>=br.bottom)continue;
     // Ignore portions clipped by scroll containers.
     const visible=(n,r)=>{for(let p=n.parentElement;p;p=p.parentElement){if(/auto|scroll|hidden/.test(getComputedStyle(p).overflow)){const pr=p.getBoundingClientRect();if(r.bottom<=pr.top||r.top>=pr.bottom||r.right<=pr.left||r.left>=pr.right)return false;}}return true;};
     if(visible(a,ar)&&visible(b,br)&&ar.left<br.right-2&&ar.right>br.left+2&&ar.top<br.bottom-2&&ar.bottom>br.top+2)pairs.push([a.getAttribute('aria-label')||a.textContent.trim(),b.getAttribute('aria-label')||b.textContent.trim()]);
    }return pairs;
   });
   const referenceToggle=page.locator('.drawio-surface:visible').last().getByRole('button',{name:/^Details & connections/});
   await referenceToggle.click();
   const referenceRows=await page.locator('.drawio-surface:visible').last().locator('.diagram-reference-content ol>li').evaluateAll(ns=>ns.map(n=>({number:n.dataset.connectionReference,id:n.dataset.recordId,text:n.textContent.replace(/\s/g,'')})));
   const referenceMatch=scene.wires.every(w=>referenceRows.some(row=>row.id===w.id&&row.number===w.reference&&row.text.includes((w.detailBody||'').replace(/\s/g,''))))&&referenceRows.length===scene.wires.length;
   await referenceToggle.click();
   const screenshot=`${width}-${String(i).padStart(2,'0')}.png`;await page.screenshot({path:path.join(dir,screenshot)});
   results.push({width,id,name:scene.name,...metrics,controlOverlaps:controls,referenceMatch,screenshot});
  }
  await page.close();
 }
 completed=true;
}catch(error){fs.writeFileSync(path.join(dir,'review.json'),JSON.stringify({status:'failed',passed:false,error:error.message,results},null,2));throw error;}finally{await browser.close();}
const failed=results.filter(r=>r.overflow.length||r.nodeOverlaps.length||r.edgeNodeOverlaps.length||r.edgeOverlaps.length||r.wireNodeCrossings.length||r.controlOverlaps.length||r.minNodeFont<12||r.renderedNodes!==r.expectedNodes||r.missingIds?.length||!r.referenceMatch);
fs.writeFileSync(path.join(dir,'review.json'),JSON.stringify({status:'completed',passed:failed.length===0&&errors.length===0,projectId:project.id,revision:project.revision,scenes:scenes.length,viewports:[1512,390],errors,failed:failed.length,results},null,2));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
fs.writeFileSync(path.join(dir,'index.html'),'<!doctype html><meta charset="utf-8"><title>All diagram pages review</title><style>body{font:15px system-ui;margin:24px;color:#172033}article{margin:32px 0;border-top:1px solid #ddd}img{width:100%;max-width:1512px}pre{white-space:pre-wrap}</style><h1>All diagram pages · revision '+project.revision+'</h1><p>'+scenes.length+' pages, two viewports; '+failed.length+' page/viewports with findings.</p>'+results.map(r=>'<article><h2>'+esc(r.width+' · '+r.name)+'</h2><pre>'+esc(JSON.stringify({...r,screenshot:undefined},null,2))+'</pre><img loading="lazy" src="'+r.screenshot+'"></article>').join(''));
console.log(JSON.stringify({pages:scenes.length,observations:results.length,failed:failed.length,errors,evidence:dir}));
if(process.env.READABILITY_STRICT==='1'&&(failed.length||errors.length))process.exitCode=1;
