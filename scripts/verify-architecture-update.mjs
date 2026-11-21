// Independent preservation oracle for a source-backed architecture update.
// Reads original snapshots directly; no generator, importer or normalizer is used.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isDeepStrictEqual} from 'node:util';
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const shape=value=>value.format?{id:value.meta.id,revision:value.meta.revision,name:value.meta.name,provider:value.design.provider,
 nodes:value.design.nodes,edges:value.design.edges,needs:value.requirements,decisions:value.decisions,openQuestions:value.openQuestions,extensions:value.extensions}:value;
const before=shape(read(process.argv[2])),after=shape(read(process.argv[3]));
const unique=(rows,label)=>{const ids=new Set(rows.map(row=>row.id));assert.equal(ids.size,rows.length,`Unique ${label}`);return new Map(rows.map(row=>[row.id,row]));};
assert.equal(after.id,before.id);assert.equal(after.name,before.name);assert.equal(after.provider,before.provider);
assert.ok(Number.isInteger(after.revision)&&after.revision>before.revision,'New design revision');
const nodes=unique(after.nodes,'blocks'),edges=unique(after.edges,'interfaces'),requirements=unique(after.needs||[],'requirements');
const protectedNode=node=>{const {description,buildSpec,parentBlockId,...data}=node.data;return {...node,data};};
const protectedEdge=edge=>{const {interfaceSpec,...rest}=edge;return rest;};
const history=after.extensions.architectureAmendments,latest=history.at(-1),quality=after.extensions.architectureDraftQuality;
assert.equal(latest.artifactId,quality.artifactId);assert.equal(latest.draftSha256,quality.draftSha256);
assert.equal(latest.contextSha256,quality.contextSha256);
assert.ok(latest.baseRevision>=before.revision&&latest.baseRevision<after.revision,'Amendment revision binding');
for(const old of before.nodes){
 const current=nodes.get(old.id);assert.ok(current,`Preserve block ${old.id}`);
 assert.deepEqual(protectedNode(current),protectedNode(old),`Preserve block identity, placement, runtime and ownership: ${old.id}`);
 if(!isDeepStrictEqual(current,old)){
  const evidence=latest.changes.find(change=>change.kind==='block'&&change.id===old.id);
  assert.ok(evidence,`Amended block has a receipt: ${old.id}`);assert.deepEqual(evidence.before,old);assert.deepEqual(evidence.after,current);
 }
}
for(const old of before.edges){
 const current=edges.get(old.id);assert.ok(current,`Preserve interface ${old.id}`);assert.deepEqual(protectedEdge(current),protectedEdge(old));
 if(!isDeepStrictEqual(current,old)){
  const evidence=latest.changes.find(change=>change.kind==='interface'&&change.id===old.id);
  assert.ok(evidence,`Amended interface has a receipt: ${old.id}`);assert.deepEqual(evidence.before,old);assert.deepEqual(evidence.after,current);
 }
}
for(const old of before.needs||[]){
 const current=requirements.get(old.id);assert.ok(current,`Preserve requirement ${old.id}`);
 const {links,...accepted}=old,{links:allocated,...retained}=current;
 assert.deepEqual(retained,accepted,`Preserve accepted requirement content: ${old.id}`);assert.ok((links||[]).every(id=>allocated.includes(id)));
}
for(const key of ['decisions','openQuestions']){
 const records=unique(after[key]||[],key);for(const old of before[key]||[])assert.deepEqual(records.get(old.id),old,`Preserve ${key}: ${old.id}`);
}
const sources=after.extensions.designSources;
for(const old of before.extensions.designSources)assert.deepEqual(sources.find(row=>row.sha256===old.sha256),old,'Preserve original source evidence');
if(process.argv[4])assert.ok(sources.some(row=>row.sha256===process.argv[4]),'Expected new source received');
for(const edge of edges.values())assert.ok(nodes.has(edge.source)&&nodes.has(edge.target),'Valid interface endpoints');
for(const row of requirements.values())assert.ok(row.links?.every(id=>nodes.has(id)),'Valid responsibility allocations');
for(const row of latest.coverage){assert.ok(requirements.has(row.id));assert.ok(sources.some(source=>source.sha256===row.sourceSha256));assert.ok(row.links.every(id=>nodes.has(id)));}
console.log(JSON.stringify({status:'passed',preservedBlocks:before.nodes.length,preservedInterfaces:before.edges.length,
 preservedRequirements:before.needs?.length||0,resultBlocks:after.nodes.length,resultInterfaces:after.edges.length,resultRequirements:after.needs.length,
 sources:sources.length,amendedBlocks:latest.changes.filter(row=>row.kind==='block').length,amendedInterfaces:latest.changes.filter(row=>row.kind==='interface').length,
 boundary:'Snapshot preservation and receipt identity only. Source interpretation, compatibility, implementation and runtime quality require independent review.'},null,2));
