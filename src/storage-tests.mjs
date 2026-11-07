// Generated tests are local mock-provider checks, never AWS deployment evidence.
export function storageTestFiles(plan) {
 if(!plan.rows.some(r=>r.implemented))return {};
 const values=new Map(),examples={aws_region:'REPLACE_WITH_REVIEWED_REGION',aws_account_id:'REPLACE_WITH_ACCOUNT_ID',review_approved:false};
 for(const b of plan.accessPlan.bindings){values.set(b.variable,'arn:aws:iam::123456789012:role/qualification/operator');examples[b.variable]='REPLACE_WITH_EXISTING_ROLE_OR_USER_ARN';}
 for(const p of plan.asyncPlan?.pipelines||[]){values.set(`${p.worker.address}_alert_topic_arns`,['arn:aws:sns:ap-southeast-2:123456789012:qualification-alerts']);examples[`${p.worker.address}_alert_topic_arns`]=[];}
 const models=[...(plan.summaryPlan?.entries||[]).map(e=>e.model),...(plan.ragPlan?.entries||[]).map(e=>e.model)];
 for(const model of models){values.set(`${model.address}_model_id`,model.settings?.modelId||'amazon.nova-micro-v1:0');examples[`${model.address}_model_id`]=model.settings?.modelId||'REPLACE_WITH_REVIEWED_DIRECT_MODEL_ID';}
 let index=0;
 for(const {worker,api}of plan.ragPlan?.entries||[]){
  for(const edge of plan.accessPlan.connections.filter(e=>e.target===api.id&&e.access==='api-invoke')){
   const id=`caller_${worker.address}_${Array.from(new TextEncoder().encode(edge.id),b=>b.toString(16).padStart(2,'0')).join('')}`;
   values.set(`${id}_subject`,`qualification_user_${++index}`);values.set(`${id}_employee_region`,'AU');
   examples[`${id}_subject`]='REPLACE_WITH_AUTHORITATIVE_SUBJECT';examples[`${id}_employee_region`]='REPLACE_WITH_REVIEWED_REGION_CODE';
  }
 }
 const variables=[...values].map(([key,value])=>`  ${key} = ${JSON.stringify(value)}`).join('\n');
 const first=plan.accessPlan.bindings[0]?.variable;
 const negative=first?`run "cross_account_binding_rejected" {\n  command = plan\n  variables { ${first} = "arn:aws:iam::999999999999:role/other" }\n  expect_failures = [terraform_data.review_gate]\n}\nrun "wildcard_binding_rejected" {\n  command = plan\n  variables { ${first} = "*" }\n  expect_failures = [var.${first}]\n}\n`:'';
 return {
  'tests/storage-access.tftest.hcl':`# Terraform 1.7+; mock AWS only. No real credentials or resources.\nmock_provider "aws" {}\nvariables {\n  aws_region = "ap-southeast-2"\n  aws_account_id = "123456789012"\n  review_approved = true\n${variables}\n}\nrun "generated_storage_plan" {\n  command = plan\n}\nrun "unapproved_plan_rejected" {\n  command = plan\n  variables { review_approved = false }\n  expect_failures = [terraform_data.review_gate]\n}\n${negative}`,
  'deployment.tfvars.json.example':JSON.stringify(examples,null,2),
  'VALIDATION.md':`# Validate the generated implementation\n\n1. Build runtimes with python3 build-runtime.py when present, then run the shipped app-tests. See BUILD.md for pinned dependencies.\n2. Install Terraform 1.7+ (1.10+ for production state), run terraform init -backend=false, terraform validate and terraform test. Retain the provider lock file. Mock plans do not call AWS and intentionally fail for unresolved implementations.\n3. Copy deployment.tfvars.json.example and replace every required placeholder with reviewed values. Leave review_approved false until requirements, costs, state, identities and permissions are reviewed. Credentials remain in the standard AWS credential chain.\n4. Review effective IAM boundaries and organization policies. Scoped grants do not revoke broader existing permissions. API caller roles have only the generated route permission; end users must not have direct Lambda invocation or catalog write access.\n5. Plan with terraform plan -var-file=deployment.tfvars.json -out=reviewed.tfplan. Run PREFLIGHT.md account checks. Apply only the exact reviewed plan after authorization.\n6. Verify real application outputs, authenticated denials, recovery, updates/deletes, revocation and cleanup. For S3, verify byte-preserving and exact-version reads, encryption/versioning and anonymous denial. Use controlled identities without broader grants for negative tests.\n7. Production storage prevents destruction. Deletion, retention and decommissioning need a reviewed lifecycle procedure; do not bypass protections merely to finish testing.\n\nNo execution evidence is embedded in a fresh export. Mock tests, control-plane access and an account plan do not prove deployed behavior or production readiness.\n`,
 };
}
