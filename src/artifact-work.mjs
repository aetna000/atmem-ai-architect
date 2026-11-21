// Backend-issued file/context bindings remain proposed architecture metadata.
// This is not a signature, execution result or business acceptance mechanism.
import {architectureSources,canonicalWork,captureWorkSources,synchronizeEngineeringIntent,validateArchitectureWork} from './architecture-work.mjs';
import {findCredentials} from './project-file.mjs';

const hash=async text=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(b=>b.toString(16).padStart(2,'0')).join('');
const same=(a,b)=>canonicalWork(a)===canonicalWork(b);
const sourceMap=(project,ids)=>architectureSources(project).filter(e=>!ids.has(e.id));
function contextProject(file){
 // Context comparison must use the exact saved semantics. The legacy diagram
 // importer normalizes runtime settings and recognized adapter enums; applying
 // those compiler transformations here could hide a newly supplied contract.
 if(!['atmem.ai-architect.project','atforma.project'].includes(file.format)||!file.meta||!Array.isArray(file.design?.nodes)||!Array.isArray(file.design?.edges))throw Error('Invalid saved architecture context.');
 const d=file.discovery||{};
 return {id:file.meta.id,provider:file.design.provider||'tools',requirements:d.problem||'',nodes:file.design.nodes,edges:file.design.edges,
  ...Object.fromEntries(['brief','useCases','facts','workflow'].filter(k=>d[k]!==undefined).map(k=>[k,d[k]])),...(file.meta.domain?{domain:file.meta.domain}:{}),
  needs:file.requirements||[],assumptions:file.assumptions||[],openQuestions:file.openQuestions||[],decisions:file.decisions||[],extensions:file.extensions||{}};
}

export async function verifyArtifactWork(receipt){
 if(receipt?.status!=='prepared'||typeof receipt.content!=='string'||new TextEncoder().encode(receipt.content).length>6_000_000||await hash(receipt.content)!==receipt.sha256)throw Error('The mapping receipt digest did not match. No mappings were changed.');
 const payload=JSON.parse(receipt.content);
 const keys=['format','version','projectId','sessionId','runId','artifactId','artifactSha256','proposalSha256','context','events','proposal','files','definitionSha256','boundary'];
 if(Object.keys(payload).some(k=>!keys.includes(k))||keys.some(k=>!(k in payload))||payload.format!=='atmem.architecture-proposal'||payload.version!==1||payload.boundary!=='artifact_file_binding_only')throw Error('Unsupported artifact mapping receipt.');
 if(payload.context?.projectId!==payload.projectId||typeof payload.context?.content!=='string'||await hash(payload.context.content)!==payload.context.sha256)throw Error('The saved context digest did not match this receipt.');
 if(findCredentials(payload).length)throw Error('Mapping receipt contains data that looks like a credential.');
 return {id:receipt.id,receiptSha256:receipt.sha256,payload};
}

