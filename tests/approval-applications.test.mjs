import test from 'node:test';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';
import {approvalProject,approvalTemplateProject} from './fixtures/approval-project.mjs';
import {approvalProfiles,validateApprovalProfile} from '../src/approval-applications.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';import {terraformSketch} from '../src/terraform.mjs';import {resourcePlan} from '../src/resources.mjs';import {generationQuality} from '../src/generation-quality.mjs';import {deliveryPack} from '../src/delivery.mjs';import {resourceAddress} from '../src/identifiers.mjs';import {reviewWorkContext,architectureWork} from '../src/architecture-work.mjs';
for(const provider of ['aws','azure','gcp','ibm'])test(provider+': selected profile survives import/export and emits source without false infrastructure completion',()=>{
 const p=approvalProject(provider),original=structuredClone(p),saved=toProjectFile(p),reopened=fromProjectFile(saved).project;
 assert.equal(saved.formatVersion,'3.0.0');
 assert.equal(fromProjectFile(saved).migrated,false);
 assert.deepEqual(reopened.nodes[0].data.approvalProfile,p.nodes[0].data.approvalProfile);assert.equal(reopened.nodes[0].data.implementation,'approval-workflow');
 const files=terraformSketch(p),root='applications/'+resourceAddress(p.nodes[0].id)+'/',quality=JSON.parse(files['generation-quality.json']);
 assert.deepEqual(JSON.parse(files[root+'application-profile.json']),p.nodes[0].data.approvalProfile);assert(files[root+'api.py'].includes('create_native_api'));
 assert(files[root+'Dockerfile'].includes('api:app_factory'));assert.equal(JSON.parse(files[root+'assembly-status.json']).workerEntrypoint,null);
 assert.equal(quality.infrastructureComplete,false);assert(quality.findings.some(f=>f.code==='application-resource-linkage-required'));
 assert.deepEqual(p,original);
});
test('an explicit approval contract cannot become a bucket through a stale service label',()=>{
 const p=approvalProject();p.nodes[0].data.service='Amazon S3';p.nodes[0].data.label='Amazon S3';const plan=resourcePlan(p),files=terraformSketch(p);
 assert.equal(plan.rows[0].implemented,false);assert(!JSON.parse(files['main.tf.json']).resource?.aws_s3_bucket);
 plan.rows[0].implemented=true;assert(generationQuality(p,plan,files).fatalFindings.some(f=>f.code==='unregistered-implementation'));
});
test('profiles cannot claim existing systems, notes, different identities or providers',()=>{
 for(const update of [{origin:'existing'},{provider:'azure'},{kind:'note'},{binding:'existing-service'}]){
  const p=approvalProject();Object.assign(p.nodes[0].data,update);assert.throws(()=>approvalProfiles(p));
 }
 const p=approvalProject();p.nodes[0].data.approvalProfile.componentId='another';assert.throws(()=>toProjectFile(p));
});
test('profile changes invalidate reviewed context without deleting earlier evidence',()=>{
 let p=approvalProject();p=reviewWorkContext(p,'block:'+p.nodes[0].id,{recordedBy:'user'});
 p.nodes[0].data.approvalProfile.operationKind='account_change';
 assert.equal(architectureWork(p).entities.find(e=>e.id==='block:'+p.nodes[0].id).contextStatus,'changed');
});
test('Spec Kit includes concrete source/task paths with domain and resource work pending',()=>{
 const p=approvalProject(),files=deliveryPack(p,null,'staging'),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks;
 const assembly=tasks.find(t=>t.id.startsWith('TASK-APP-ASSEMBLY-'));assert(assembly);assert(assembly.files.some(p=>p.endsWith('/api.py')));assert(assembly.dependsOn.every(id=>tasks.some(t=>t.id===id)));
 const parent=tasks.find(t=>t.id.startsWith('TASK-RESOURCE-')&&t.componentIds?.includes(p.nodes[0].id));assert(parent.dependsOn.includes(assembly.id));assert(!assembly.dependsOn.includes(parent.id));
 const map=JSON.parse(files['spec-kit/implementation-map.json']);assert.equal(map.components[0].applicationImplementation,'shared_api_assembly_only');
});
test('browser and pure native declaration validators agree on valid and invalid metadata',()=>{
 const valid=approvalProject().nodes[0].data.approvalProfile,corpus=[valid];
 for(const change of [v=>v.provider='other',v=>v.payloadContract.version=true,v=>v.payloadContract.source.properties.itemId.maxBytes=1.5,v=>v.destinationContract.payloadContractSha256='f'.repeat(64),v=>v.componentId='界'.repeat(171),v=>v.identitySettings.token='forbidden',v=>v.operationKind='execute',v=>v.publicOrigin='http://public.example',v=>v.payloadContract.result.additionalProperties=true]){const value=structuredClone(valid);change(value);corpus.push(value);}
 const js=corpus.map(value=>{try{validateApprovalProfile(value);return true;}catch{return false;}});
 const code='import json,sys;from src.runtime.workflow_profile import ApplicationProfile;values=json.load(sys.stdin);out=[]\nfor value in values:\n try:ApplicationProfile(value);out.append(True)\n except (ValueError,TypeError):out.append(False)\nprint(json.dumps(out))';
 const result=spawnSync('python3',['-c',code],{input:JSON.stringify(corpus),encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.deepEqual(JSON.parse(result.stdout),js);assert.deepEqual(js,[true,...Array(corpus.length-1).fill(false)]);
});
for(const provider of ['aws','azure','gcp','ibm'])test(provider+': native output references survive model/export without invented profile values',()=>{
 const {project}=approvalTemplateProject(provider),saved=toProjectFile(project),reopened=fromProjectFile(saved).project,files=terraformSketch(reopened),root='applications/'+resourceAddress(project.nodes[0].id)+'/';
 assert.deepEqual(reopened.nodes[0].data.approvalProfile,project.nodes[0].data.approvalProfile);assert.equal(saved.formatVersion,'3.0.0');
 assert(files[root+'application-template.json']);assert(!files[root+'application-profile.json']);assert(files[root+'resolve-profile.py']);
 assert(files[root+'api.py'].includes('load_bound_profile'));assert.equal(JSON.parse(files[root+'assembly-status.json']).bindingStatus,'unresolved');
 assert(files[root+'Dockerfile'].includes('application-template.json'));
});
test('output references require their exact graph owner/provider and affect context currency',()=>{
 const {project}=approvalTemplateProject();let reviewed=reviewWorkContext(project,'block:'+project.nodes[0].id);
 reviewed.nodes[1].data.description='Identity owner/configuration changed';assert.equal(architectureWork(reviewed).entities.find(e=>e.id==='block:'+project.nodes[0].id).contextStatus,'changed');
 for(const mutation of ['missing','provider','environment','sensitive']){
  const {project}=approvalTemplateProject(),ref=project.nodes[0].data.approvalProfile.identitySettings.POOL_ID.nativeOutput;
  if(mutation==='missing')ref.componentId='absent';else if(mutation==='provider')ref.provider='azure';else if(mutation==='environment')ref.environment='production';else ref.name='client_secret';
  assert.throws(()=>approvalProfiles(project));
 }
});

test('deferred browser/native validators agree on public fields and policy counterexamples',()=>{
 const valid=approvalTemplateProject().project.nodes[0].data.approvalProfile,corpus=[valid];
 for(const mutate of [v=>v.accountId=v.publicOrigin,v=>v.operationKind=v.publicOrigin,v=>v.identitySettings.POOL_ID.nativeOutput.environment='production',v=>v.identitySettings.POOL_ID.nativeOutput.provider='gcp',v=>v.identitySettings.POOL_ID.nativeOutput.name='client_secret',v=>v.destinationContract.mappingVersion=v.publicOrigin,v=>v.destinationContract.scope=v.publicOrigin]){const value=structuredClone(valid);mutate(value);corpus.push(value);}
 const js=corpus.map(value=>{try{validateApprovalProfile(value);return true;}catch{return false;}});
 const code='import json,sys;from src.runtime.workflow_bindings import application_declaration;values=json.load(sys.stdin);out=[]\nfor value in values:\n try:application_declaration(value);out.append(True)\n except (ValueError,TypeError):out.append(False)\nprint(json.dumps(out))';
 const result=spawnSync('python3',['-c',code],{input:JSON.stringify(corpus),encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.deepEqual(JSON.parse(result.stdout),js);assert.deepEqual(js,[true,false,false,false,false,false,false,true]);
 const p=approvalTemplateProject().project,files=deliveryPack(p,null,'staging'),tasks=JSON.parse(files['spec-kit/tasks.json']).tasks,assembly=tasks.find(t=>t.id.startsWith('TASK-APP-ASSEMBLY-'));
 const binding=tasks.find(t=>t.id.startsWith('TASK-APP-BINDING-'));assert(binding.steps.some(s=>s.includes('resolve-profile.py')));assert(binding.dependsOn.includes(assembly.id));assert(!assembly.dependsOn.includes(binding.id));assert(tasks.find(t=>t.id==='TASK-E2E').dependsOn.includes(binding.id));
 const visit=(id,chain=[])=>{assert(!chain.includes(id),'Task cycle: '+[...chain,id].join(' -> '));const task=tasks.find(t=>t.id===id);assert(task,'Missing task '+id);for(const dep of task.dependsOn)visit(dep,[...chain,id]);};for(const task of tasks)visit(task.id);
assert(assembly.files.some(s=>s.endsWith('/application-template.json')));assert(!assembly.files.some(s=>s.endsWith('/application-profile.json')));
});
