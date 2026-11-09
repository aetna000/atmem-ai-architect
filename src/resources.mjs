import {existingReference} from './existing-references.mjs';
import {hasCrossCloud,crossCloudPlan} from './cross-cloud-storage.mjs';
import {webPlan} from './rag-web.mjs';
import {sourceContractPlan} from './source-contracts.mjs';
import {ragPlan} from './bounded-rag.mjs';
import {summaryPlan} from './bedrock-summary.mjs';
import { asyncPipelinePlan } from './async-documents.mjs';
import { runtimeSettings } from "./runtime-settings.mjs";
// A schedule of the diagram's intent, not discovered cloud inventory.
import { storageAccessPlan } from "./s3-access.mjs";
import { roleOf } from "./review.mjs";

const SERVICES = [
  [/\bcloudfront\b/i, "Amazon CloudFront", ["aws_cloudfront_distribution"], "Requests, transfer and private static assets"],
  [/\bcognito\b/i, "Amazon Cognito", ["aws_cognito_user_pool"], "Active users and authentication features"],
  [/\bapi\s*gateway\b/i, "Amazon API Gateway", ["aws_apigatewayv2_api"], "API requests, transfer and access logs"],
  [/\bs3\b/i, "Amazon S3", ["aws_s3_bucket", "aws_s3_bucket_public_access_block", "aws_s3_bucket_server_side_encryption_configuration", "aws_s3_bucket_versioning", "aws_s3_bucket_ownership_controls", "aws_s3_bucket_policy"], "Storage, requests, retrieval and transfer"],
  [/bedrock.*guard|guard.*bedrock/i, "Amazon Bedrock Guardrails", ["aws_bedrock_guardrail"], "Enabled policy checks and text units; confirm each policy's charge"],
  [/bedrock.*knowledge|knowledge.*bedrock/i, "Amazon Bedrock Knowledge Bases", ["aws_bedrockagent_knowledge_base", "aws_iam_role"], "Embeddings, ingestion, vector store and retrieval; select the backing store"],
  [/\bbedrock\b/i, "Amazon Bedrock", [], "Model-specific input/output tokens; guardrails, embeddings and knowledge bases separately"],
  [/\blambda\b/i, "AWS Lambda", ["aws_lambda_function", "aws_iam_role"], "Requests, duration, memory and logs"],
  [/\bopensearch\b/i, "Amazon OpenSearch", [], "Deployment mode, indexing/search capacity and storage"],
  [/\bapp\s*runner\b/i, "AWS App Runner", ["aws_apprunner_service"], "Provisioned and active compute, builds, logs and transfer"],
  [/\b(ecs|fargate)\b/i, "Amazon ECS", ["aws_ecs_service", "aws_ecs_task_definition"], "Compute, load balancing, networking, images and logs"],
  [/\bdynamodb\b/i, "Amazon DynamoDB", ["aws_dynamodb_table"], "Read/write requests, storage and backup"],
  [/\bsqs\b/i, "Amazon SQS", ["aws_sqs_queue"], "Requests, payload size and transfer"],
  [/\bsagemaker\b/i, "Amazon SageMaker AI", [], "Training, serving instances, processing and storage"],
  [/\b(iot|kinesis)\b/i, "AWS ingestion service", [], "Messages, connections, processing and retention"],
  [/\bcloudtrail\b/i, "AWS CloudTrail", ["aws_cloudtrail"], "Management/data events, delivery, retention and query costs"],
  [/\bcloudwatch\b/i, "Amazon CloudWatch", ["aws_cloudwatch_log_group"], "Logs, metrics, alarms and retention"],
  [/\biam\b/i, "AWS IAM", ["aws_iam_policy"], "Review associated services; IAM policy alone is not an application guardrail"],
];
const CANDIDATES = { data: "Storage or existing data connector", ingest: "Ingestion / processing service", index: "Search / vector index", llm: "Model API and model selection", guard: "Guardrails and access policies", human: "Approval workflow", app: "Application runtime and API", output: "User interface / delivery integration", model: "Model training or serving", monitor: "Monitoring and alerting" };

// Explicit selections are authoritative; labels are only candidates, never a way to
// override an unsupported or conflicting selection. Generic names retain open modes.
export function resolveService(data) {
  if (data.provider !== "aws") return null;
  const value = String(data.service || data.label || "");
  if (/bedrock/i.test(value) && /\b(model|inference|invoke)\b/i.test(value) && /(guardrail|knowledge)/i.test(value) && /\bwith\b|[+&]/i.test(value)) return { ambiguous: true, selected: !!data.service };
  let matches = SERVICES.filter(([re]) => re.test(value));
  if (/bedrock.*(guard|knowledge)|(guard|knowledge).*bedrock/i.test(value)) matches = matches.filter(([,name]) => name !== "Amazon Bedrock");
  if (matches.length !== 1) return { ambiguous: matches.length > 1, selected: !!data.service };
  let [, name, resources, costs] = matches[0];
  if (name === "Amazon OpenSearch") {
    if (/serverless/i.test(value)) { name = "Amazon OpenSearch Serverless"; resources = ["aws_opensearchserverless_collection"]; }
    else if (/\b(domain|provisioned|managed cluster)\b/i.test(value)) { name = "Amazon OpenSearch domain"; resources = ["aws_opensearch_domain"]; }
  }
  return { name, resources, costs, selected: !!data.service };
}

