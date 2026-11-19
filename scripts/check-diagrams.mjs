import fs from 'node:fs';
import path from 'node:path';
import {chromium} from '@playwright/test';

const root=process.argv[2];
const output=process.argv[3];
if(!root||!output)throw Error('Usage: node scripts/check-diagrams.mjs PACKAGE_DIRECTORY RESULTS_DIRECTORY');
const base=process.env.ATMEM_WORKFLOW_URL||'http://127.0.0.1:5194';
function walk(folder) {
  return fs.readdirSync(folder,{withFileTypes:true}).flatMap(entry=>{
    const full=path.join(folder,entry.name);
    if(entry.isDirectory())return walk(full);
    if(entry.name.endsWith('.mmd'))return [{file:path.relative(root,full),source:fs.readFileSync(full,'utf8')}];
    if(entry.name.endsWith('.md'))return [...fs.readFileSync(full,'utf8').matchAll(/^```mermaid[ \t]*\r?\n([\s\S]*?)^```[ \t]*$/gm)]
      .map((match,index)=>({file:path.relative(root,full)+'#mermaid-'+(index+1),source:match[1]}));
    return [];
  });
}
const files=walk(root);
const browser=await chromium.launch();
const results=[];
try {
 const page=await browser.newPage({viewport:{width:1600,height:1200}});
 await page.route('**/diagram-audit',route=>route.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));
 await page.goto(base+'/diagram-audit');
 await page.evaluate(async()=>{
  const {default:mermaid}=await import('/node_modules/mermaid/dist/mermaid.esm.min.mjs');
  mermaid.initialize({startOnLoad:false,securityLevel:'strict',suppressErrorRendering:true,flowchart:{htmlLabels:false}});
  window.auditMermaid=mermaid;
 });
 fs.mkdirSync(output,{recursive:true});
 for(const [index,{file,source}] of files.entries()){
  const result=await page.evaluate(async({source,index})=>{
   try{
    const {svg}=await window.auditMermaid.render('audit'+index,source);
    const doc=new DOMParser().parseFromString(svg,'image/svg+xml');
    const box=doc.documentElement.getAttribute('viewBox')?.split(/\s+/).map(Number);
    if(doc.querySelector('parsererror')||!box||box.some(n=>!Number.isFinite(n))||box[2]<=0||box[3]<=0)throw Error('Invalid SVG geometry');
    return {status:'rendered',viewBox:box,svg};
   }catch(e){return {status:'failed',error:e.message};}
   finally{document.querySelectorAll('body > div').forEach(node=>node.remove());}
  },{source,index});
  const {svg,...summary}=result;
  results.push({file,...summary});
  if(svg && (index<3 || summary.viewBox[2]>6000))fs.writeFileSync(path.join(output,index+'.svg'),svg);
  if(result.status==='failed'||(index+1)%50===0)console.log(index+1,results.filter(r=>r.status==='failed').length,'failures',result.status==='failed'?file+': '+result.error.slice(0,240):'');
 }
 fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({files:files.length,results},null,2));
 console.log('Rendering complete',JSON.stringify({rendered:results.filter(r=>r.status==='rendered').length,failed:results.filter(r=>r.status==='failed').length}));
 if(!files.length||results.some(result=>result.status==='failed'))process.exitCode=1;
} finally {await browser.close();}
