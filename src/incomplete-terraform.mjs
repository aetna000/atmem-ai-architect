import {existingReferenceFiles} from './existing-references.mjs';
import {generationProviders} from './generation-provider.mjs';
// Preserve intent for unsupported workloads without fabricating a different cloud.
export function incompleteTerraform(project,plan,environment){
 const providers=generationProviders(project);
 const gaps=[...plan.gapDetails.map(g=>g.id),'provider-workload-implementation-required'];
 const config={terraform:{required_version:'>= 1.7.0, < 2.0.0'},variable:{review_approved:{type:'bool',default:false}},locals:{unfinished_work:gaps},resource:{terraform_data:{review_gate:{input:{design_revision:project.revision,environment,requested_providers:providers},lifecycle:{precondition:[{condition:'${var.review_approved && length(local.unfinished_work) == 0}',error_message:'This workload has no complete compiler for the requested providers. Implement its required resources and connections before deployment.'}]}}}},output:{design_revision:{value:project.revision}}};
 return {...existingReferenceFiles(project),'main.tf.json':JSON.stringify(config,null,2),'resource-schedule.json':JSON.stringify(plan,null,2),'generation-status.json':JSON.stringify({version:1,status:'implementation_required',providers,deployable:false,runtimeValidated:false,gaps},null,2),'README.md':`# Infrastructure implementation required\n\nRequested providers: ${providers.join(', ')||'not selected'}. No substitute provider or application resources have been generated. This file contains a blocking review gate only. It is not deployment infrastructure.\n\n${plan.gapDetails.map(g=>'- '+g.message).join('\n')}\n\nPreserve the design and implement the missing compiler capabilities; do not clear the gate to obtain a pass.\n`};
}