export function resourcePlan(project) {
  if(hasCrossCloud(project))return crossCloudPlan(project);
  const nodes = project.nodes.filter((n) => n.data.kind !== "note");
  const ids = new Set(nodes.map((n) => n.id));
  const rows = nodes.map((n) => {
    const match = resolveService(n.data);
    const existing = n.data.origin === "existing";
    const foundation = !existing && n.data.provider === "aws" && match?.name === "Amazon S3";
    const compute=!existing && n.data.provider==="aws" && match?.name==="AWS Lambda" && n.data.implementation==="text-statistics";
    // Encode the complete ID: stable on reorder/rename, valid Terraform identifier, no collisions.
    const address = `block_${Array.from(new TextEncoder().encode(n.id), (b) => b.toString(16).padStart(2, "0")).join("")}`;
    return { id: n.id, address, label: n.data.label, provider: n.data.provider,
      service: match?.name || n.data.service || CANDIDATES[roleOf(n)] || "Service to be selected",
      selection: match?.ambiguous ? "Ambiguous service names" : match?.name ? (match.selected ? "Explicit service field; deployment review required" : "Named in diagram") : "Needs service confirmation", existing,
      region: n.data.config?.region || "To be selected", resources: match?.resources || [],
      costDrivers: match?.costs || "Confirm service, capacity and billable dimensions",
      dependencies: project.edges.filter((e) => e.target === n.id && ids.has(e.source)).map((e) => e.source),
      terraform: existing ? "Existing — reference/import plan needed" : foundation ? "S3 foundation generated" : "Implementation needed",
      foundation, compute, api:!existing&&match?.name==="Amazon API Gateway"&&n.data.implementation==="iam-rag-api", summary:!existing&&n.data.provider==="aws"&&match?.name==="AWS Lambda"&&n.data.implementation==="bedrock-summary", settings: runtimeSettings(n.data.config),
    };
  });
  const asyncPlan=asyncPipelinePlan(project,rows);
  const modelPlan=summaryPlan(project,rows);
  const retrievalPlan=ragPlan(project,rows);
  const connectorPlan=sourceContractPlan(project,rows,retrievalPlan);
  const browserPlan=webPlan(project,rows,retrievalPlan);
  const accessPlan=storageAccessPlan(project,rows);
  for(const row of rows){
    row.reference=accessPlan.bindings.some(b=>b.id===row.id);
    row.externalReference=row.existing && row.provider==="tools" && nodes.find(n=>n.id===row.id)?.data.binding==="web-browser";
    row.existingServiceReference=existingReference(nodes.find(n=>n.id===row.id));
    row.implemented=!!row.existingServiceReference||row.externalReference||row.foundation||row.compute||row.reference||browserPlan.componentIds.includes(row.id)||connectorPlan.sources.some(s=>s.id===row.id)||retrievalPlan.componentIds.includes(row.id)||modelPlan.modelIds.includes(row.id)||modelPlan.entries.some(e=>e.worker.id===row.id)||asyncPlan.componentIds.includes(row.id);
    if(asyncPlan.componentIds.includes(row.id))row.terraform="Typed asynchronous pipeline implementation generated";
    if(modelPlan.modelIds.includes(row.id))row.terraform="Existing regional foundation model — required model ID input generated";
    if(modelPlan.entries.some(e=>e.worker.id===row.id))row.terraform="Bedrock summary handler, scoped model permission and caller binding generated";
    if(retrievalPlan.componentIds.includes(row.id))row.terraform="Bounded IAM-authenticated RAG implementation generated";
    if(connectorPlan.sources.some(s=>s.id===row.id))row.terraform="Local source-contract runner generated; native vendor integration unverified";
    if(browserPlan.componentIds.includes(row.id))row.terraform="Private web hosting and Cognito authorization-code/PKCE sign-in generated";
    if(row.compute){row.terraform="Text-statistics function, execution role, logs, version and alias generated";row.resources=["aws_lambda_function","aws_iam_role","aws_iam_role_policy","aws_cloudwatch_log_group","aws_lambda_alias","aws_lambda_permission"];}
    if(row.externalReference)row.terraform="External browser — no infrastructure to provision; connection behavior still requires validation";
    if(row.existingServiceReference){row.resources=[];row.terraform="Existing service reference — preserved without provisioning or import; behavior and connections remain unverified";}
    if(row.reference){row.terraform="Existing IAM principal — required ARN input generated";row.service="Existing AWS IAM principal";row.selection="Explicit principal binding";}
  }
  const connections = project.edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ id: e.id, source: e.source, target: e.target, data: e.label || "data", generated: (accessPlan.connections.some(c=>c.id===e.id)||asyncPlan.edgeIds.includes(e.id)||modelPlan.edgeIds.includes(e.id)||retrievalPlan.edgeIds.includes(e.id)||connectorPlan.connections.some(c=>c.id===e.id)||browserPlan.edgeIds.includes(e.id)), status: (accessPlan.connections.some(c=>c.id===e.id)||asyncPlan.edgeIds.includes(e.id)||modelPlan.edgeIds.includes(e.id)||retrievalPlan.edgeIds.includes(e.id)||connectorPlan.connections.some(c=>c.id===e.id)||browserPlan.edgeIds.includes(e.id)) ? "Scoped access policy generated; account and runtime verification required" : "Application integration and permissions not implemented" }));
  const missingStorageAccess=rows.filter(r=>(r.foundation||r.compute||r.summary||r.api)&&!accessPlan.connections.some(e=>e.target===r.id)&&!browserPlan.entries.some(e=>e.api.id===r.id));
  const gaps = [
    ...missingStorageAccess.map(r=>`${r.label}: explicit caller access contract is missing.`),
    ...rows.filter((r) => !r.implemented).map((r) => `${r.label}: ${r.terraform}.`),
    ...connections.filter(e=>!e.generated).map((e) => `Wire ${e.source} → ${e.target}: implement data flow, access policy and acceptance test.`),
    ...(!rows.length ? ["No resources in the design yet."] : []),
  ];
  const encode=value=>Array.from(new TextEncoder().encode(value),b=>b.toString(16).padStart(2,"0")).join("");
  const gapDetails=[
    ...missingStorageAccess.map(r=>({id:`access-${r.address}`,componentIds:[r.id],taskId:`TASK-RESOURCE-${encode(r.id)}`,message:`${r.label}: explicit caller access contract is missing.`})),
    ...rows.filter(r=>!r.implemented).map(r=>({id:`resource-${r.address}`,componentIds:[r.id],taskId:`TASK-RESOURCE-${encode(r.id)}`,message:`${r.label}: ${r.terraform}.`})),
    ...connections.filter(e=>!e.generated).map(e=>({id:`connection-${encode(e.id)}`,edgeIds:[e.id],taskId:`TASK-INTEGRATION-${encode(e.id)}`,message:`Wire ${e.source} → ${e.target}: implement data flow, access policy and acceptance test.`})),
    ...(!rows.length?[{id:'architecture-empty',taskId:'TASK-SCOPE',message:'No resources in the design yet.'}]:[]),
  ];
  return { revision: project.revision, rows, connections, accessPlan, asyncPlan, summaryPlan:modelPlan, ragPlan:retrievalPlan, sourceContractPlan:connectorPlan, webPlan:browserPlan, gaps, gapDetails, scope: "Diagram-derived resource schedule; service choices and resource types require engineering review.", sources: [
    "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket",
    "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail",
    "https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_knowledge_base",
    "https://aws.amazon.com/bedrock/pricing/",
  ] };
}

export function resourceMarkdown(project) {
  const plan = resourcePlan(project);
  const c = (v) => String(v ?? "").replaceAll("|", "\\|").replaceAll("\n", " ");
  return `## Cloud resource schedule\n\n${plan.scope}\n\n| Block ID | Component | Provider | Service | Region | Ownership | Terraform coverage |\n|---|---|---|---|---|---|---|\n${plan.rows.map((r) => `| ${c(r.id)} | ${c(r.label)} | ${r.provider} | ${c(r.service)} | ${c(r.region)} | ${r.existing ? "Existing" : "Proposed"} | ${r.terraform} |`).join("\n")}\n\n### Resources and cost dimensions\n\n${plan.rows.map((r) => `- **${c(r.label)}** (${c(r.id)}): ${r.resources.join(", ") || "Resource types to confirm"}. ${r.costDrivers}. Depends on: ${r.dependencies.join(", ") || "none drawn"}.`).join("\n")}\n\n### Engineering work remaining\n\n${plan.gaps.map((g) => `- ${g}`).join("\n") || "S3 foundation only. Validate the plan, account, region, cost and security before applying."}\n\nReferences (resource semantics; not retrieved prices):\n${plan.sources.map((s) => `- ${s}`).join("\n")}\n`;
}
