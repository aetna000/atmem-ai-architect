import {compileCapabilityComposition} from './delivery-capabilities.mjs';
import {applyStateCustody} from './state-custody.mjs';
import {ownershipInventory} from './ownership-inspection.mjs';
import {inspectTerraformModules} from './terraform-admission.mjs';
import{hasInvoice}from'./invoice-plan.mjs';
import{invoiceTerraform}from'./invoice-terraform.mjs';
import {awsPublicFaqTerraform,azurePublicFaqTerraform,gcpPublicFaqTerraform,ibmPublicFaqTerraform} from './public-faq-clouds.mjs';
import {ibmStructuredTerraform} from './ibm-structured.mjs';
import {CLOUD_PROVIDER_LOCKS} from './cloud-provider-locks.mjs';
import {azureStructuredTerraform} from './azure-structured.mjs';
import {gcpStructuredTerraform} from './gcp-structured.mjs';
import {generationProviders} from './generation-provider.mjs';
import {compileStructuredApi} from './structured-api.mjs';
import {generationQuality} from './generation-quality.mjs';
import {hasContainers} from './container-contracts.mjs';
import {containerTerraform} from './container-terraform.mjs';
import {isAwsGeneration} from './generation-provider.mjs';
import {incompleteTerraform} from './incomplete-terraform.mjs';
import {existingReferenceFiles} from './existing-references.mjs';
import {hasCrossCloud,crossCloudTerraform} from './cross-cloud-storage.mjs';
import {compileWeb} from './rag-web.mjs';
import {sourceContractFiles} from './source-contracts.mjs';
import {compileRag} from './bounded-rag.mjs';
import {awsPreflightFiles} from './aws-preflight.mjs';
import {compileSummaries} from './bedrock-summary.mjs';
import { compileAsyncDocuments } from './async-documents.mjs';
import { pythonRuntimeFiles } from "./python-runtime.mjs";
// Pure draft generator. The separate validation service can initialize providers and validate; no cloud execution.
import { productionStateFiles } from "./production-state.mjs";
import { compileTextStatistics } from "./text-statistics.mjs";
import { storageTestFiles } from "./storage-tests.mjs";
import { resourcePlan } from "./resources.mjs";
import { blockers, review } from "./review.mjs";

