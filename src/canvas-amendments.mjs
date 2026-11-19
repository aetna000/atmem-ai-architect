// Source-backed design amendments. Identity, ownership and accepted scope are not
// model-writable through this channel; new allocation evidence is separate.
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
function keys(value,allowed,label){
 if(!object(value)||Object.keys(value).some(key=>!allowed.includes(key)))throw Error(`Unsupported ${label} fields. Preserve identity, ownership and accepted requirements.`);
}
function rows(value,limit,label){
 if(value===undefined)return [];
 if(!Array.isArray(value)||value.length>limit)throw Error(`Invalid ${label} inventory.`);
 return value;
}

export function amendCanvasGraph(project,draft){
 for(const field of ['removeNodes','removeEdges','updateRequirements','removeRequirements','needs','decisions','provider']){
  if(Object.hasOwn(draft,field))throw Error('This design channel cannot remove scope, rewrite requirements or change ownership. Record the proposed change for review.');
 }
 const nodes=new Map(project.nodes.map(node=>[node.id,node]));
 const edges=new Map(project.edges.map(edge=>[edge.id,edge]));
 const changes=[];
 const touched=new Set();
 for(const update of rows(draft.updateNodes,200,'block amendment')){
  keys(update,['id','data'],'block amendment');keys(update.data,['description','buildSpec','parentBlockId'],'block specification amendment');
  const before=nodes.get(update.id);
  if(!before||touched.has(update.id)||!Object.keys(update.data).length)throw Error('Each block amendment must name one existing block exactly once.');
  touched.add(update.id);
  if(Object.hasOwn(update.data,'description')&&(typeof update.data.description!=='string'||!update.data.description.trim()))throw Error('A block amendment needs a nonempty description.');
  const data={...before.data,...update.data};
  if(Object.hasOwn(update.data,'buildSpec')){
   if(!object(update.data.buildSpec)||!Object.keys(update.data.buildSpec).length)throw Error('A block amendment cannot clear its specification.');
   if(update.data.buildSpec.verificationCases!==undefined){
    const retained=new Set((update.data.buildSpec.verificationCases||[]).map(row=>row.id));
    if((before.data.buildSpec?.verificationCases||[]).some(row=>!retained.has(row.id)))throw Error('A refinement cannot silently remove verification cases.');
   }
   data.buildSpec={...before.data.buildSpec,...update.data.buildSpec};
  }
  if(data.parentBlockId===null)delete data.parentBlockId;
  const after={...before,data};nodes.set(update.id,after);
  changes.push({kind:'block',id:update.id,before,after});
 }
 touched.clear();
 for(const update of rows(draft.updateEdges,600,'interface amendment')){
  keys(update,['id','interfaceSpec'],'interface amendment');
  const before=edges.get(update.id);
  if(!before||touched.has(update.id)||!object(update.interfaceSpec)||!Object.keys(update.interfaceSpec).length)throw Error('Each interface amendment must name one existing interface exactly once.');
  touched.add(update.id);
  const after={...before,interfaceSpec:{...before.interfaceSpec,...update.interfaceSpec}};
  edges.set(update.id,after);changes.push({kind:'interface',id:update.id,before,after});
 }
 return {nodes:[...nodes.values(),...draft.addNodes],edges:[...edges.values(),...draft.addEdges],changes};
}

export function allocateRequirements(requirements,coverage){
 return requirements.map(row=>{
  const links=[...new Set([...(row.links||[]),...coverage.filter(item=>item.id===row.id).flatMap(item=>item.links)])];
  return links.length===(row.links||[]).length?row:{...row,links};
 });
}

// A bounded audit log retains changes and original artifact references. Full
// authored documents remain in their immutable server captures, not duplicated.
export function validateAmendmentHistory(history){
 if(history===undefined)return [];
 if(!Array.isArray(history)||history.length>40||new TextEncoder().encode(JSON.stringify(history)).length>500_000
   ||history.some((row,index)=>!object(row)||row.version!==1||typeof row.artifactId!=='string'||!row.artifactId||row.artifactId.length>150
     ||!/^[a-f0-9]{64}$/.test(row.draftSha256)||row.contextSha256!=null&&!/^[a-f0-9]{64}$/.test(row.contextSha256)
     ||!Number.isInteger(row.baseRevision)||row.baseRevision<1||index>0&&row.baseRevision<=history[index-1].baseRevision
     ||!Array.isArray(row.changes)||row.changes.length>800||!Array.isArray(row.coverage)||row.coverage.length>800))throw Error('Architecture amendment history is invalid or exceeds its receiving bound. Preserve the captured artifacts; no history was discarded.');
 return history;
}

export function appendAmendment(project,receipt){
 const old=project.extensions?.architectureDocuments;
 const previousDocuments=old?{artifactId:old.artifactId,draftSha256:old.draftSha256,contextSha256:old.contextSha256,
   files:old.files.map(({path,sha256})=>({path,sha256}))}:undefined;
 return validateAmendmentHistory([...(validateAmendmentHistory(project.extensions?.architectureAmendments)),
  {...receipt,...(previousDocuments?{previousDocuments}:{})}]);
}
