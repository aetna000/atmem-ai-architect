import test from 'node:test';import assert from 'node:assert/strict';
import {composeTerraformUnits,deliveryUnitName} from '../src/terraform-composition.mjs';
import {relocateTerraformTemplate} from '../src/terraform-expressions.mjs';
import {terraformSketch} from '../src/terraform.mjs';import {invoiceProject} from './fixtures/invoice-project.mjs';import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';
const container=(provider,id)=>({id:'composition-client',version:1,revision:3,name:'Unfamiliar scientific instrument',provider,requirements:'Keep ownership and operate the supplied instrument image.',nodes:[{id,position:{x:0,y:0},data:{label:'Independent instrument service',kind:'resource',provider,origin:'proposed',implementation:'container-service',service:CONTAINER_SERVICES[provider].service}}],edges:[]});
const unit=(p,implementation)=>({id:p.nodes.find(n=>n.data.implementation)?.id,implementation,files:terraformSketch(p)});
test('expression relocation changes references, never literal/escaped text or object attributes',()=>{
 const names={region:'unit__region',enabled:'unit__enabled',map:'unit__map'};
 assert.equal(relocateTerraformTemplate('Literal var.region and $${var.region}; ${format("var.region:%s",var.region)}',names),'Literal var.region and $${var.region}; ${format("var.region:%s",var.unit__region)}');
 assert.equal(relocateTerraformTemplate('${jsonencode({"nested" = "${var.region}", literal="var.region", value=var.map["var.region"], other=object.var.region})}',names),'${jsonencode({"nested" = "${var.unit__region}", literal="var.region", value=var.unit__map["var.region"], other=object.var.region})}');
 assert.equal(relocateTerraformTemplate('%{ if var.enabled }${var.region}%{ endif }',names),'%{ if var.unit__enabled }${var.unit__region}%{ endif }');
 assert.throws(()=>relocateTerraformTemplate('${var.missing}',names),/Undeclared/);assert.throws(()=>relocateTerraformTemplate('${var.region',names),/Unterminated/);
});
for(const cloud of ['aws','azure','gcp','ibm'])test(cloud+': invoice plus unfamiliar supplied-image service preserve isolated source, exact providers, inputs and protections',()=>{
 const p=invoiceProject(cloud),a=unit(p,'invoice-workflow'),b=unit(container(cloud,'instrument-µ'),'container-service'),before=structuredClone([a,b]);
 const files=composeTerraformUnits(p,[a,b]),tf=JSON.parse(files['main.tf.json']),manifest=JSON.parse(files['composition.json']);assert.deepEqual([a,b],before);
 assert.equal(Object.keys(tf.module).length,2);assert.equal(manifest.units.length,2);assert.equal(tf.variable.review_approved.default,false);assert.deepEqual(tf.locals.unfinished_work,[]);
 for(const u of manifest.units){const original=[a,b].find(v=>v.id===u.id),child=JSON.parse(files[u.path+'/main.tf.json']);assert.equal(child.provider,undefined);assert.deepEqual(child.resource,JSON.parse(original.files['main.tf.json']).resource);assert.equal(tf.module[u.module].source,'./'+u.path);assert.equal(tf.module[u.module].review_approved,'${var.review_approved}');for(const file of Object.keys(original.files))if(file!=='main.tf.json')assert.equal(files[u.path+'/'+file],original.files[file]);}
 const flipped=composeTerraformUnits({...p,name:'Unrelated water quality business'},[b,a]);assert.equal(flipped['main.tf.json'],files['main.tf.json']);
 assert(Object.values(tf.provider).every(v=>v.length>=1));assert(Object.keys(tf.variable).some(v=>v.endsWith('__runtime_image')));assert(Object.keys(tf.variable).some(v=>v.endsWith('__block_696e737472756d656e742dc2b5_image')));
 assert(JSON.parse(composeTerraformUnits(p,[a,b],{environment:'production'})['main.tf.json']).locals.unfinished_work.includes('composition-state-custody-and-operations-review-required'));
});
test('cross-provider and repeated capabilities compose by declared unit identity, without provider fallback',()=>{
 const a=unit(container('aws','shared-one'),'container-service'),b=unit(container('gcp','shared-two'),'container-service'),c=unit(container('aws','shared-three'),'container-service');
 const f=composeTerraformUnits({revision:5},[a,b,c]),tf=JSON.parse(f['main.tf.json']);assert.deepEqual(Object.keys(tf.terraform.required_providers).sort(),['aws','google']);assert.equal(tf.provider.aws.length,2);assert.equal(tf.provider.google.length,1);assert.equal(new Set(Object.values(tf.module).map(m=>m.source)).size,3);
});
test('unknown scope, incompatible reviewed providers, duplicate identities and unsafe package paths cannot disappear',()=>{
 const a=unit(invoiceProject('ibm'),'invoice-workflow'),b=unit(container('ibm','instrument'),'container-service');b.files['.terraform.lock.hcl']=b.files['.terraform.lock.hcl'].replace('2.9.0','1.89.0');assert.throws(()=>composeTerraformUnits({revision:1},[a,b]),/Conflicting reviewed provider versions/);
 const x=unit(container('gcp','x'),'container-service'),y=unit(container('gcp','y'),'container-service');assert.throws(()=>composeTerraformUnits({},[x,x]),/Duplicate/);
 const config=JSON.parse(x.files['main.tf.json']);config.locals.unfinished_work=['required-network'];x.files['main.tf.json']=JSON.stringify(config);const tf=JSON.parse(composeTerraformUnits({},[x,y],{gaps:['required-interface']})['main.tf.json']);assert(tf.locals.unfinished_work.includes('required-interface'));assert(tf.locals.unfinished_work.includes(deliveryUnitName('x')+':required-network'));
 y.files['../escape']='no';assert.throws(()=>composeTerraformUnits({},[x,y]),/unsupported path/);delete y.files['../escape'];
 const bad=JSON.parse(y.files['main.tf.json']);bad.terraform.backend={local:{}};y.files['main.tf.json']=JSON.stringify(bad);assert.throws(()=>composeTerraformUnits({},[x,y]),/state custody/);
 assert.notEqual(deliveryUnitName('µ'),deliveryUnitName('u'));assert.throws(()=>deliveryUnitName('x'.repeat(513)),/clipped/);
});
