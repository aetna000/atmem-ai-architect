import {drawioFile} from './drawio-model.mjs';
import {architectureGraph} from './architecture-diagram-geometry.mjs';
import {diagramProjection} from './architecture-diagrams.mjs';
import {renderDiagramSvg} from './drawio-render.mjs';

export async function architectureSceneFiles(model,revision){
  const entries=[];
  for(const [index,view] of model.views.entries()){
    const scene=architectureGraph(diagramProjection(model,view),view);
    const {svg}=await renderDiagramSvg(scene,{name:view.name,revision});
    const slug=view.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,90)||view.kind;
    entries.push(['diagrams/'+String(index+1).padStart(2,'0')+'-'+slug+'.svg',svg]);
  }
  return Object.fromEntries(entries);
}

export async function projectSceneFiles(project){
  const {drawioPages}=await import('./drawio-handoff.mjs');
  const entries=[],verifiedPages=[],checks=[];
  for(const [index,page] of drawioPages(project).entries()){
    const {svg,scene,readability}=await renderDiagramSvg(page,{name:page.name,revision:project.revision});
    verifiedPages.push(scene);checks.push({id:page.id,name:page.name,...readability,nativeRoutingRepairs:scene.nativeRoutingRepairs});
    const slug=page.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,90)||'page';
    entries.push(['diagrams/'+String(index+1).padStart(2,'0')+'-'+slug+'.svg',svg]);
  }
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pages=verifiedPages;
  entries.push(['architecture.drawio',drawioFile(verifiedPages)]);
  entries.push(['diagram-readability.json',JSON.stringify({version:1,revision:project.revision,evidence:'Rendered native geometry, text and connector checks; not deployment verification',pages:checks},null,2)]);
  const links=entries.filter(([name])=>name.endsWith('.svg')).map(([name],i)=>'<li><a href="'+escape(name.slice(9))+'">'+escape(pages[i].name)+'</a><span>'+pages[i].vertices.filter(v=>v.selectable!==false).length+' elements · '+pages[i].wires.length+' relationships</span></li>').join('');
  entries.push(['diagrams/index.html','<!doctype html><html lang="en"><meta charset="utf-8"><title>'+escape(project.name)+' diagrams</title><style>body{font:16px/1.5 system-ui;margin:40px;color:#202639;max-width:1050px}h1{font-size:32px}ul{padding:0;list-style:none}li{padding:14px;border-bottom:1px solid #ddd}a{color:#873b50}span{display:block;font-size:12px;color:#666}</style><h1>'+escape(project.name)+'</h1><p>Design revision '+project.revision+'</p><ul>'+links+'</ul></html>']);
  return Object.fromEntries(entries);
}
