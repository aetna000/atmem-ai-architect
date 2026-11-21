import test from 'node:test';
import assert from 'node:assert/strict';
import {resourcePlan} from '../src/resources.mjs';
import {terraformSketch} from '../src/terraform.mjs';
import {existingReference} from '../src/existing-references.mjs';
import {validateImport} from '../src/core.mjs';
import {toAgentProject} from '../src/local-agent.mjs';
import {CLOUD_STORAGE_SCENARIOS} from '../src/cloud-storage-scenarios.mjs';
const site={id:'existing-site',position:{x:0,y:0},data:{label:'atmem.ai',kind:'resource',provider:'gcp',origin:'existing',service:'Firebase Hosting'}};
const app={id:'app',position:{x:300,y:0},data:{label:'Cloud Run',kind:'resource',provider:'gcp',origin:'proposed',service:'Google Cloud Run'}};
const project={version:1,revision:12,name:'Existing Firebase site',provider:'gcp',nodes:[site,app],edges:[{id:'website-api',source:site.id,target:app.id,label:'Authenticated API'}]};
test('existing Firebase site is preserved while application and integration gaps remain',()=>{
 const plan=resourcePlan(project);assert.ok(plan.rows[0].existingServiceReference);assert.deepEqual(plan.rows[0].resources,[]);
 assert.ok(!plan.gapDetails.some(g=>g.componentIds?.includes(site.id)));
 assert.ok(plan.gapDetails.some(g=>g.componentIds?.includes(app.id)));
 assert.ok(plan.gapDetails.some(g=>g.edgeIds?.includes('website-api')));
 const files=terraformSketch(project);const tf=JSON.parse(files['main.tf.json']);
 assert.deepEqual(Object.keys(tf.resource),['terraform_data']);assert.equal(tf.import,undefined);
 const ref=JSON.parse(files['existing-references.json']).references[0];assert.equal(ref.provision,false);assert.equal(ref.import,false);assert.equal(ref.behaviorValidated,false);
});
test('explicit references survive project and agent boundaries without changing cloud ownership',()=>{
 const p=structuredClone(project);p.nodes[0].data.service='Existing Cloud Run';p.nodes[0].data.binding='existing-service';
 const clean=validateImport(p),agent=toAgentProject(clean);assert.equal(agent.nodes[0].data.binding,'existing-service');assert.equal(agent.nodes[0].data.provider,'gcp');
 assert.ok(resourcePlan(clean).rows[0].existingServiceReference);
});
test('labels, proposed services and implementation conflicts cannot bypass checks',()=>{
 for(const data of [{...site.data,origin:'proposed'},{...site.data,service:undefined},{...site.data,implementation:'private-object-storage'},{...site.data,origin:'proposed',binding:'existing-service'}])assert.equal(existingReference({...site,data}),null);
});
test('storage exports preserve references without treating their edges as implemented',()=>{
 const p=structuredClone(CLOUD_STORAGE_SCENARIOS.find(s=>s.id==='gcp').project);p.nodes.push(site);
 let plan=resourcePlan(p);assert.equal(plan.gapDetails.length,0);assert.ok(plan.rows.find(r=>r.id===site.id).existingServiceReference);
 const files=terraformSketch(p);assert.ok(files['existing-references.json']);assert.ok(!JSON.stringify(JSON.parse(files['main.tf.json']).resource).includes('existing-site'));
 p.edges.push({id:'site-store',source:site.id,target:'documents',label:'Read'});plan=resourcePlan(p);assert.ok(plan.gapDetails.some(g=>g.edgeIds?.includes('site-store')));
});
