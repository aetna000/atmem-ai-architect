// Source-backed design amendments. Identity, ownership and accepted scope are not
// model-writable through this channel; new allocation evidence is separate.
import {sha256} from '@noble/hashes/sha2.js';
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
    const removed=(before.data.buildSpec?.verificationCases||[]).filter(row=>!retained.has(row.id)).map(row=>row.id);
    if(removed.length){
     const error=Error('A refinement cannot silently remove verification cases. Retain their IDs in the named module.');
     error.canvasDiagnostic=JSON.stringify({code:'verification_case_removal',blockId:update.id,caseIds:removed});throw error;
    }
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

// Add missing blocker allocations without rewriting an owner's question or
// extending an old answer to newly affected scope. Only unanswered gates qualify.
export function allocateQuestions(project,coverage,{requirements,edges,nodes,sourceDigests,slotMode}){
 const questions=project.openQuestions||[],byId=new Map(questions.map(q=>[q.id,q])),touched=new Set(),changes=[];
 const inventories={requirementIds:new Set(requirements.map(r=>r.id)),interfaceIds:new Set(edges.map(e=>e.id)),links:new Set(nodes.filter(n=>n.data.kind!=='note').map(n=>n.id))};
 for(const row of rows(coverage,60,'question coverage')){
  keys(row,['id','sourceSlot','sourceSha256','reference','requirementIds','interfaceIds','links'],'question coverage');
  const before=byId.get(row.id),sourceSha256=slotMode&&Number.isInteger(row.sourceSlot)&&row.sourceSha256===undefined?sourceDigests[row.sourceSlot-1]:!slotMode?row.sourceSha256:undefined;
  if(!before||touched.has(row.id)||before.status==='answered'||before.answer?.trim()||!sourceDigests.includes(sourceSha256)
    ||typeof row.reference!=='string'||!row.reference.trim()||row.reference.length>400)throw Error('Question coverage needs one unanswered saved gate and an exact source reference.');
  touched.add(row.id);let linked=0;const additions={};
  for(const [field,known] of Object.entries(inventories)){
   const values=row[field]??[];
   if(!Array.isArray(values)||values.length>50||values.some(id=>!known.has(id)))throw Error('Question coverage refers to an unknown or excess '+field+'.');
   linked+=values.length;
   const merged=[...new Set([...(before[field]||[]),...values])];
   if(merged.length>50)throw Error('Question coverage exceeds its explicit allocation bound. No links were discarded.');
   if(values.length)additions[field]=merged;
  }
  if(!linked)throw Error('Question coverage needs an affected requirement, interface or component.');
  const after={...before,...additions};byId.set(row.id,after);
  changes.push({kind:'questionCoverage',id:row.id,sourceSha256,reference:row.reference,
   before:Object.fromEntries(Object.keys(inventories).map(k=>[k,before[k]||[]])),after:Object.fromEntries(Object.keys(inventories).map(k=>[k,after[k]||[]]))});
 }
 return {questions:questions.map(q=>byId.get(q.id)),changes};
}

// A bounded audit log retains changes and original artifact references. Full
// authored documents remain in their immutable server captures, not duplicated.
export function validateAmendmentHistory(history){
 if(history===undefined)return [];
 if(!Array.isArray(history)||history.length>40||new TextEncoder().encode(JSON.stringify(history)).length>500_000
   ||history.some((row,index)=>!object(row)||row.version!==1||typeof row.artifactId!=='string'||!row.artifactId||row.artifactId.length>150
     ||!/^[a-f0-9]{64}$/.test(row.draftSha256)||row.contextSha256!=null&&!/^[a-f0-9]{64}$/.test(row.contextSha256)
     ||!Number.isInteger(row.baseRevision)||row.baseRevision<1||index>0&&row.baseRevision<=history[index-1].baseRevision
     ||!Array.isArray(row.changes)||row.changes.length>800||row.changes.some(change=>!validReferences(change,row))
     ||!Array.isArray(row.coverage)||row.coverage.length>800)){
  const error=Error('Architecture amendment history is invalid or exceeds its receiving bound. Preserve the captured artifacts; no history was discarded.');
  error.hostStorageBound=true;throw error;
 }
 return history;
}

// Large before/after values are already retained in the exact submission and
// captured canvas. Reference those immutable records instead of copying a whole
// module's specification into every history entry. Existing history is untouched.
const bytes=value=>new TextEncoder().encode(JSON.stringify(value));
const fingerprint=value=>{const content=bytes(value);return {sha256:Array.from(sha256(content),b=>b.toString(16).padStart(2,'0')).join(''),bytes:content.length};};
function validReferences(change,receipt){
 if(!object(change)||!change.beforeRef&&!change.afterRef)return true; // Legacy inline receipts remain readable.
 const {beforeRef:before,afterRef:after}=change;
 const collection=change.kind==='block'?'nodes':change.kind==='interface'?'edges':null;
 return collection&&typeof change.id==='string'&&!Object.hasOwn(change,'before')&&!Object.hasOwn(change,'after')
  &&[before,after].every(ref=>object(ref)&&/^[a-f0-9]{64}$/.test(ref.sha256)&&Number.isSafeInteger(ref.bytes)&&ref.bytes>0)
  &&before.contextSha256===receipt.contextSha256&&/^[a-f0-9]{64}$/.test(before.contextSha256)
  &&before.collection==='design.'+collection&&before.id===change.id
  &&after.artifactId===receipt.artifactId&&after.draftSha256===receipt.draftSha256
  &&after.path==='architecture.canvas.json'&&after.collection===(collection==='nodes'?'updateNodes':'updateEdges')
  &&after.id===change.id&&after.mode==='merge-with-before';
}
function referenceLargeChanges(receipt){
 if(!/^[a-f0-9]{64}$/.test(receipt.contextSha256||''))return receipt;
 return {...receipt,changes:receipt.changes.map(change=>{
  if(!['block','interface'].includes(change.kind)||!change.before||!change.after||bytes(change).length<=8_000)return change;
  const {before,after,...identity}=change,collection=change.kind==='block'?'nodes':'edges';
  return {...identity,beforeRef:{...fingerprint(before),contextSha256:receipt.contextSha256,collection:'design.'+collection,id:change.id},
   afterRef:{...fingerprint(after),artifactId:receipt.artifactId,draftSha256:receipt.draftSha256,path:'architecture.canvas.json',
    collection:collection==='nodes'?'updateNodes':'updateEdges',id:change.id,mode:'merge-with-before'}};
 })};
}

export function appendAmendment(project,receipt){
 const old=project.extensions?.architectureDocuments;
 const previousDocuments=old?{artifactId:old.artifactId,draftSha256:old.draftSha256,contextSha256:old.contextSha256,
   files:old.files.map(({path,sha256})=>({path,sha256}))}:undefined;
 return validateAmendmentHistory([...(validateAmendmentHistory(project.extensions?.architectureAmendments)),
  {...referenceLargeChanges(receipt),...(previousDocuments?{previousDocuments}:{})}]);
}
