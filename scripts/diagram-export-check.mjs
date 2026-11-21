import fs from 'node:fs';
import path from 'node:path';
import {chromium} from 'playwright';
import {parseProjectFile} from '../src/project-file.mjs';
import {drawioPages} from '../src/drawio-handoff.mjs';
const[url,file]=process.argv.slice(2),dir=process.env.EXPORT_EVIDENCE||'/tmp/atmem-diagram-export-audit';fs.mkdirSync(dir,{recursive:true});
const project=parseProjectFile(fs.readFileSync(file,'utf8')).project,scenes=drawioPages(project),results=[];
fs.writeFileSync(path.join(dir,'export-review.json'),JSON.stringify({status:'running',passed:false,pages:scenes.length,results:[]}));
let completed=false;
const browser=await chromium.launch({channel:'chrome'});
try{
 const page=await browser.newPage({viewport:{width:1512,height:945}});await page.goto(url);
 const rejected=await page.evaluate(async()=>{
  const {renderDiagramSvg}=await import('/src/drawio-render.mjs');
  const style='fontSize=14;whiteSpace=wrap;html=0;';
  const a={id:'a',name:'Clinic',body:'Clinic',x:0,y:0,width:160,height:80,style};
  const cases=[{vertices:[a,{...a,id:'b',name:'Pharmacy',body:'Pharmacy'}],wires:[]},
   {vertices:[{...a,body:'Identifiable clinical data must remain within its allowed processing boundary. '.repeat(10)}],wires:[]},
   {vertices:[a,{...a,id:'b',x:600},{...a,id:'obstacle',x:280}],wires:[{id:'crossing',source:'a',target:'b',body:'1',reference:'1',style:'noEdgeStyle=1;'}]}];
  const outcomes=[];for(const scene of cases){try{await renderDiagramSvg(scene,{name:'Invalid clinic diagram'});outcomes.push(false);}catch(e){if(!/layout issues/.test(e.message))throw e;outcomes.push(true);}}return outcomes;
 });
 if(!rejected.every(Boolean))throw Error('Readability gate accepted a deliberately unreadable diagram.');
 fs.writeFileSync(path.join(dir,'negative-controls.json'),JSON.stringify({overlappingNodesRejected:rejected[0],unwrappedTextRejected:rejected[1],lineThroughNodeRejected:rejected[2]},null,2));
 for(const [i,scene]of scenes.entries()){
  const result=await page.evaluate(async({scene,name,revision})=>{
   const {renderDiagramSvg}=await import('/src/drawio-render.mjs');
   const originalProjection=JSON.stringify(scene);const result=await renderDiagramSvg(scene,{name,revision});
   const projectionUnchanged=originalProjection===JSON.stringify(scene);
   const holder=document.createElement('div');holder.style.cssText='position:absolute;left:0;top:0;background:white;z-index:999';holder.innerHTML=result.svg;document.body.append(holder);
   const roots=[...holder.querySelectorAll('[data-cell-kind=vertex]')].filter(n=>scene.vertices.find(v=>v.id===n.dataset.recordId)?.selectable!==false);
   const boxes=roots.map(n=>({id:n.dataset.recordId,box:n.getBoundingClientRect()})),overflow=[],overlaps=[],edgeOverlaps=[];
   const intersects=(a,b)=>a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1;
   roots.forEach((n,i)=>{const box=boxes[i].box;for(const t of n.nextElementSibling?.querySelectorAll('text')||[]){const r=t.getBoundingClientRect();if(r.left<box.left-2||r.right>box.right+2||r.top<box.top-2||r.bottom>box.bottom+2)overflow.push({id:n.dataset.recordId,text:t.textContent});}for(let j=0;j<i;j++)if(intersects(box,boxes[j].box))overlaps.push([boxes[i].id,boxes[j].id]);});
   const labels=[...holder.querySelectorAll('[data-cell-kind=edge]')].flatMap(n=>[...n.nextElementSibling?.querySelectorAll('text')||[]].map(t=>({id:n.dataset.recordId,box:t.getBoundingClientRect()})));
   for(let j=0;j<labels.length;j++){for(const node of boxes)if(intersects(labels[j].box,node.box))edgeOverlaps.push([labels[j].id,node.id]);for(let k=0;k<j;k++)if(intersects(labels[j].box,labels[k].box))edgeOverlaps.push([labels[j].id,labels[k].id]);}
   const legend=holder.querySelector('[data-diagram-references]')?.textContent||'';
   const references=scene.wires.map(w=>{const row=[...holder.querySelectorAll('[data-connection-reference]')].find(n=>n.dataset.recordId===w.id&&n.dataset.connectionReference===w.reference);const body=(w.detailBody??w.name??w.body).replace(/\s/g,'');return{id:w.id,retained:!!row&&row.textContent.replace(/\s/g,'').includes(body)&&row.dataset.from===scene.vertices.find(v=>v.id===w.source)?.name&&row.dataset.to===scene.vertices.find(v=>v.id===w.target)?.name};});
   const strokes=[...holder.querySelectorAll('[data-cell-kind=edge]')].map(n=>({id:n.dataset.recordId,path:[...n.querySelectorAll('path')].find(p=>p.getAttribute('fill')==='none'&&p.getAttribute('visibility')!=='hidden')})).filter(v=>v.path);
   const buckets=new Map();
   strokes.forEach((stroke,index)=>{const matrix=stroke.path.getScreenCTM(),length=stroke.path.getTotalLength();stroke.samples=[];for(let at=4;at<length-4;at+=4){const p=stroke.path.getPointAtLength(at),q=new DOMPoint(p.x,p.y).matrixTransform(matrix);stroke.samples.push(q);const key=Math.floor(q.x/4)+':'+Math.floor(q.y/4);if(!buckets.has(key))buckets.set(key,new Set());buckets.get(key).add(index);}});
   const likely=new Map();strokes.forEach((stroke,index)=>{const counts=new Map();for(const p of stroke.samples){const seen=new Set(),x=Math.floor(p.x/4),y=Math.floor(p.y/4);for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const other of buckets.get((x+dx)+':'+(y+dy))||[])if(other<index)seen.add(other);for(const other of seen)counts.set(other,(counts.get(other)||0)+1);}likely.set(index,[...counts].filter(([,count])=>count>=6).map(([other])=>other));});
   const strokeOverlaps=[];for(let i=0;i<strokes.length;i++)for(const j of likely.get(i)){
    const b=strokes[j].path,inverse=b.getScreenCTM().inverse();let run=0,longest=0;
    let previousHit=false;
    for(const screen of strokes[i].samples){const local=screen.matrixTransform(inverse),hit=b.isPointInStroke(local);if(hit){run=previousHit?run+4:0;longest=Math.max(longest,run);}else run=0;previousHit=hit;}
    if(longest>24)strokeOverlaps.push([strokes[i].id,strokes[j].id,longest]);
   }
   const measured={projectionUnchanged,strokeOverlaps,nodes:roots.length,expectedNodes:scene.vertices.filter(v=>v.selectable!==false).length,overflow,overlaps,edgeOverlaps,references};holder.remove();return{...result,measured};
  },{scene,name:scene.name,revision:project.revision});
  const filename=String(i).padStart(2,'0')+'-'+scene.id.replace(/[^a-z0-9]/gi,'-')+'.svg';fs.writeFileSync(path.join(dir,filename),result.svg);
  results.push({id:scene.id,name:scene.name,file:filename,width:result.width,height:result.height,...result.measured});
 }
 completed=true;
}catch(error){fs.writeFileSync(path.join(dir,'export-review.json'),JSON.stringify({status:'failed',passed:false,error:error.message,pages:scenes.length,results},null,2));throw error;}finally{await browser.close();}
const failed=results.filter(r=>!r.projectionUnchanged||r.nodes!==r.expectedNodes||r.overflow.length||r.overlaps.length||r.edgeOverlaps.length||r.strokeOverlaps.length||r.references.some(x=>!x.retained));
fs.writeFileSync(path.join(dir,'export-review.json'),JSON.stringify({status:'completed',passed:failed.length===0,pages:scenes.length,failed:failed.length,results},null,2));console.log(JSON.stringify({pages:scenes.length,failed:failed.length,evidence:dir}));if(process.env.READABILITY_STRICT==='1'&&failed.length)process.exitCode=1;
