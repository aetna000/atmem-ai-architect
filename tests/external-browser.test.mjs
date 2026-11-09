import test from 'node:test';
import assert from 'node:assert/strict';
import {resourcePlan} from '../src/resources.mjs';
const browser={id:'browser',position:{x:0,y:0},data:{label:'Visitor browser',kind:'resource',provider:'tools',origin:'existing',binding:'web-browser'}};
const app={id:'app',position:{x:100,y:0},data:{label:'Cloud Run',kind:'resource',provider:'gcp',origin:'proposed',service:'Google Cloud Run'}};
test('external browser needs no import; application and connection gaps remain',()=>{
 const plan=resourcePlan({nodes:[browser,app],edges:[{id:'https',source:'browser',target:'app',label:'HTTPS'}]});
 assert.equal(plan.rows[0].externalReference,true);assert.match(plan.rows[0].terraform,/no infrastructure/);
 assert.ok(!plan.gapDetails.some(g=>g.componentIds?.includes('browser')));
 assert.ok(plan.gapDetails.some(g=>g.componentIds?.includes('app')));
 assert.ok(plan.gapDetails.some(g=>g.edgeIds?.includes('https')));
});
test('proposed browser and untyped existing service cannot evade implementation checks',()=>{
 assert.throws(()=>resourcePlan({nodes:[{...browser,data:{...browser.data,origin:'proposed'}}],edges:[]}),/Reference bindings/);
 for(const data of [{...browser.data,binding:undefined}]){
  const plan=resourcePlan({nodes:[{...browser,data}],edges:[]});assert.ok(plan.gapDetails.some(g=>g.componentIds?.includes('browser')));
 }
});

test('legacy external browser can receive a typed correction without hiding application gaps',async()=>{
 const {emulationPrompt,guardEmulationCorrection}=await import('../src/emulation-feedback.mjs');
 const before={nodes:[{...browser,data:{...browser.data,binding:undefined}},app],edges:[]};
 const report={status:'blocked',checks:[],blockers:['browser']};
 const prompt=emulationPrompt(before,report);
 const evidence=JSON.parse(prompt.split('Evidence: ')[1]);
 assert.deepEqual(evidence.externalClients,[{id:'browser',label:'Visitor browser',binding:null}]);
 const after=structuredClone(before);after.nodes[0].data.binding='web-browser';
 assert.equal(guardEmulationCorrection(before,after),true);
 assert.equal(resourcePlan(before).gapDetails.length-resourcePlan(after).gapDetails.length,1);
 assert.ok(resourcePlan(after).gapDetails.some(g=>g.componentIds?.includes('app')));
});
