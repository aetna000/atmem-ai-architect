import assert from 'node:assert/strict';
import {existsSync,readFileSync,realpathSync,statSync} from 'node:fs';
import {resolve,sep} from 'node:path';
import {createHash} from 'node:crypto';

const root=realpathSync(resolve(process.argv[2]||'.'));
function file(relative) {
  assert.equal(typeof relative,'string');
  assert.ok(!relative.includes('\\')&&relative.split('/').every(part=>part&&part!=='.'&&part!=='..'));
  const path=resolve(root,relative);
  assert.ok(path.startsWith(root+sep)&&existsSync(path)&&realpathSync(path).startsWith(root+sep)&&statSync(path).isFile(),relative);
  return path;
}
const json=name=>JSON.parse(readFileSync(file(name),'utf8'));
const unique=(rows,label)=>{
  const ids=new Set(rows.map(row=>row.id));
  assert.equal(ids.size,rows.length,`Unique ${label}`);
  return ids;
};

const manifest=json('manifest.json');
const project=json('project.atmem-ai-architect.json');
const {tasks}=json('spec-kit/tasks.json');
const progress=json('spec-kit/progress.json');
const {components}=json('spec-kit/blocks/index.json');
const quality=json('spec-kit/architecture-coverage.json');
const amendments=project.extensions?.architectureAmendments;
if(amendments?.length){
  assert.deepEqual(json('spec-kit/architecture-amendments.json').revisions,amendments);
  const latest=amendments.at(-1);
  assert.equal(latest.artifactId,quality.artifactId);
  assert.equal(latest.draftSha256,quality.draftSha256);
  for(const revision of amendments)for(const change of revision.changes){
    assert.equal(change.before.id,change.id);assert.equal(change.after.id,change.id);
    if(change.kind==='block'){
      const protectedNode=node=>{const {description,buildSpec,parentBlockId,...data}=node.data;return {...node,data};};
      assert.deepEqual(protectedNode(change.after),protectedNode(change.before),'Block identity, ownership and runtime preserved');
    }else{
      assert.equal(change.kind,'interface');
      const {interfaceSpec:before,...old}=change.before,{interfaceSpec:after,...current}=change.after;
      assert.deepEqual(current,old,'Interface endpoints and identity preserved');
    }
  }
}
const documents=project.extensions?.architectureDocuments;
if(documents?.files?.length){
  const receipt=json('design-documents-receipt.json');
  assert.equal(receipt.artifactId,documents.artifactId);
  assert.equal(receipt.draftSha256,quality.draftSha256);
  assert.equal(receipt.files.length,documents.files.length);
  for(const document of documents.files){
    const exported=receipt.files.find(row=>row.path===document.path);
    assert.ok(exported,`Missing captured design document ${document.path}`);
    const expected=document.path==='README.md'?'NATIVE_DESIGN.md':document.path;
    assert.equal(exported.exportPath,expected);
    const bytes=readFileSync(file(expected));
    assert.equal(createHash('sha256').update(bytes).digest('hex'),document.sha256);
    assert.equal(bytes.toString('utf8'),document.content);
    assert.ok(manifest.files.includes(expected));
  }
}
manifest.files.forEach(file);
assert.equal(manifest.projectId,project.meta.id);
assert.equal(manifest.designRevision,project.meta.revision);
assert.equal(manifest.deploymentExecuted,false);
assert.ok(typeof quality.draftSha256==='string'&&/^[a-f0-9]{64}$/.test(quality.draftSha256));
const ids=unique(project.design.nodes,'block IDs');
const requirements=unique(project.requirements,'requirement IDs');
const taskIds=unique(tasks,'task IDs');
assert.deepEqual(unique(progress.tasks,'progress records'),taskIds);
const byTask=new Map(tasks.map(task=>[task.id,task]));
const seen=new Set(),active=new Set();
function visit(id) {
  assert.ok(!active.has(id),`Task cycle at ${id}`);
  if(seen.has(id))return;
  assert.ok(byTask.has(id),`Unknown task ${id}`);
  active.add(id);
  byTask.get(id).dependsOn.forEach(visit);
  active.delete(id);seen.add(id);
}
tasks.forEach(task=>{
  visit(task.id);
  task.specFiles?.forEach(file);
  assert.ok(task.requirementIds?.every(id=>requirements.has(id))??true);
});
const byBlock=new Map(components.map(block=>[block.id,block]));
const architectural=project.design.nodes.filter(node=>node.data.kind!=='note');
assert.equal(components.length,architectural.length);
for(const block of components){
  assert.ok(ids.has(block.id));
  assert.ok(block.taskIds.length&&block.taskIds.every(id=>taskIds.has(id)));
  assert.ok(block.requirementIds.every(id=>requirements.has(id)));
  let cursor=block,depth=0;
  while(cursor.parent){
    assert.ok(byBlock.has(cursor.parent)&&depth++<components.length,`Invalid ancestry at ${block.id}`);
    cursor=byBlock.get(cursor.parent);
  }
  assert.equal(depth,block.depth);
  for(const name of ['spec.md','plan.md','infrastructure-devops.md','testing.md','scenarios.md','tasks.json','WORK_ORDER.md'])file(`${block.path}/${name}`);
}
unique(project.design.edges,'interface IDs');
assert.ok(project.design.edges.every(edge=>ids.has(edge.source)&&ids.has(edge.target)));
const sources=project.extensions?.designSources||[];
assert.ok(sources.length&&sources.every(source=>/^[a-f0-9]{64}$/.test(source.sha256)));
const traced=project.requirements.filter(row=>sources.some(source=>row.basis?.includes(source.sha256)));
assert.ok(traced.length&&traced.every(row=>row.links?.length&&row.links.every(id=>ids.has(id))));
assert.ok(sources.every(source=>traced.some(row=>row.basis.includes(source.sha256))));

const mmd=manifest.files.filter(name=>name.endsWith('.mmd'));
assert.ok(mmd.some(name=>name.startsWith('spec-kit/system/')&&name.endsWith('-sequence.mmd')));
assert.ok(mmd.some(name=>name.startsWith('spec-kit/system/')&&name.endsWith('-functional.mmd')));
assert.ok(mmd.some(name=>name.startsWith('spec-kit/system/')&&name.endsWith('-events.mmd')));
console.log(JSON.stringify({status:'structural_checks_passed',blocks:components.length,interfaces:project.design.edges.length,
  requirements:requirements.size,nonfunctionalRequirements:project.requirements.filter(row=>row.kind==='nonfunctional').length,
  sourceDocuments:sources.length,tasks:tasks.length,diagrams:mmd.length,score:quality.score,
  reviewCaptured:quality.reviewCaptured,coverageStatus:quality.status,boundary:'File, trace and graph assertions only. No implementation, capacity or site execution claim.'},null,2));
