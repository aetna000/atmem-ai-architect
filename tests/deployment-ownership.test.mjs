import test from 'node:test';import assert from 'node:assert/strict';
import {validateImport} from '../src/core.mjs';import {toAgentProject} from '../src/local-agent.mjs';import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';
const project=()=>({version:1,revision:1,name:'Existing source',provider:'gcp',nodes:[{id:'app',position:{x:0,y:0},data:{label:'Architect',provider:'gcp',kind:'resource',origin:'existing',service:'Google Cloud Run',implementation:'container-service',deploymentMode:'create'}}],edges:[]});
test('existing source can create a cloud deployment without changing its ownership',()=>{
 const p=validateImport(project());assert.equal(p.nodes[0].data.origin,'existing');assert.equal(toAgentProject(p).nodes[0].data.deploymentMode,'create');const row=resourcePlan(p).rows[0];assert.equal(row.existing,false);assert.equal(row.sourceExisting,true);assert.ok(JSON.parse(terraformSketch(p)['main.tf.json']).resource.google_cloud_run_v2_service);
});
test('existing cloud deployment is preserved and create/reference conflict is rejected',()=>{
 const p=project();delete p.nodes[0].data.deploymentMode;assert.equal(resourcePlan(p).rows[0].existing,true);assert.equal(JSON.parse(terraformSketch(p)['main.tf.json']).resource.google_cloud_run_v2_service,undefined);p.nodes[0].data.deploymentMode='create';p.nodes[0].data.binding='existing-service';assert.throws(()=>validateImport(p),/without an external reference/);
});
test('imported Pulumi state remains external metadata, never a proposed replacement',async()=>{
 const {snapshotToProject}=await import('../src/pulumi.mjs');
 const p=snapshotToProject({resources:[{id:'observed',name:'existing-documents',provider:'aws',type:'aws:s3/bucket:Bucket'}]});
 assert.equal(p.nodes[0].data.origin,'existing');const row=resourcePlan(p).rows[0];assert.equal(row.existing,true);assert.equal(row.foundation,false);assert.equal(JSON.parse(terraformSketch(p)['main.tf.json']).resource.aws_s3_bucket,undefined);
 p.nodes[0].data.origin='imported Pulumi state';delete p.nodes[0].data.binding;assert.equal(resourcePlan(p).rows[0].existing,true);assert.ok(resourcePlan(p).rows[0].existingServiceReference);
});
