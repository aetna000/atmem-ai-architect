import {diagramProjection,kindLabel} from './architecture-diagrams.mjs';

export function architectureDiagramHandoff(projectName,revision,model){
  const lines=['# '+projectName+' diagram handoff','',
    'Project revision '+revision,'',
    model.views.length+' views · '+model.elements.length+' shared elements · '+model.relations.length+' shared relationships','',
    'The diagrams describe the solution design. Specified records cite their source. Proposed records require review.',''];
  const labels=new Map(model.elements.map(row=>[row.id,row.name]));
  function record(row, endpoint=''){
    return ['### '+row.name, '',kindLabel(row.kind)+' · '+kindLabel(row.basis)+(endpoint?' · '+endpoint:'')+' · '+row.id,'',
      ...(row.source?['Source — '+row.source,'']:[]),
      ...row.details.flatMap(({name,value})=>['**'+name+'**','',value,''])];
  }
  for(const view of model.views){
    const {nodes,edges,diagnostics}=diagramProjection(model,view);
    lines.push('## '+view.name,'');
    if(diagnostics.length)lines.push('**Open items**','',...diagnostics.map(issue=>'- '+issue),'');
    if(nodes.length)lines.push('**Elements**','',...nodes.map(row=>'- '+row.name+' · '+row.id),'');
    if(edges.length)lines.push('**Relationships**','',...edges.map((row,index)=>
      (view.kind==='sequence'?(index+1)+'. ':'- ')+labels.get(row.from)+' → '+labels.get(row.to)+' · '+row.name+' · '+row.id),'');
  }
  lines.push('## Shared elements','',...model.elements.flatMap(row=>record(row)),
    '## Shared relationships','',...model.relations.flatMap(row=>record(row,labels.get(row.from)+' → '+labels.get(row.to))));
  return lines.join('\n')+'\n';
}

export function architectureDiagramReview(projectName,revision,model){
  const views=model.views.map(view=>{
    const {nodes,edges,diagnostics}=diagramProjection(model,view);
    const records=[...new Map([...nodes,...edges].map(row=>[row.id,row])).values()];
    return {id:view.id,kind:view.kind,name:view.name,elements:nodes.length,relationships:edges.length,
      specified:records.filter(row=>row.basis==='specified').length,proposed:records.filter(row=>row.basis==='proposed').length,
      sourceReferences:[...new Set(records.map(row=>row.source).filter(Boolean))],openItems:diagnostics};
  });
  return {version:1,project:projectName,revision,viewCount:views.length,
    populatedViewCount:views.filter(view=>view.elements).length,
    reviewBoundary:'Projection and evidence checks. Runtime and deployment verification are separate.',
    views};
}

export function architectureDiagramHandoffFiles(projectName,revision,model){
  return {
    'architecture-handoff.md':architectureDiagramHandoff(projectName,revision,model),
    'architecture-model.json':JSON.stringify(model,null,2),
    'architecture-review.json':JSON.stringify(architectureDiagramReview(projectName,revision,model),null,2),
  };
}
