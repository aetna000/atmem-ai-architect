import {drawioFile} from './drawio-model.mjs';
import {architectureGraph} from './architecture-diagram-geometry.mjs';
import {diagramProjection} from './architecture-diagrams.mjs';
import {DiagramLayoutError,renderDiagramSvg} from './drawio-render.mjs';
import {drawioPages,diagramFileStem} from './drawio-handoff.mjs';
import {diagramReferenceRows} from './diagram-labels.mjs';
import {html} from './handoff-presentation.mjs';
import {sequenceFigure,connectionFigure} from './handoff-drawings.mjs';

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

export async function renderProjectScenes(project,{allowConnectionSheets=false}={}){
  const entries=[],verifiedPages=[],checks=[];
  let board;
  for(const [index,page] of drawioPages(project).entries()){
    let result,presentation=page.timeline?'sequence':'saved-layout';
    try{
      result=await renderDiagramSvg(page,{name:page.name,revision:project.revision});
      if(page.timeline)result.drawingSvg=sequenceFigure(page).drawingSvg;
    }catch(error){
      if(!allowConnectionSheets||!(error instanceof DiagramLayoutError))throw error;
      result={...(page.timeline?sequenceFigure(page):connectionFigure(page)),scene:page,readability:error.readability};
      presentation=page.timeline?'sequence':'connections';
    }
    if(!index)board=result;
    const {svg,drawingSvg,scene,readability}=result,stem=diagramFileStem(page.name,index);
    verifiedPages.push(scene);checks.push({id:page.id,name:page.name,presentation,...readability,nativeRoutingRepairs:scene.nativeRoutingRepairs,
      references:diagramReferenceRows(scene).map(({number,from,to,description})=>({number,from,to,description}))});
    entries.push(['diagrams/'+stem+'.svg',svg],['diagrams/figures/'+stem+'.svg',drawingSvg]);
  }
  entries.push(['architecture.drawio',drawioFile(verifiedPages)]);
  entries.push(['diagram-readability.json',JSON.stringify({version:1,revision:project.revision,evidence:'Rendered native geometry, text and connector checks; not deployment verification',pages:checks},null,2)]);
  const links=checks.map((p,i)=>{const stem=diagramFileStem(p.name,i);return '<figure><h2>'+html(p.name)+'</h2><a href="'+stem+'.svg"><img loading="lazy" alt="'+html(p.name)+'" src="figures/'+stem+'.svg"></a><figcaption>'+p.nodes+' elements · '+p.connections+' relationships · <a href="'+stem+'.svg">Open drawing with references</a></figcaption></figure>';}).join('');
  entries.push(['diagrams/index.html','<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html(project.name)+' diagrams</title><style>body{font:16px/1.5 system-ui;margin:32px auto;padding:0 20px;color:#19362f;max-width:1000px}figure{margin:2em 0}img{display:block;width:100%;border:1px solid #cbd8ce;border-radius:6px}a{color:#17614f}figcaption{padding:.5em 0}</style><main><h1>'+html(project.name)+'</h1><p>Design revision '+html(project.revision)+'</p>'+links+'</main></html>']);
  return {files:Object.fromEntries(entries),board};
}

export async function projectSceneFiles(project){return (await renderProjectScenes(project)).files;}
