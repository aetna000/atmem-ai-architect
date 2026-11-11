export function applyStateCustodyTasks(emitted,tasks){
 if(!emitted['state-custody.json'])return;
 const record=JSON.parse(emitted['state-custody.json']);
 tasks.push({id:'TASK-STATE-CUSTODY',phase:'State and operations',title:'Verify the explicitly selected root state custody',status:'todo',dependsOn:['TASK-SETUP','TASK-SECURITY-DESIGN','TASK-INFRA-STATIC'],files:['terraform/STATE.md','terraform/state-custody.json','terraform/backend.hcl.example','terraform/main.tf.json'],steps:[
  'Read terraform/state-custody.json and STATE.md. Preserve the '+record.environment+' backend '+record.selection.backend+', owner/residency intent and linked decision '+record.selection.decisionId+'. Selection or an Accepted design decision is not observed custody evidence.',
  'Run terraform init -backend=false and terraform validate locally. Do not initialize a remote backend, clear the acceptance blocker or put credentials in backend.hcl/source to obtain a pass.',
  'Prepare an environment-specific private backend.hcl using the example and approved credential chain. Before separately authorized state access, agree platform owner, namespace, residency, least privilege, encryption, retention and recovery responsibilities.',
  'With explicit authorization on isolated test state, verify competing-writer lock exclusion, owner-safe unlock, denied access and version recovery. Record native backend/service versions and exact configuration/evidence digests; mocks do not prove the destination.',
  'Existing-state migration needs a separate approved plan, private verified backup, lineage/serial/resource inventory and writer freeze. Verify lineage after migration and retain rollback evidence; this task does not authorize migration.'
 ],outputs:['Accepted custody/operating decision and private input location','Access/lock/recovery evidence bound to the exact destination','Separately approved migration plan when applicable'],acceptance:['Owner, environment, residency and exact backend namespace are independently verified.','Missing, denied, failed and mock-only checks remain visible.','Backend selection has not silently migrated state or accepted operations.']});
 const planning=tasks.find(t=>t.id==='TASK-CLOUD-PLAN');if(planning)planning.dependsOn.push('TASK-STATE-CUSTODY');
}
