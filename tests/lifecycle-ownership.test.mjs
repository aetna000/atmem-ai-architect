import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';
import {importPulumiSnapshot,snapshotToProject} from '../src/pulumi.mjs';import {validateImport} from '../src/core.mjs';import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
import {resourcePlan} from '../src/resources.mjs';import {terraformSketch} from '../src/terraform.mjs';import {generationQuality} from '../src/generation-quality.mjs';import {agentContext} from '../src/local-agent.mjs';
import {architectureWork,reviewWorkContext} from '../src/architecture-work.mjs';
import {resourceAddress} from '../src/identifiers.mjs';
import {specKit} from '../src/spec-kit.mjs';
const types={aws:'aws:ecs/service:Service',azure:'azure-native:app:ContainerApp',gcp:'gcp:cloudrunv2/service:Service',ibm:'ibm:codeengine:App'};
for(const provider of Object.keys(types))test(provider+': observed state and explicit reference markers remain external beside a new supplied-image deployment',()=>{
 const urn='urn:pulumi:dev::external-platform::'+types[provider]+'::preserved-runtime',p=compositionFixture(provider),imported=snapshotToProject(importPulumiSnapshot({resources:[{urn,type:types[provider],inputs:{secret:'must-not-retain'},outputs:{token:'must-not-retain'}}]})),node=imported.nodes[0];
 Object.assign(node.data,{service:CONTAINER_SERVICES[provider].service,implementation:'container-service',deploymentMode:'reference'});p.nodes.push(node);p.extensions=imported.extensions;const before=structuredClone(p);
 const saved=fromProjectFile(toProjectFile(validateImport(p))).project;assert.deepEqual(saved.extensions.externalReferences,p.extensions.externalReferences);assert(agentContext(saved).some(r=>r.text.includes(urn)));assert(!JSON.stringify(saved).includes('must-not-retain'));
 const plan=resourcePlan(p),files=terraformSketch(p),reference=JSON.parse(files['existing-references.json']).references.find(r=>r.id===node.id),inventory=JSON.parse(files['deployment-ownership.json']).components;
 assert.equal(plan.rows.find(r=>r.id===node.id).implemented,true);assert.equal(reference.identity.externalId,urn);assert.equal(reference.provision,false);assert.equal(reference.import,false);assert.equal(reference.behaviorValidated,false);assert.deepEqual(inventory.find(r=>r.id===node.id).managedAddresses,[]);assert.equal(inventory.find(r=>r.id===node.id).disposition,'reference_only');assert.equal(inventory.find(r=>r.id==='instrument-µ').disposition,'existing_source_new_deployment');assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);assert.deepEqual(p,before);
 const changed=structuredClone(p);changed.nodes.at(-1).data={...changed.nodes.at(-1).data,origin:'proposed',deploymentMode:'create',binding:undefined};assert.throws(()=>validateImport(changed),/External state provenance/);assert.throws(()=>resourcePlan(changed),/External state provenance/);
});
test('Pulumi identities are retained exactly or rejected without clipping or choosing duplicate owners',()=>{
 const type=types.aws,urn='urn:pulumi:dev::external-platform::'+type+'::resource';
 for(const input of [[{urn:urn+'x'.repeat(600),type}],[{urn,type:'x'.repeat(201)}],[{urn:'urn:pulumi:dev::project::'+type+'::'+'x'.repeat(151),type}],[{urn,type},{urn,type}]]){
  const raw={resources:input},before=structuredClone(raw);assert.throws(()=>importPulumiSnapshot(raw),/nothing was clipped|Duplicate Pulumi/);assert.deepEqual(raw,before);
 }
 assert.throws(()=>importPulumiSnapshot({resources:[null]}),/no resource was silently discarded/);
});
test('root and child state adoption/move/removal cannot hide behind valid module addresses',()=>{
 const p=compositionFixture('gcp'),plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units[0];
 for(const key of ['main.tf.json',unit.path+'/main.tf.json'])for(const operation of ['import','moved','removed']){
  const changed={...files},config=JSON.parse(files[key]);config[operation]=[{to:'${google_cloud_run_v2_service.foreign}',id:'foreign-object'}];changed[key]=JSON.stringify(config);assert(generationQuality(p,plan,changed).fatalFindings.some(f=>f.code==='ownership-transition-unreviewed'),operation);
 }
});
test('external identity changes invalidate context review and retain the original snapshots',()=>{
 const p=compositionFixture('gcp');p.extensions={externalReferences:{version:1,references:[{componentId:'observed',source:'pulumi-stack-export',externalId:'urn:pulumi:dev::platform::gcp:cloudrunv2/service:Service::first',resourceType:types.gcp}]}};p.nodes.push({id:'observed',position:{x:0,y:0},data:{kind:'resource',label:'Existing deployment',provider:'gcp',origin:'existing',binding:'existing-service'}});
 const reviewed=reviewWorkContext(p,'block:observed'),before=structuredClone(reviewed.extensions.architectureWork);reviewed.extensions.externalReferences.references[0].externalId+='-changed';const entity=architectureWork(reviewed).entities.find(e=>e.id==='block:observed');assert.equal(entity.contextStatus,'changed');assert(entity.changedRefs.includes('block:observed'));assert.deepEqual(reviewed.extensions.architectureWork,before);
});
test('preserved components cannot gain managed addresses or forged adoption claims',()=>{
 const p=compositionFixture('gcp');p.nodes.push({id:'preserved',position:{x:0,y:0},data:{kind:'resource',label:'Existing service',provider:'gcp',origin:'existing',binding:'existing-service'}});const plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units[0],key=unit.path+'/main.tf.json',tf=JSON.parse(files[key]);
 tf.resource.google_cloud_run_v2_service[resourceAddress('preserved')]={name:'foreign',location:'europe-west1'};assert(generationQuality(p,plan,{...files,[key]:JSON.stringify(tf)}).fatalFindings.some(f=>f.code==='existing-resource-managed'));
 const inventory=JSON.parse(files['deployment-ownership.json']);inventory.migrationAuthorized=true;assert(generationQuality(p,plan,{...files,'deployment-ownership.json':JSON.stringify(inventory)}).fatalFindings.some(f=>f.code==='ownership-inventory-mismatch'));
 const kit=specKit(p,{snapshotId:'ownership',stamp:'Synthetic lifecycle handoff',environment:'staging',now:new Date('2026-11-12T00:00:00Z')});const tasks=JSON.parse(kit['spec-kit/tasks.json']).tasks;assert(tasks.filter(t=>t.id.startsWith('TASK-RESOURCE-')).every(t=>t.files.includes('terraform/deployment-ownership.json')));
});
