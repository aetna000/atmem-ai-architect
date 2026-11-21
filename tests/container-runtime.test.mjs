import test from 'node:test';import assert from 'node:assert/strict';
import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';
import {resourcePlan} from '../src/resources.mjs';import {terraformSketch} from '../src/terraform.mjs';
import {generationQuality} from '../src/generation-quality.mjs';
import {validateImport} from '../src/core.mjs';import {containerRuntime} from '../src/container-runtime.mjs';
const MiB=2**20,GiB=2**30;
const cases={aws:[512*MiB,'512','256'],azure:[1536*MiB,'1.5Gi',0.75],gcp:[6*GiB,'6144Mi','2'],ibm:[2e9,'2G','0.5']};
for(const [provider,[bytes,memory,cpu]]of Object.entries(cases))test(provider+': exact memory lowers in standalone and mixed units without changing ownership or requirements',()=>{
 const p=compositionFixture(provider),node=p.nodes.at(-1);node.data.config={containerMemoryBytes:bytes,...(provider==='aws'?{logRetentionDays:90}:{})};const before=structuredClone(p);
 for(const project of [p,{...p,nodes:[node],edges:[]}]){
  const plan=resourcePlan(project),files=terraformSketch(project),unit=plan.composition?.units.find(u=>u.id===node.id),tf=JSON.parse(files[(unit?unit.path+'/':'')+'main.tf.json']);
  assert.deepEqual(plan.gaps,[]);assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,true);
  const address=plan.rows.find(r=>r.id===node.id).address;
  if(provider==='aws'){assert.equal(tf.resource.aws_ecs_task_definition[address].memory,memory);assert.equal(tf.resource.aws_ecs_task_definition[address].cpu,cpu);assert.equal(tf.resource.aws_cloudwatch_log_group[address].retention_in_days,90);}
  if(provider==='azure'){assert.equal(tf.resource.azurerm_container_app[address].template.container.memory,memory);assert.equal(tf.resource.azurerm_container_app[address].template.container.cpu,cpu);}
  if(provider==='gcp')assert.deepEqual(tf.resource.google_cloud_run_v2_service[address].template.containers.resources.limits,{cpu,memory});
  if(provider==='ibm'){assert.equal(tf.resource.ibm_code_engine_app[address].scale_memory_limit,memory);assert.equal(tf.resource.ibm_code_engine_app[address].scale_cpu_limit,cpu);}
 }
 assert.deepEqual(p,before);assert.equal(validateImport(p).nodes.at(-1).data.config.containerMemoryBytes,bytes);
});
test('exact unsupported or conflicting quantities remain blocked; decimal and binary units never substitute',()=>{
 for(const [provider,bytes]of [['aws',768*MiB],['azure',5*GiB],['ibm',GiB]]){
  const p=compositionFixture(provider);p.nodes.at(-1).data.config={containerMemoryBytes:bytes};const before=structuredClone(p),plan=resourcePlan(p),files=terraformSketch(p);assert(plan.gaps.some(g=>g.includes('no exact supported')));assert.equal(JSON.parse(files['generation-quality.json']).infrastructureComplete,false);assert(JSON.parse(files['main.tf.json']).locals.unfinished_work.some(g=>g.includes('containerMemoryBytes')));assert.deepEqual(p,before);
 }
 const p=compositionFixture('gcp');p.nodes.at(-1).data.config={memoryMb:1024,containerMemoryBytes:1e9};assert(resourcePlan(p).gaps.some(g=>g.includes('conflicts')));
});
test('memoryMb keeps MiB semantics, small Cloud Run selects generation1, and unsupported behavior remains explicit',()=>{
 for(const provider of ['aws','azure','gcp']){const p=compositionFixture(provider);p.nodes.at(-1).data.config={memoryMb:1024};assert.equal(containerRuntime(p.nodes.at(-1)).memoryBytes,GiB);assert.deepEqual(resourcePlan(p).gaps,[]);}
 const p=compositionFixture('gcp');p.nodes.at(-1).data.config={containerMemoryBytes:128*MiB,concurrency:7};assert.equal(containerRuntime(p.nodes.at(-1)).executionEnvironment,'EXECUTION_ENVIRONMENT_GEN1');assert(resourcePlan(p).gaps.some(g=>g.includes('concurrency=7')));
 p.nodes[1].data.config.containerMemoryBytes=GiB;assert.throws(()=>validateImport(p),/explicit container-service/);
});

for(const provider of Object.keys(cases))test(provider+': independent inspection detects dropped memory, public ingress and default identities',()=>{
 const p=compositionFixture(provider),node=p.nodes.at(-1);node.data.config={containerMemoryBytes:cases[provider][0]};const plan=resourcePlan(p),files=terraformSketch(p),unit=plan.composition.units.find(u=>u.id===node.id),key=unit.path+'/main.tf.json',name=plan.rows.find(r=>r.id===node.id).address;
 for(const mutation of ['memory','ingress','identity']){
  const changed={...files},tf=JSON.parse(files[key]);
  if(provider==='aws'){if(mutation==='memory')tf.resource.aws_ecs_task_definition[name].memory='10240';if(mutation==='ingress')tf.resource.aws_ecs_service[name].network_configuration.assign_public_ip=true;if(mutation==='identity')delete tf.resource.aws_ecs_task_definition[name].task_role_arn;}
  if(provider==='azure'){const b=tf.resource.azurerm_container_app[name];if(mutation==='memory')b.template.container.memory='4Gi';if(mutation==='ingress')b.ingress.external_enabled=true;if(mutation==='identity')delete b.identity;}
  if(provider==='gcp'){const b=tf.resource.google_cloud_run_v2_service[name];if(mutation==='memory')b.template.containers.resources.limits.memory='512Mi';if(mutation==='ingress')b.ingress='INGRESS_TRAFFIC_ALL';if(mutation==='identity')delete b.template.service_account;}
  if(provider==='ibm'){const b=tf.resource.ibm_code_engine_app[name];if(mutation==='memory')b.scale_memory_limit='1G';if(mutation==='ingress')b.managed_domain_mappings='public';if(mutation==='identity')delete b.run_service_account;}
  changed[key]=JSON.stringify(tf);assert(generationQuality(p,plan,changed).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),mutation);
  const forged=structuredClone(plan);forged.rows.find(r=>r.id===node.id).containerContract=null;assert(generationQuality(p,forged,changed).fatalFindings.some(f=>f.code==='container-constraint-mismatch'),'Metadata must not disable inspection');
 }
});

test('provider allocation boundaries retain exact sizes rather than an arbitrary cross-cloud cap',()=>{
 const cases=[['aws',30*GiB,'4096'],['aws',32*GiB,'8192'],['aws',120*GiB,'16384'],['aws',244*GiB,'32768'],['gcp',16*GiB,'4'],['gcp',24*GiB,'6'],['gcp',32*GiB,'8'],['ibm',12e9,'6'],['ibm',20e9,'10'],['ibm',48e9,'12']];
 for(const [provider,bytes,cpu]of cases){const node=compositionFixture(provider).nodes.at(-1);node.data.config={containerMemoryBytes:bytes};const result=containerRuntime(node);assert.equal(result.cpu,cpu);assert.equal(result.memoryBytes,bytes);assert.deepEqual(result.gaps,[]);}
 for(const [provider,bytes]of [['aws',31*GiB],['aws',121*GiB],['gcp',33*GiB],['ibm',49e9]]){const node=compositionFixture(provider).nodes.at(-1);node.data.config={containerMemoryBytes:bytes};assert(containerRuntime(node).gaps.length);}
});
