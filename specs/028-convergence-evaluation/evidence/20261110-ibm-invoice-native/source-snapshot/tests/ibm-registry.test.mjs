import test from'node:test';
import assert from'node:assert/strict';
import {ibmRegistryHost,ibmRegistryHostExpression}from'../src/ibm-registry.mjs';
import {terraformSketch}from'../src/terraform.mjs';
import {ibmStructuredProject}from'./fixtures/ibm-structured-project.mjs';
import {publicFaqProject}from'./fixtures/public-faq-project.mjs';

test('IBM regional registries use documented domains and cannot infer a global fallback',()=>{
 assert.equal(ibmRegistryHost('au-syd'),'au.icr.io');assert.equal(ibmRegistryHost('eu-de'),'de.icr.io');assert.equal(ibmRegistryHost('jp-osa'),'jp2.icr.io');assert.equal(ibmRegistryHost('ca-mon'),'ca2.icr.io');
 for(const region of ['global','us-east','au-syd.icr.io','unknown','${file("private")}'])assert.throws(()=>ibmRegistryHost(region));
 assert.throws(()=>ibmRegistryHostExpression('var.region);file("private")'));
});
test('both existing IBM application families retain actual regional registry mapping in generated exports',()=>{
 for(const project of [ibmStructuredProject(),publicFaqProject('ibm')]){
  const files=terraformSketch(project),config=JSON.parse(files['main.tf.json']),app=Object.values(config.resource.ibm_code_engine_app)[0];
  assert.ok(app.image_reference.startsWith('${lookup('));assert.ok(app.image_reference.includes('"au-syd":"au.icr.io"'));assert.ok(!app.image_reference.includes('${var.region}.icr.io/'));assert.match(config.variable.region.validation.condition,/au-syd/);
 }
});
