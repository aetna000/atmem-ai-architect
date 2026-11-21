import {applyDrawingLayout} from './drawing-layout.mjs';
import {architectureGraph} from './architecture-diagram-geometry.mjs';
import {diagramProjection} from './architecture-diagrams.mjs';
import {boardGraph,drawioFile,graphMermaid} from './drawio-model.mjs';

import {engineeringDiagram,engineeringElementIndex} from './engineering-model.mjs';
import {systemModelIndex,systemModelOnBoard} from './system-model.mjs';
import {engineeringGraph,legacyGraph} from './model-page-geometry.mjs';

export function drawioPages(project,model=project.extensions?.architectureDiagrams){
  const system=project.extensions?.systemModel&&systemModelOnBoard(project.extensions.systemModel,project);
  const engineering=project.extensions?.engineeringModel;
  const systemIndex=system&&systemModelIndex(system);
  const engineeringIndex=engineering&&engineeringElementIndex(engineering);
  const blocks=new Map(project.nodes.map(node=>[node.id,node.data.buildSpec]));
  function linked(scene,blockId){
    return {...scene,vertices:scene.vertices.map(row=>({...row,properties:blocks.get(blockId(row.id))}))};
  }
  return [
    {id:'board',name:'Architecture board',...boardGraph(project.nodes,project.edges)},
    ...(model?.views||[]).map(view=>{
      const projection=diagramProjection(model,view);
      return {id:view.id,name:view.name,timeline:projection.type.layout==='timeline',...architectureGraph(projection,view)};
    }),
    ...(system?.diagrams||[]).map(view=>({id:'system/'+view.id,name:view.name,timeline:view.kind==='sequence',
      ...linked(legacyGraph(view,systemIndex),id=>systemIndex.elements.get(id)?.blockId)})),
    ...(engineering?.diagrams||[]).map(view=>({id:'engineering/'+view.id,name:view.name,
      ...linked(engineeringGraph(engineeringDiagram(engineering,view.id),engineeringIndex),id=>engineeringIndex.get(id)?.element.blockId)})),
  ].map(page=>({...page,...applyDrawingLayout(page,(project.extensions?.drawingLayouts?.pages?.[page.id==='board'?'board/full':page.id.startsWith('system/')||page.id.startsWith('engineering/')?page.id:'view/'+page.id]??(page.id==='board'&&!project.nodes.some(n=>n.data.parentBlockId)?project.extensions?.drawingLayouts?.pages?.board:undefined)))}));
}

export function drawioHandoffFiles(project,model){
  const pages=drawioPages(project,model);
  return {
    'architecture.drawio':drawioFile(pages),
    ...Object.fromEntries(pages.map((page,index)=>{
      const slug=page.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,90)||'page';
      return ['diagrams/'+String(index+1).padStart(2,'0')+'-'+slug+'.mmd',graphMermaid(page,{timeline:page.timeline})];
    })),
  };
}
