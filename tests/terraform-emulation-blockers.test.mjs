import test from 'node:test';import assert from 'node:assert/strict';
import{describeTerraformBlockers,applyBlockers}from'../src/terraform-emulation-blockers.mjs';
import{terraformSketch}from'../src/terraform.mjs';
const project={version:1,revision:1,name:'Claims architecture',provider:'tools',nodes:[{id:'claims-api',type:'resource',position:{x:0,y:0},data:{label:'Claims API',kind:'resource',provider:'tools'}}],edges:[]};
test('a blocked generated design retains every gate item with readable component guidance',()=>{
 const files=terraformSketch(project),ids=JSON.parse(files['main.tf.json']).locals.unfinished_work;
 const rows=describeTerraformBlockers(files,project);assert.deepEqual(rows.map(r=>r.id),ids);
 assert.ok(rows.some(r=>r.componentIds?.includes('claims-api')&&r.message.includes('Claims API')&&r.action));
 assert.ok(rows.some(r=>r.id==='provider-workload-implementation-required'&&r.category==='generator_support'));
 assert.deepEqual(JSON.parse(files['main.tf.json']).locals.unfinished_work,ids);
});
test('empty-resource blocked reports still expose all blockers, with explicit fallback for legacy reports',()=>{
 const report={status:'blocked',resources:[],blockers:['first','unknown'],blockerDetails:[{id:'first',message:'Caller access contract is missing.',action:'Define a caller.'}]};
 assert.deepEqual(applyBlockers(report),[{id:'first',message:'Caller access contract is missing.',action:'Define a caller.'},{id:'unknown',message:'unknown'}]);
 assert.deepEqual(applyBlockers({blockers:['legacy']}),[{id:'legacy',message:'legacy'}]);assert.deepEqual(applyBlockers(null),[]);
});
test('unknown gate items remain visible rather than being silently discarded',()=>{
 const rows=describeTerraformBlockers({'main.tf.json':JSON.stringify({locals:{unfinished_work:['future-gap']}})},project);assert.equal(rows[0].id,'future-gap');assert.equal(rows[0].message,'future-gap');assert.ok(rows[0].action);
});
