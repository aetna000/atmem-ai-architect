import test from 'node:test';
import assert from 'node:assert/strict';
import {pdmTemplate,checkProject,orderProject,executeBlock,validateImport,propose,CLOUDS} from '../src/core.mjs';
import {systemView} from '../src/levels.mjs';
import {defaultAssessment,optionScore,recommendationDecision,keepEngagement,cleanEngagement} from '../src/engagement.mjs';
import {clientPack,OPTION_NAMES} from '../src/pack.mjs';
// Mirrors the browser runner: inputs from every parent are merged.
function run(p,scenario='happy'){const out={},errors={};for(const n of orderProject(p)){const parents=p.edges.filter(e=>e.target===n.id);if(parents.some(e=>errors[e.source]||!(e.source in out))&&parents.length){errors[n.id]='skipped';continue;}try{out[n.id]=executeBlock(n,parents.length?Object.assign({},...parents.map(e=>out[e.source])):null,scenario);}catch(e){errors[n.id]=e.message;}}return {out,errors};}
for(const cloud of CLOUDS)test(`${cloud}: predictive maintenance passes all success measures`,()=>{
  const p=pdmTemplate(cloud);
  assert.deepEqual(checkProject(p).filter(i=>i.level==='error'),[]);
  const {out,errors}=run(p);assert.deepEqual(errors,{});
  assert.equal(out.measures.status,'passed');assert.ok(out.measures.measures.every(m=>m.pass));
  assert.ok(p.nodes.filter(n=>n.data.provider===cloud).length>=9);
  assert.doesNotThrow(()=>validateImport(p));
});
const failures={'sensor-dropout':['features',/coverage 55%/],'weak-model':['measures',/Model precision = 0.72/],drift:['monitor',/Drift detected/],ungrounded:['guardrail',/Guardrail blocked/],denied:['guardrail',/Access denied/],'tool-error':['app',/unavailable/]};
for(const [scenario,[block,message]] of Object.entries(failures))test(`${scenario} is caught at ${block}`,()=>{
  const {errors}=run(pdmTemplate('azure'),scenario);assert.match(errors[block],message);
});
test('validateImport keeps PoC scope, existing blocks and measures, and drops bad measures',()=>{
  const p=pdmTemplate('gcp');p.nodes.find(n=>n.id==='measures').data.measures.push({label:'x',path:'a;b',op:'>=',target:1});
  const q=validateImport(p);const m=q.nodes.find(n=>n.id==='measures').data;
  assert.equal(m.measures.length,4);assert.equal(q.nodes.find(n=>n.id==='app').data.origin,'existing');assert.equal(q.nodes.find(n=>n.id==='sensors').data.poc,true);
});
test('system view has an ML pipeline layer',()=>assert.ok(systemView(pdmTemplate()).nodes.some(n=>n.data.label==='ML pipeline')));
test('architect drafts maintenance on any of the four clouds and opens options on compare',()=>{
  for(const cloud of ['AWS','Azure','Google Cloud','IBM']){const r=propose(`Predictive maintenance on ${cloud}`,pdmTemplate());assert.equal(r.next.domain,'maintenance');}
  assert.equal(propose('Compare all four clouds',pdmTemplate()).action,'options');
});
test('scorecard needs every weighted criterion and feeds a decision',()=>{
  const p={...pdmTemplate(),assessment:defaultAssessment()};
  assert.equal(optionScore(p.assessment,'aws'),null);
  Object.assign(p.assessment.scores.aws,{cost:3,risk:4,scalability:5,security:4});p.assessment.weights.cost=2;
  assert.equal(optionScore(p.assessment,'aws'),3.8);
  const d=recommendationDecision(p,'aws',OPTION_NAMES);assert.match(d.title,/predictive maintenance: AWS/);assert.match(d.options,/AWS: 3.8/);
});
test('engagement survives proposals and is sanitised on import',()=>{
  const cur={...pdmTemplate(),requirements:'Client words',decisions:[{id:'adr-001',title:'t',status:'Accepted'}],brief:{client:'Client Co'}};
  const next=keepEngagement(pdmTemplate('ibm'),cur);assert.equal(next.decisions.length,1);assert.equal(next.brief.client,'Client Co');assert.equal(next.requirements,'Client words');
  const e=cleanEngagement({decisions:[{status:'Hacked',title:'<x>'}],assessment:{scores:{aws:{cost:9}}}});
  assert.equal(e.decisions[0].status,'Proposed');assert.equal(e.assessment.scores.aws.cost,null);
});
test('client pack covers every deliverable',()=>{
  const p=pdmTemplate();const md=clientPack({...p,brief:{client:'Client Co'}},null);
  for(const h of ['## Summary','## Discover','## Design','### Target architecture','```mermaid','### Cloud options','### Success criteria','### Security, governance and responsible AI','## Build','Scale gate','## Decisions'])assert.ok(md.includes(h),h);
  assert.match(md,/Prepared for Client Co/);assert.match(md,/Not tested on this revision/);
});
