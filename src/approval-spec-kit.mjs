import {approvalProfiles} from './approval-applications.mjs';
import {resourceAddress} from './identifiers.mjs';
export function applyApprovalTasks(project,files,tasks){
 for(const {node,profile}of approvalProfiles(project)){
  const root='terraform/applications/'+resourceAddress(node.id)+'/';
  const parent=tasks.find(t=>t.id.startsWith('TASK-RESOURCE-')&&t.componentIds?.includes(node.id));
  if(!parent)throw Error('Selected application lost its component implementation task.');
  const paths=Object.keys(files).filter(p=>p.startsWith(root));parent.files=[...new Set([...(parent.files||[]),...paths])];
  parent.steps.push('Read '+root+'application-profile.json, api.py and assembly-status.json. This is shared API source only; implement provider resources and the complete domain/worker behavior without deleting requirements or clearing work gates.');
  const id='TASK-APP-ASSEMBLY-'+resourceAddress(node.id);
  parent.dependsOn=[...new Set([...(parent.dependsOn||[]),id])];
  tasks.push({id,phase:'Implementation',title:'Implement the selected approval application source: '+node.data.label,dependsOn:['TASK-SETUP','TASK-SECURITY-DESIGN'],componentIds:[node.id],requirementIds:parent.requirementIds||[],files:paths,steps:[
   'Retain exact component/provider/environment/account and complete requirements; reconcile '+profile.environment+' against the intended deployment environment.',
   'Build the emitted API image using the exact lock and native profile. Review native identity/database/API-role and worker-role environment bindings; keep credentials outside source.',
   'Implement a real domain processor and concrete worker entrypoint using create_native_worker; use the profile-bound destination and membership_key for explicitly admitted native users. Do not substitute fixture behavior or metadata-selected imports.',
   'Run clean local HTTP/queue/SQL/TLS positive and negative source checks including changed policy, authorization, idempotency and unknown effects. Record fixture boundaries; the dependent component/integration tasks still own provider resources and real destination compatibility.'
  ],outputs:['Explicit runtime/profile input contract','Concrete domain source and worker entrypoint','Artifact-bound local source/integration evidence'],acceptance:['All linked requirements retain their original text/ownership.','API/worker/domain source has independent executable checks.','Provider linkage, schema/mocks and whole-system acceptance remain separate dependent work.']});
 }
}