function compileTerraform(project, environment = "staging") {
  const composed=resourcePlan(project);
  if(composed.composition)return compileCapabilityComposition(project,composed,resourcePlan,environment);
  if(hasInvoice(project))return invoiceTerraform(project,resourcePlan(project),environment);
  if(hasContainers(project))return containerTerraform(project,resourcePlan(project),environment);
  if(hasCrossCloud(project))return crossCloudTerraform(project,environment);
  const plan = resourcePlan(project);
  if(plan.publicFaqPlan.entries.length){const provider=generationProviders(project).join(',');const adapter={aws:awsPublicFaqTerraform,azure:azurePublicFaqTerraform,gcp:gcpPublicFaqTerraform,ibm:ibmPublicFaqTerraform}[provider];if(adapter)return adapter(project,plan,environment);}
  if(generationProviders(project).join(',')==='azure'&&plan.azureStructuredPlan.entries.length)return azureStructuredTerraform(project,plan,environment);
  if(generationProviders(project).join(',')==='gcp'&&plan.gcpStructuredPlan.entries.length)return gcpStructuredTerraform(project,plan,environment);
  if(generationProviders(project).join(',')==='ibm'&&plan.ibmStructuredPlan.entries.length)return ibmStructuredTerraform(project,plan,environment);
  if(!isAwsGeneration(project))return incompleteTerraform(project,plan,environment);
  const env = ["production","qualification"].includes(environment) ? environment : "staging";
  const resources = { terraform_data: { review_gate: {
    input: { design_revision: project.revision, environment: env },
    lifecycle: { precondition: [{ condition: "${var.review_approved && length(local.unfinished_work) == 0}", error_message: "Review this sketch and finish the work listed in resource-schedule.json before a deployment plan can succeed." }] },
  } } };
  const bindingVariables={};
  for(const binding of plan.accessPlan.bindings){
    const variable=binding.variable;
    bindingVariables[variable]={type:'string',nullable:false,description:`Existing IAM role or user ARN for input ${variable}. The referenced identity is not modified; API access contracts create a separate scoped caller role.`,validation:{condition:`\${can(regex("^arn:aws:iam::[0-9]{12}:(role|user)/[A-Za-z0-9_+=,.@/-]+$", var.${variable}))}`,error_message:'Supply an IAM role/user ARN, not a root, session, wildcard or service principal.'}};
    resources.terraform_data.review_gate.lifecycle.precondition.push({condition:`\${can(regex(format("^arn:aws:iam::%s:(role|user)/", var.aws_account_id), var.${variable}))}`,error_message:'The bound IAM principal must belong to the selected AWS account.'});
  }
  const add = (type, name, body) => { (resources[type] ||= {})[name] = { ...body, depends_on: ["terraform_data.review_gate"] }; };
  for (const r of plan.rows.filter((r) => r.foundation)) {
    const name = r.address;
    const bucket = `\${aws_s3_bucket.${name}.id}`;
    add("aws_s3_bucket", name, { bucket_prefix: `atforma-${name.slice(0, 24).replaceAll("_", "-")}-`, force_destroy: false, lifecycle: { prevent_destroy: env !== "qualification" }, tags: { ManagedBy: "AtMem AI Architect", Environment: env } });
    add("aws_s3_bucket_public_access_block", name, { bucket, block_public_acls: true, block_public_policy: true, ignore_public_acls: true, restrict_public_buckets: true });
    add("aws_s3_bucket_server_side_encryption_configuration", name, { bucket, rule: { apply_server_side_encryption_by_default: { sse_algorithm: "AES256" } } });
    add("aws_s3_bucket_versioning", name, { bucket, versioning_configuration: { status: "Enabled" } });
    add("aws_s3_bucket_ownership_controls", name, { bucket, rule: { object_ownership: "BucketOwnerEnforced" } });
    const grants=plan.accessPlan.connections.filter(edge=>edge.target===r.id).flatMap((edge,index)=>{
      const Principal={AWS:`\${var.${edge.principalVariable}}`};
      return [
        {Sid:`OperatorBucket${index}`,Effect:'Allow',Principal,Action:['s3:ListBucket','s3:GetBucketLocation'],Resource:`\${aws_s3_bucket.${name}.arn}`},
        {Sid:`OperatorObjects${index}`,Effect:'Allow',Principal,Action:['s3:GetObject','s3:GetObjectVersion',...(edge.access==='s3-read-write'?['s3:PutObject']:[])],Resource:`\${aws_s3_bucket.${name}.arn}/*`},
      ];
    });
    add("aws_s3_bucket_policy", name, { bucket, policy: JSON.stringify({ Version: "2012-10-17", Statement: [{ Sid: "DenyInsecureTransport", Effect: "Deny", Principal: "*", Action: "s3:*", Resource: [`\${aws_s3_bucket.${name}.arn}`, `\${aws_s3_bucket.${name}.arn}/*`], Condition: { Bool: { "aws:SecureTransport": "false", "aws:PrincipalIsAWSService": "false" } } },...grants] }) });
  }
  const compute=compileTextStatistics(plan,env);
  const async=compileAsyncDocuments(plan,env);
  const summaries=compileSummaries(plan,env);
  const rag=compileRag(plan,env);
  const structuredApi=compileStructuredApi(plan,env);
  for(const [type,items]of Object.entries(rag.resources))resources[type]={...(resources[type]||{}),...items};
  for(const [type,items]of Object.entries(summaries.resources))resources[type]={...(resources[type]||{}),...items};
  for(const [type,items]of Object.entries(async.resources))resources[type]={...(resources[type]||{}),...items};
  resources.terraform_data.review_gate.lifecycle.precondition.push(...async.preconditions);
  for(const [type,items]of Object.entries(compute.resources))resources[type]={...(resources[type]||{}),...items};
  for(const [type,items]of Object.entries(structuredApi.resources))resources[type]={...(resources[type]||{}),...items};
  const web=compileWeb(plan,env,resources);
  // Untrusted diagram text is never interpolated into Terraform expressions or resource names.
  const unfinished = [...(env==='production'?plan.sourceContractPlan.sources.map(s=>`native-vendor-integration-unverified-${s.address}`):[]),...plan.gapDetails.map(g => g.id), ...blockers(review(project)).map((_, i) => `architecture review blocker ${i + 1}`)];
  const config = {
    terraform: { required_version: env === "production" ? ">= 1.10.0, < 2.0.0" : ">= 1.5.0, < 2.0.0", ...(env === "production" ? {backend:{s3:{encrypt:true,use_lockfile:true}}}:{}), required_providers: { aws: { source: "hashicorp/aws", version: "~> 6.0" } } },
    variable: {
      ...bindingVariables,
      ...compute.variables, ...async.variables, ...summaries.variables, ...rag.variables,
      aws_region: { type: "string", description: "Explicitly choose the reviewed deployment region; no region is assumed." },
      aws_account_id: { type: "string", description: "Expected AWS account ID; provider refuses a different account.", validation: { condition: '${can(regex("^[0-9]{12}$", var.aws_account_id))}', error_message: "Use a twelve digit AWS account ID." } },
      review_approved: { type: "bool", default: false, description: "Set only after reviewing the design, cost, security and generated Terraform." },
    },
    provider: { aws: { region: "${var.aws_region}", allowed_account_ids: ["${var.aws_account_id}"] } },
    locals: { unfinished_work: unfinished }, resource: resources,
    ...((Object.keys(compute.data).length||Object.keys(web.data).length)?{data:{...compute.data,...web.data}}:{}),
    output: { ...compute.outputs, ...async.outputs, ...summaries.outputs, ...rag.outputs, ...web.outputs, design_revision: { value: project.revision }, environment: { value: env }, implemented_foundations: { value: plan.rows.filter((r) => r.foundation).length }, buckets: { value: Object.fromEntries(plan.rows.filter(r=>r.foundation).map(r=>[r.address,{name:`${"${"}aws_s3_bucket.${r.address}.id}`,arn:`${"${"}aws_s3_bucket.${r.address}.arn}`}])) } },
  };
  return {
    ...awsPreflightFiles(),
    '.terraform.lock.hcl':CLOUD_PROVIDER_LOCKS.aws,
    ...existingReferenceFiles(project),
    '.gitignore':'.terraform/\nbuild/\n*.tfstate\n*.tfstate.*\n*.tfplan\nreviewed-plan.json\n.preflight/\n*.tfvars\n*.tfvars.json\n*.zip\n__pycache__/\n',
    ...(env === "production" ? productionStateFiles():{}),
    ...storageTestFiles(plan),
    ...sourceContractFiles(plan),
    ...compute.files, ...async.files, ...summaries.files, ...rag.files, ...structuredApi.files, ...web.files,
    ...pythonRuntimeFiles([...plan.rows.filter(r=>r.compute).map(r=>({address:r.address,sdk:false})),...async.builds,...summaries.builds,...rag.builds]),
    "main.tf.json": JSON.stringify(config, null, 2),
    "resource-schedule.json": JSON.stringify(plan, null, 2),
    "README.md": `# AtMem AI Architect Terraform sketch\n\nRevision r${project.revision}; ${env}.\n\nExplicit proposed S3 blocks get native resources: a bucket, public-access block, encryption, versioning, bucket-owner-enforced ownership and a deny-insecure-transport policy. Buckets prevent destruction. Typed existing IAM-principal bindings and direct s3-read/s3-read-write edges generate required same-account role/user ARN inputs and bucket-scoped access policies. Labels alone never grant permissions. Read includes versioned reads; write adds PutObject, not deletion. Existing identities are not created or changed. Other IAM, model access, application code, network policy, services and integrations still require engineering work. Typed text-statistics Lambda components additionally generate a tested handler, execution role, scoped logging, published version, live alias and caller permission. Other workloads remain incomplete; this is not a complete deployable application unless all required implementations and integrations are covered and verified.\n\nDefault review gate prevents a successful plan; unresolved work also blocks it. Review resource-schedule.json and the architecture document, implement missing generator capabilities and regenerate from the project; do not hand-clear unfinished_work to make a plan pass.\n\nFor production, read STATE.md and supply the reviewed S3 backend configuration; local state is for staging validation only. Build packaged runtimes first using python3 build-runtime.py when present (see BUILD.md). Run the shipped Python application tests where present: python3 -m unittest discover -s app-tests -p '*_test.py'. Run terraform test for generated mock-provider checks.\n\nOn your own machine: install Terraform, review provider version constraints, then run terraform init -backend=false and terraform validate. Retain the generated provider lock file. Configure the standard AWS credential chain separately; never put credentials in project files. Supply aws_region, aws_account_id and every generated principal_*_arn input to terraform plan. Principal ARNs must identify existing roles/users in that account; root/session/wildcard and cross-account bindings are rejected. Review inherited IAM permissions, permission boundaries and organization policies separately: a scoped bucket grant does not revoke permissions granted elsewhere. Run the read-only account prerequisites in PREFLIGHT.md. Review the actual account, region, changes, costs and permissions before approving any apply. This export carries no validation evidence. Use AtMem AI Architect’s Terraform → Test Terraform view to run local schema checks. No cloud plan or deployment has been validated.\n\nReview AES256 versus customer-managed keys, retention, version-storage cost, access policies and state storage against your requirements. The diagram's region is documented but not silently used; aws_region must be deliberately supplied.\n\nReferences:\n- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket\n- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block\n- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration\n- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning\n- https://developer.hashicorp.com/terraform/language/resources/terraform-data\n`,
  };
}

export function terraformSketch(project,environment="staging"){
 const files=applyStateCustody(project,environment,{...compileTerraform(project,environment),...existingReferenceFiles(project)});
 const root=JSON.parse(files['main.tf.json']);
 files['deployment-ownership.json']=JSON.stringify(ownershipInventory(project,inspectTerraformModules(project,resourcePlan(project),files,root,()=>{}).configs),null,2)+'\n';
 files['generation-quality.json']=JSON.stringify(generationQuality(project,resourcePlan(project),files,{environment}),null,2);
 return files;
}
