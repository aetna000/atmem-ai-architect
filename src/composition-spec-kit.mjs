const key=value=>Array.from(new TextEncoder().encode(value),v=>v.toString(16).padStart(2,'0')).join('');
export function applyCompositionTasks(project,plan,emitted,tasks,implementation){
 if(!plan.composition)return;
 const checks=[];
 for(const unit of plan.composition.units){
  const component=implementation.components.find(c=>c.id===unit.id),path='terraform/'+unit.path,id='TASK-UNIT-TEST-'+key(unit.id),resource=tasks.find(t=>t.id==='TASK-RESOURCE-'+key(unit.id));
  checks.push(id);
  const steps=[`Read ${path}/README.md, ${path}/main.tf.json and terraform/composition.json. Preserve this unit's provider, ownership, source, images and protected resources.`,
   `From ${path}/, run terraform init -backend=false, terraform validate and terraform test. Retain test counts and failed/skipped checks; provider mocks do not establish application runtime or account behavior.`,
   `Root inputs for this unit: ${component.requiredInputs.join(', ')}. Read terraform/deployment.tfvars.json.example; keep real values and credentials outside source. Root approval stays false until complete-composition review.`,
   'Run the actual application or supplied-image acceptance checks for linked requirements and interfaces. Record absent or unsupported scope; do not treat module structure or a mock plan as complete-system evidence.'];
  tasks.push({id,phase:'Local unit qualification',title:'Qualify delivery unit '+unit.id,status:'todo',dependsOn:['TASK-SETUP','TASK-SECURITY-DESIGN',resource.id],steps,outputs:['Exact unit source/input/provider identities','Native schema/mock and application acceptance receipts'],acceptance:['Actual file paths and selected providers match this unit.','All required local checks execute; missing, failed, skipped or mock-only behavior remains explicit.'],componentIds:[unit.id],requirementIds:component.requirements});
  if(unit.implementation==='container-service'){
   resource.steps=[`Preserve the supplied application responsibility: ${project.nodes.find(n=>n.id===unit.id).data.description||resource.title}.`,
    `Inspect ${path}/README.md and ${path}/main.tf.json. This unit generates a private native runtime footprint; the actual application source and immutable Linux image must be supplied and qualified.`,
    `Build and test the owner-supplied image using its documented repository/runtime instructions. Supply its exact image digest and reviewed destination/network inputs using ${component.requiredInputs.join(', ')}.`,
    'Verify startup, health, authorization, bounded resource use and each linked application/data contract independently. Runtime identity has no implied application-data access; missing integrations stay blocking generator work.',
    'Preserve existing environment/network/project ownership. Publication, cloud access, apply, migration and deployment require explicit authorization; generated source does not grant it.'];
   resource.outputs=[path+'/main.tf.json',path+'/tests/container.tftest.hcl','Supplied-image build/runtime/behavior evidence'];
  }
 }
 tasks.push({id:'TASK-COMPOSITION-VALIDATION',phase:'Local composition qualification',title:'Validate all delivery units and their complete interfaces',status:'todo',dependsOn:['TASK-INFRA-STATIC',...checks],steps:[
  'From terraform/, run terraform init -backend=false and terraform validate. Confirm the full module closure, explicit provider aliases, exact versions/inputs, stable addresses and retained whole-project unfinished scope.',
  'Run every unit-local test command in spec-kit/implementation-map.json and retain nonzero test counts. Combine the actual unit runtimes and verify the declared interfaces with independent positive/negative journeys; isolated unit tests do not establish new composition behavior.',
  'Keep unsupported components, constraints and interfaces visible. Root and unit review gates must block incomplete scope even when review is approved.',
  'Review whole-composition state custody, access, residency, locking/recovery and operating responsibilities. Production remains blocked until the root state/operations capability is implemented and independently accepted.'
 ],outputs:['Whole-composition schema and module/provider/input inventory','Connected-runtime/interface acceptance and unresolved-scope report'],acceptance:['Every declared unit and interface has exact implementation/test links.','Configuration/mock/runtime/account/deployment evidence levels remain separate.'],componentIds:plan.composition.units.map(u=>u.id)});
 tasks.find(t=>t.id==='TASK-CLOUD-PLAN').dependsOn.push('TASK-COMPOSITION-VALIDATION');
 const staticTask=tasks.find(t=>t.id==='TASK-INFRA-STATIC');staticTask.steps.push('Validate the root and each units/* directory separately; each child has retained native mock tests. Execute the explicit commands in spec-kit/implementation-map.json and never count an empty root test directory as a pass.');
}
