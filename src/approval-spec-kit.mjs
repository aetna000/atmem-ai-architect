import {approvalProfiles,approvalReferences} from './approval-applications.mjs';
import {resourceAddress} from './identifiers.mjs';
export function applyApprovalTasks(project,files,tasks){
 for(const {node,profile}of approvalProfiles(project)){
  const root='terraform/applications/'+resourceAddress(node.id)+'/',deferred=profile.format==='approval-application-template-v1',metadata=deferred?'application-template.json':'application-profile.json';
  const parent=tasks.find(t=>t.id.startsWith('TASK-RESOURCE-')&&t.componentIds?.includes(node.id));
  if(!parent)throw Error('Selected application lost its component implementation task.');
  const paths=Object.keys(files).filter(p=>p.startsWith(root));parent.files=[...new Set([...(parent.files||[]),...paths])];
  parent.steps.push('Read '+root+metadata+', api.py and assembly-status.json. This is shared API source only; implement provider resources and the complete domain/worker behavior without deleting requirements or clearing work gates.');
  const id='TASK-APP-ASSEMBLY-'+resourceAddress(node.id);
  parent.dependsOn=[...new Set([...(parent.dependsOn||[]),id])];
  tasks.push({id,phase:'Implementation',title:'Implement the selected approval application source: '+node.data.label,dependsOn:['TASK-SETUP','TASK-SECURITY-DESIGN'],componentIds:[node.id],requirementIds:parent.requirementIds||[],files:paths,steps:[
   'Retain exact component/provider/environment/account and complete requirements; reconcile '+profile.environment+' against the intended deployment environment.',
   'Build the emitted API image using the exact lock and native profile. Review native identity/database/API-role and worker-role environment bindings; keep credentials outside source.',
   'Implement a real domain processor and concrete worker entrypoint using create_native_worker; use the profile-bound destination and membership_key for explicitly admitted native users. Do not substitute fixture behavior or metadata-selected imports.',
   'Run clean local HTTP/queue/SQL/TLS positive and negative source checks including changed policy, authorization, idempotency and unknown effects. Record fixture boundaries; the dependent component/integration tasks still own provider resources and real destination compatibility.'
  ],outputs:['Explicit runtime/profile input contract','Concrete domain source and worker entrypoint','Artifact-bound local source/integration evidence'],acceptance:['All linked requirements retain their original text/ownership.','API/worker/domain source has independent executable checks.','Provider linkage, schema/mocks and whole-system acceptance remain separate dependent work.']});
  if(deferred){
   const refs=approvalReferences(profile),bindingId='TASK-APP-BINDING-'+resourceAddress(node.id);
   const sourceTasks=[...new Set(refs.map(ref=>tasks.find(t=>t.id.startsWith('TASK-RESOURCE-')&&t.componentIds?.includes(ref.componentId))?.id))];
   if(sourceTasks.includes(undefined))throw Error('Application output source lost its component task.');
   tasks.push({id:bindingId,phase:'Implementation',title:'Resolve public runtime inputs: '+node.data.label,dependsOn:[...new Set([id,parent.id,...sourceTasks])],componentIds:[...new Set([node.id,...refs.map(r=>r.componentId)])],requirementIds:parent.requirementIds||[],files:[root+metadata,root+'resolve-profile.py',root+'workflow_bindings.py'],steps:[
    'Build source independently of unresolved outputs. When the owned resources or explicit local fixtures supply their outputs, review exact component/provider/environment and source digests; do not invent native IDs or put credentials in the public ledger.',
    'Run python -I '+root+'resolve-profile.py --outputs /ABSOLUTE/PUBLIC-OUTPUT-LEDGER.json --out /ABSOLUTE/FRESH-BINDING-DIRECTORY. Mount that bundle read-only as runtime-binding before starting the API; reject missing, stale or mismatched receipts.',
    'Record structural resolution separately from real source/cloud identity, authorization and operating acceptance. Local fixtures must remain labelled; no cloud operation is authorized by this task.'
   ],outputs:['Fresh application-profile.json and matching binding-receipt.json outside source control','Exact input/artifact digests and disclosed fixture boundaries'],acceptance:['No fallback or fixed ownership/policy change.','Unresolved and mismatched bundles fail before native runtime setup.','Connected acceptance uses the exact resolved application declaration.']});
   for(const task of tasks)if(task.id==='TASK-E2E'||task.id.startsWith('TASK-ACCEPTANCE-')&&task.componentIds?.includes(node.id))task.dependsOn=[...new Set([...task.dependsOn,bindingId])];
  }
 }
}
