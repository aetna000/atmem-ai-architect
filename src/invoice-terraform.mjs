import{awsInvoiceTerraform}from'./invoice-aws.mjs';
import{azureInvoiceTerraform}from'./invoice-azure.mjs';
import{gcpInvoiceTerraform}from'./invoice-gcp.mjs';
import{ibmInvoiceTerraform}from'./invoice-ibm.mjs';
import{invoiceState}from'./invoice-state.mjs';
import{validInvoiceRegion}from'./invoice-region.mjs';
import{incompleteTerraform}from'./incomplete-terraform.mjs';

// Public dispatch is deliberately separate from isolated native-adapter fixtures.
// It retains all graph gaps and blocks a partial module from passing as the whole.
export function invoiceTerraform(project,plan,environment='staging'){
 const entries=plan.invoicePlan?.entries||[];
 if(entries.length!==1)return incompleteTerraform(project,plan,environment);
 const{row}=entries[0],adapter={aws:awsInvoiceTerraform,azure:azureInvoiceTerraform,gcp:gcpInvoiceTerraform,ibm:ibmInvoiceTerraform}[row.provider];
 if(!adapter)return incompleteTerraform(project,plan,environment);
 const files=adapter(project,{...row,region:validInvoiceRegion(row.provider,row.region)?row.region:''},environment),config=JSON.parse(files['main.tf.json']);
 config.locals.unfinished_work=plan.gapDetails.map(gap=>gap.id);
 config.resource.terraform_data.review_gate.lifecycle.precondition.push({condition:'${length(local.unfinished_work) == 0}',error_message:'Preserved requirements/components/connections are not all implemented. Inspect resource-schedule.json and repair the generator composition; do not clear unfinished_work.'});
 const state=invoiceState(row.provider);
 if(environment==='production')config.terraform.backend=state.backend;
 files['main.tf.json']=JSON.stringify(config,null,2)+'\n';
 files['resource-schedule.json']=JSON.stringify(plan,null,2)+'\n';
 files['invoice-contract.json']=JSON.stringify({format:'invoice-workflow-v1',provider:row.provider,componentId:row.id,accountingComponentId:entries[0].accountingId,limits:{maxPdfBytes:10000000,maxPdfPages:100,retentionDays:90},review:'Separate live SQL user/reviewer roles; only approved payload hashes admit accounting delivery.',accounting:'Existing normalized-action-v1 adapter, destination contract digest and stable operation identity. Actual accounting compatibility/idempotency is independently accepted; uncertain outcomes are fenced and reconciled, not blindly retried.',evidence:'Generated source and contracts; not account-plan, cloud runtime or production evidence.'},null,2)+'\n';
 Object.assign(files,state.files);
 files['.gitignore']+='backend.hcl\n*.tfbackend\nreviewed-plan.json\n';
 files['README.md']+='\n## Whole-project scope and state\n\nRead invoice-contract.json, resource-schedule.json, OPERATING_JOBS.md and STATE.md.\nAdditional requested components/flows/configuration remain visible and block the\nreview gate until implemented. No diagram requirement is removed by this module.\nProduction uses its reviewed provider-specific protected state/locking backend; no\nstate store is deployed or silently borrowed from another cloud. Destination\nstate residency, access, locking and recovery acceptance precede account planning.\n';
 return files;
}