export function applyArtifactWork(project,owner,verified,{now=new Date()}={}){
 if(project.id!==owner)return project;
 const {id,receiptSha256,payload:p}=verified;
 if(p.projectId!==owner||p.context?.projectId!==owner||p.boundary!=='artifact_file_binding_only')throw Error('This mapping receipt belongs to a different project.');
 if(p.proposal?.version!==1||!Array.isArray(p.proposal.records)||!p.proposal.records.length||p.proposal.records.length>200||Object.keys(p.proposal).some(k=>!['version','records'].includes(k)))throw Error('Invalid artifact work proposal.');
 const records=p.proposal.records.map(r=>({...r,source:'agent',agreement:'proposed'})),ids=new Set(records.map(r=>'work:'+r.id));
 if(ids.size!==records.length)throw Error('Repeated work mapping identity.');
 let basis=contextProject(JSON.parse(p.context.content));
 if(basis.id!==owner)throw Error('Saved mapping context belongs to another project.');
 // Merge exact durable client events on both sides; a late reply never replaces
 // newer local requirements, another session's intent or a switched project.
 basis=synchronizeEngineeringIntent(basis,p.sessionId,p.events,owner);
 const current=synchronizeEngineeringIntent(project,p.sessionId,p.events,owner);
 if(!same(sourceMap(current,ids),sourceMap(basis,ids)))throw Error('The design changed since this package was built. Regenerate against the current requirements before linking mappings.');
 const state=validateArchitectureWork(current.extensions?.architectureWork);
 const existing=state.artifactMappings.find(m=>m.id===id);
 if(existing){if(existing.receiptSha256!==receiptSha256||!same(existing.records,records)||existing.artifactSha256!==p.artifactSha256)throw Error('A mapping receipt cannot change identity.');return current;}
 const byId=new Map(state.records.map(r=>[r.id,r]));
 for(const record of records){
  const old=byId.get(record.id);
  if(old){
   const prior=state.artifactMappings.findLast(m=>m.records.some(r=>r.id===record.id));
   if(!prior||old.source!=='agent'||old.agreement!=='proposed'||!same(old,prior.records.find(r=>r.id===record.id))||prior.sessionId!==p.sessionId)throw Error('A generated mapping conflicts with an existing or accepted record. Keep both histories and resolve the identity explicitly.');
  }
  byId.set(record.id,record);
 }
 const sourceState={...state,records:[...byId.values()]};
 const sources=architectureSources({...current,extensions:{...current.extensions,architectureWork:sourceState}});
 const known=new Set(sources.map(s=>s.id));
 for(const record of records){
  if(record.dependsOn.some(ref=>!known.has(ref)))throw Error('The proposal names a missing requirement, block, interface or work reference.');
  const paths=record.data?.files||[];
  if(record.kind==='implementation'&&!paths.length)throw Error('Implementation mappings must name captured artifact files.');
  if(!Array.isArray(paths)||new Set(paths).size!==paths.length||paths.some(path=>!p.files.some(f=>f.path===path)))throw Error('A proposed mapping lacks an actual artifact file binding.');
 }
 const captured=captureWorkSources(state,sourceMap(current,ids));
 const mapping={id,receiptSha256,sessionId:p.sessionId,runId:p.runId,artifactId:p.artifactId,artifactSha256:p.artifactSha256,proposalSha256:p.proposalSha256,
  contextId:p.context.id,contextRevision:p.context.revision,contextSha256:p.context.sha256,definitionSha256:p.definitionSha256,
  records,files:p.files,sourceSnapshotIds:captured.ids,recordedAt:now.toISOString(),scope:'artifact_file_binding_only'};
 const next={...sourceState,snapshots:captured.snapshots,artifactMappings:[...state.artifactMappings,mapping]};
 const validated=validateArchitectureWork(next);
 return {...current,extensions:{...current.extensions,architectureWork:validated}};
}

export function artifactWorkProjection(project){
 const state=validateArchitectureWork(project.extensions?.architectureWork),sources=architectureSources(project),byId=new Map(sources.map(s=>[s.id,s]));
 const mappings=state.artifactMappings.map(m=>{
  const ids=new Set(m.records.map(r=>'work:'+r.id)),expected=m.sourceSnapshotIds.map(id=>state.snapshots.find(s=>s.id===id).value);
  const before=new Map(expected.map(s=>[s.id,s])),after=new Map(sources.filter(s=>!ids.has(s.id)).map(s=>[s.id,s]));
  const changedRefs=[...new Set([...before.keys(),...after.keys()])].filter(ref=>!same(before.get(ref),after.get(ref))).sort();
  for(const record of m.records)if(!same(byId.get('work:'+record.id)?.value,record))changedRefs.push('work:'+record.id);
  const newer=state.artifactMappings.findLast(x=>x.sessionId===m.sessionId).artifactId!==m.artifactId;
  return {...m,contextStatus:newer?'superseded':changedRefs.length?'changed':'current',changedRefs:[...new Set(changedRefs)]};
 });
 const coverage=sources.filter(s=>['requirement','responsibility','interface'].includes(s.kind)&&!s.id.startsWith('work:')).map(source=>{
  const references=[];
  for(const mapping of mappings.filter(m=>m.contextStatus==='current'))for(const record of mapping.records.filter(r=>r.kind==='implementation')){
   const pending=[...record.dependsOn],seen=new Set();let linked=false;
   while(pending.length){
    const ref=pending.pop();if(seen.has(ref))continue;seen.add(ref);if(ref===source.id)linked=true;
    const entry=byId.get(ref);
    // Broad change dependencies (for example an unscoped ADR) are not claims
    // that one implementation covers every requirement in that context.
    if(ref.startsWith('work:'))pending.push(...(entry?.value.dependsOn||[]));
    else if(ref.startsWith('block:'))pending.push(...(project.needs||[]).filter(r=>r.links?.includes(ref.slice(6))).map(r=>'requirement:'+r.id));
    else if(ref.startsWith('interface:')&&entry)pending.push('block:'+entry.value.source,'block:'+entry.value.target);
   }
   if(linked)references.push({recordId:record.id,artifactId:mapping.artifactId,files:record.data.files||[]});
  }
  return {ref:source.id,title:source.title,status:references.length?'file_reference_linked':'unmapped',references};
 });
 return {format:'atmem.architecture-artifact-mappings',version:1,projectId:project.id,mappings,coverage,
  boundary:'References to server-bound artifact files and saved context, not execution, acceptance or compiler coverage. Reopened project metadata is not an authenticated receipt; use the owning session service to reverify it.'};
}
