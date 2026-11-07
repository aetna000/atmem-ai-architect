import test from 'node:test';
import assert from 'node:assert/strict';
import {template,pdmTemplate,validateImport,CLOUDS} from '../src/core.mjs';
import {toProjectFile,fromProjectFile,parseProjectFile,findCredentials,FORMAT,FORMAT_VERSION} from '../src/project-file.mjs';
import {newRequirement,newAssumption,newQuestion,reviseDecision} from '../src/records.mjs';
import {defaultAssessment,newDecision} from '../src/engagement.mjs';

function rich(p){
  p={...p,brief:{client:'Client Co',strategicIntent:'Fewer outages'},useCases:[{id:'uc-1',title:'Predict failures',value:'High',risk:'Medium',fit:'High',verdict:'Pursue',reason:'Clear value'}],gate:{adoption:'Two planners'},assessment:defaultAssessment()};
  p.assessment.scores.aws.cost=4;
  p.needs=[newRequirement({id:'req-1',statement:'Alerts within 2 s',measure:{metric:'p95 latency',op:'<=',target:2,unit:'s'},links:[p.nodes[0].id]})];
  p.assumptions=[newAssumption({id:'asm-1',statement:'500 pumps',owner:'Matt',madeAt:'2026-11-01',links:[p.nodes[0].id]})];
  p.openQuestions=[newQuestion({id:'q-1',question:'Which region?',owner:'Client IT'})];
  p.decisions=[{...newDecision(p,{title:'Region',subject:'cloud.region',status:'Accepted',decision:'eu-west-1',date:'2026-11-01'})}];
  return validateImport(reviseDecision(p,'adr-001',{decision:'eu-central-1'},'Data residency'));
}
const designs=[...['aws','azure','gcp','ibm','tools'].map(c=>template(c)),...CLOUDS.map(c=>pdmTemplate(c))];
for(const [i,p] of designs.entries())test(`round-trip keeps every user field (${p.name} #${i})`,()=>{
  const original=rich(p);
  const file=JSON.parse(JSON.stringify(toProjectFile(original)));
  assert.equal(file.format,FORMAT);assert.equal(file.formatVersion,FORMAT_VERSION);
  const {project,migrated}=fromProjectFile(file);
  assert.equal(migrated,false);
  const {id,createdAt,...back}=project;
  assert.deepEqual(back,original);
  assert.ok(id&&createdAt);
  // Second round trip is stable, including identity.
  const again=fromProjectFile(JSON.parse(JSON.stringify(toProjectFile(project)))).project;
  assert.deepEqual(again,project);
});
test('workbench v1 files migrate and say so',()=>{
  const {project,migrated,from}=fromProjectFile(JSON.parse(JSON.stringify(pdmTemplate('gcp'))));
  assert.equal(migrated,true);assert.equal(from,'workbench v1');assert.equal(project.nodes.length,11);
});
test('newer major versions are refused, newer minor versions keep unknown fields',()=>{
  const file=toProjectFile(pdmTemplate());
  assert.throws(()=>fromProjectFile({...file,formatVersion:'3.0.0'}),/format 3.0.0.*reads 2.3.0/);
  const {project,migrated}=fromProjectFile({...file,formatVersion:'2.9.0',futureSection:{a:1},meta:{...file.meta,colour:'teal'}});
  assert.equal(migrated,true);
  assert.deepEqual(project.extensions.futureSection,{a:1});assert.deepEqual(project.extensions['meta.extra'],{colour:'teal'});
  const out=toProjectFile(project);assert.deepEqual(out.extensions.futureSection,{a:1});
});
test('credentials block export and import and name the field',()=>{
  const p=pdmTemplate();p.nodes[0].data.description='key AKIAABCDEFGHIJKLMNOP';
  assert.throws(()=>toProjectFile(p),/design.nodes\[0\].data.description looks like a credential/);
  const file=toProjectFile(pdmTemplate());file.extensions={password:'hunter2'};
  assert.throws(()=>fromProjectFile(file),/extensions.password/);
  assert.deepEqual(findCredentials({token:''}),[]);
  assert.ok(findCredentials({a:'-----BEGIN RSA PRIVATE KEY-----'}).length);
});
test('limits: size, component and connection counts, broken files',()=>{
  assert.throws(()=>parseProjectFile(' '.repeat(2_000_001)),/2 MB/);
  const file=toProjectFile(pdmTemplate());
  const many={...file,design:{...file.design,nodes:Array.from({length:201},(_, i)=>({...file.design.nodes[0],id:`n${i}`}))}};
  assert.throws(()=>fromProjectFile(many),/oversized/);
  assert.throws(()=>fromProjectFile({...file,design:{...file.design,edges:[{id:'x',source:'nope',target:'sensors'}]}}),/Invalid connection/);
  assert.throws(()=>fromProjectFile({format:'something.else'}),/Not an AtMem AI Architect project file/);
});
import {clientPack} from '../src/pack.mjs';
test('the pack prints requirements, assumptions, open questions and only current decisions with history',()=>{
  const md=clientPack(rich(pdmTemplate()),null);
  assert.match(md,/\| Alerts within 2 s \| NFR · performance \| should \| p95 latency <= 2s/);
  assert.match(md,/500 pumps _\(stated 2026-11-01, Matt\)_/);
  assert.match(md,/- Which region\? _\(Client IT\)_/);
  assert.match(md,/ADR-002 · Region/);assert.match(md,/_Changed because: Data residency_/);assert.match(md,/ADR-001 \(2026-11-01, superseded\): eu-west-1/);
  assert.doesNotMatch(md,/### ADR-001/);
});

test('legacy project identity imports and exports with the new brand without losing data',()=>{
 const p={version:1,revision:1,name:'Existing user project',provider:'tools',nodes:[],edges:[],requirements:'Keep existing work',extensions:{requirementComments:[{id:'feedback',text:'Keep this comment'}]}};
 const file=toProjectFile(p);assert.equal(file.format,'atmem.ai-architect.project');
 const old={...file,format:'atforma.project'};
 const loaded=fromProjectFile(old);assert.equal(loaded.migrated,true);
 assert.equal(loaded.project.name,p.name);assert.equal(loaded.project.extensions.requirementComments[0].text,'Keep this comment');
 assert.equal(toProjectFile(loaded.project).format,'atmem.ai-architect.project');
});
