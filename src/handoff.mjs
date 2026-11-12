// Derived engineering evidence. Presence of prose is not implementation or approval.
import {resourcePlan} from './resources.mjs';
import {estimate} from './estimate.mjs';
import {review} from './review.mjs';
import {requirementNumber} from './derive.mjs';
export const handoffKey=value=>Array.from(new TextEncoder().encode(String(value)),v=>v.toString(16).padStart(2,'0')).join('');
const resourceTask=id=>`TASK-RESOURCE-${handoffKey(id)}`;

const PROFILES = {
 'Amazon S3': [
  'Agree object ownership, retention/deletion, lifecycle and encryption/key policy; distinguish source data from Terraform state and build artifacts.',
  'Add least-privilege bucket access and transport policy; test denied access, version recovery and deletion behavior.'
 ],
 'AWS Lambda': [
  'Specify runtime, entry point, immutable package/image, memory, timeout and concurrency; identify the trigger and its invocation permissions.',
  'Define execution IAM, network egress, secret references and log retention; implement retries, idempotency, checkpoints and dead-letter handling where asynchronous.',
  'Test representative payload sizes, duplicate events, throttling and downstream failures; measure cold and warm execution where latency matters.'
 ],
 'Amazon OpenSearch': [
  'Choose a provisioned domain or Serverless explicitly; select lexical, vector or hybrid retrieval before creating resources.',
  'Define index mappings, document/version IDs, ACL and region filters, deletion propagation and reindexing; for vectors select embedding model and dimensions.',
  'Specify encryption, network and data-access policies, capacity and recovery; prove filtered retrieval excludes unauthorized titles, snippets and documents.'
 ],
 'Amazon OpenSearch Serverless': [
  'Specify collection type, encryption, network and data-access policies, private connectivity and capacity limits.',
  'Define index mappings and creation ownership; for vector search select embedding model/dimensions and query strategy.',
  'Test permissions, document deletion, capacity, reindex/recovery and source ACL freshness.'
 ],
 'Amazon OpenSearch domain': [
  'Specify engine version, node/storage sizing, availability layout, encryption, private connectivity and fine-grained access.',
  'Define index mappings, snapshot/restore, upgrades and capacity; for vectors select embedding model and dimensions.',
  'Test recovery, document deletion and ACL/region-filtered retrieval under the agreed workload.'
 ],
 'Amazon Bedrock': [
  'Select exact generation and, if needed, embedding model IDs, invocation API and inference mode; verify account access, regional availability and quotas with dated evidence.',
  'Map every inference destination to the agreed processing boundary; a regional endpoint or APAC profile does not by itself establish country-only processing.',
  'Implement scoped invocation IAM, token/time limits, retries and budget controls; keep source authorization before model invocation.',
  'Define prompt-injection handling, authorized citations, insufficient-evidence responses and output checks; test these separately from model guardrails.'
 ],
 'Amazon Bedrock Guardrails': [
  'Select supported policies, thresholds and a versioned guardrail; specify input/output invocation and behavior when checks fail or are unavailable.',
  'Evaluate false positives, bypasses and restricted content with fixtures; guardrails do not substitute for source ACL enforcement.'
 ],
 'Amazon Bedrock Knowledge Bases': [
  'Select the embedding model, backing store, data sources, chunking, synchronization and service roles explicitly.',
  'Verify connector support for source ACLs, deletions and freshness; implement missing permission enforcement before retrieval.',
  'Test sync failures, reindexing, authorized citations and country boundaries for ingestion, embeddings and generation.'
 ],
 'AWS App Runner': [
  'Verify account eligibility before retaining App Runner; it is closed to new customers. Record the hosting decision and current official availability evidence.',
  'Specify one deployment unit per actual application, immutable image, registry access, instance role, ingress/egress, health checks and scaling.',
  'Design identity sessions, secrets, custom domain/TLS, logs and rollback; test deployment health and source dependency failures.'
 ],
 'Amazon ECS': [
  'Choose explicit ECS/Fargate resources or a reviewed managed deployment mode; define the task image, execution/task roles and secret references.',
  'Specify subnets, security groups, ingress/load balancing, egress, health checks, scaling and deployment rollback.',
  'Measure resource limits and request latency; test unhealthy deployments, dependency failures and recovery.'
 ],
 'Amazon DynamoDB': [
  'Define partition/sort keys and access patterns, capacity mode, indexes, encryption, point-in-time recovery and deletion protection.',
  'Specify conditional writes, idempotency, TTL semantics and retention; test contention, throttling and restoration.'
 ],
 'Amazon SQS': [
  'Choose standard/FIFO semantics, encryption, queue policy, retention, visibility timeout and dead-letter/redrive settings.',
  'Define producer/consumer IAM and retries; prove duplicate processing is safe and poison messages can be recovered.'
 ],
 'Amazon CloudWatch': [
  'Define structured redacted logs, retention, metrics, alarms, dashboards and alert ownership for each component.',
  'Test ingestion failure, denied access and latency alarms; verify sensitive prompts, source text and credentials are excluded.'
 ],
};
export function engineeringSteps(row) {
 if(row.containerContract)return [`Review terraform/main.tf.json resource ${row.containerContract.type}.${row.address} and the associated variables in deployment.tfvars.json.example.`, `Build the supplied application image, pin ${row.address}_image to its SHA-256 digest, and verify it listens on port 8080; infrastructure does not establish application behavior.`, 'Run terraform validate and terraform test using tests/container.tftest.hcl; review private ingress, runtime identity, registry access, platform prerequisites and destination-specific startup/rollback tests before applying.'];
 if(row.externalReference)return ['Preserve the external browser; no resource or import is required.','Define and test its HTTPS/application interactions, including denied access and unavailable service behavior.'];
 if(row.existingServiceReference)return ['Preserve this externally managed service without creating or importing it.','Document its owner, endpoint, identity and integration contract; test actual connections separately.'];
 if(row.reference)return ['Bind the required Terraform ARN input to a reviewed existing same-account IAM role or user; never recreate the identity.','Verify scoped bucket/object permissions, effective boundaries and organization policies, versioned reads and denied access; the generated grant is not account-access evidence.'];
 if(row.existing)return [
  'Identify system owner, tenant/location, supported APIs and permitted read scopes; document a reference contract instead of recreating the system.',
  'Specify identity mapping, source permissions, pagination/rate limits, update/delete events and maximum synchronization lag.',
  'Define credential rotation, outages and recovery; test revoked access and unavailable sources using approved fixtures before live integration.'
 ];
 return PROFILES[row.service] || [
  `Confirm the exact ${row.provider} service, deployment mode, region and supported resource types using current primary documentation.`,
  'Specify runtime/artifact, identity, network paths, secrets, capacity, health checks and operational owner; resolve whether this is infrastructure or a responsibility within another application.',
  'Document service-specific failure modes, retention/recovery and acceptance tests; do not substitute a similarly named service or another provider.'
 ];
}

export function handoffAssessment(project, now = new Date()) {
 const resources=resourcePlan(project), decisions=(project.decisions||[]).filter(d=>d.status==='Accepted'), needs=project.needs||[], findings=[];
 const add=(id,priority,area,message,action,taskIds=['TASK-SCOPE'],componentIds=[],requirementIds=[])=>findings.push({id,priority,area,message,action,taskIds,componentIds,requirementIds,status:'open'});
 const costs=estimate(project,now);
 if(costs.gaps.length)add('cost-coverage',2,'cost',`${costs.gaps.length} cost worksheet gaps remain; unpriced resources are not free.`,'Complete usage assumptions and dated regional price sources; reconcile all billable dimensions with the reviewed plan.',['TASK-COST-BASELINE','TASK-COST']);
 if(!(project.facts||[]).some(f=>f.name==='budget.per_month')&&!needs.some(r=>r.category==='cost'))add('budget-target',2,'cost','No budget constraint is recorded.','Agree a budget or explicitly document that no budget limit was specified; do not invent a price target.',['TASK-COST-BASELINE']);
 for(const f of review(project).filter(f=>f.status==='open'&&['blocker','major'].includes(f.severity)))add(`review-${handoffKey(f.key)}`,f.severity==='blocker'?1:2,'security',f.statement,f.action,['TASK-SECURITY-DESIGN','TASK-SECURITY'],f.components);
 const regionDecisions=decisions.filter(d=>d.subject==='cloud.region').map(d=>String(d.decision||'').trim());
 if(new Set(regionDecisions).size>1)add('region-decisions-conflict',1,'placement','Multiple accepted deployment-region decisions disagree.','Resolve or supersede conflicting decisions explicitly; do not choose the most convenient value.');
 const agreed=subject=>decisions.some(d=>d.subject===subject&&String(d.decision||'').trim());
 if(!project.brief?.application?.trim())add('scope-outcome',1,'scope','No structured application outcome is recorded.','Confirm a concise outcome, intended users and exclusions; raw conversation fragments are not an implementation brief.');
 if(!(project.useCases||[]).length)add('scope-boundary',1,'scope','No explicit scope boundary is recorded.','Record included and excluded use cases before sizing or implementation.');
 if(!resources.rows.length)add('architecture-empty',1,'architecture','No deployable or existing components are described.','Define the components and interactions; an empty Terraform configuration is not a deployment.');
 if(resources.rows.some(r=>r.provider!=='tools'))for(const [subject,label]of [['platform.cloud','cloud provider'],['data.country','data country and processing boundary'],['cloud.region','deployment region']])if(!agreed(subject))add(`decision-${subject}`,1,'placement',`The ${label} is not independently confirmed.`,`Record an explicit ${subject} decision. Proposed diagram placement is not approval.`);
 for(const row of resources.rows){
  const task=[resourceTask(row.id)], ids=[row.id], key=handoffKey(row.id);
  if(!row.existing&&regionDecisions.length===1&&regionDecisions[0]!==row.region&&!/proposed|to be|unknown|confirm|select|tbd/i.test(row.region))add(`region-conflict-${key}`,1,'placement',`${row.label}: diagram placement differs from the accepted region decision.`,'Confirm whether this is intentional multi-region placement or stale design data; reconcile without silently overriding either source.',task,ids);
  if(row.selection==='Ambiguous service names')add(`service-ambiguous-${key}`,1,'architecture',`${row.label}: multiple service names match.`, 'Set an explicit service; do not generate infrastructure from this label.',task,ids);
  if(row.service==='Amazon OpenSearch')add(`search-mode-${key}`,1,'architecture',`${row.label}: OpenSearch deployment mode is unresolved.`,'Choose domain or Serverless and the retrieval/index design before generating resource types.',task,ids);
  if(!row.existing && /proposed|to be|unknown|confirm|select|tbd/i.test(row.region))add(`placement-${key}`,2,'placement',`${row.label}: placement is unresolved.`,'Verify service/model availability and record the chosen region without silently replacing proposed placement.',task,ids);
  if(!row.existing && !row.implemented)add(`implementation-${key}`,2,'implementation',`${row.label}: native infrastructure/application implementation is absent.`,engineeringSteps(row)[0],task,ids);
  if(row.reference)add(`existing-${key}`,2,'integration',`${row.label}: ARN input and bucket-scoped access policy are generated; account-specific verification remains.`,'Supply the existing same-account role/user ARN; verify effective IAM permissions, organization controls and positive/negative runtime access. No identity is created or modified.',task,ids);
  else if(row.existing)add(`existing-${key}`,2,'integration',`${row.label}: existing-system contract and access are unverified.`,engineeringSteps(row)[0],task,ids);
 }
 const appRunner=resources.rows.filter(r=>r.service==='AWS App Runner'&&!r.existing);
 if(appRunner.length)add('service-lifecycle-apprunner',1,'availability','App Runner eligibility needs verification.','AWS closed App Runner to new customers. Verify existing-customer eligibility or agree an alternative. Source: https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html (reviewed 2026-11-07).',appRunner.map(r=>resourceTask(r.id)),appRunner.map(r=>r.id));
 const apps=resources.rows.filter(r=>['AWS App Runner','Amazon ECS'].includes(r.service));
 if(apps.length>1)add('deployment-unit-mapping',1,'architecture','Multiple application blocks may represent shared responsibilities.','Map logical blocks to physical deployment units. Preserve accepted consolidation decisions; do not create one service per diagram block automatically.',apps.map(r=>resourceTask(r.id)),apps.map(r=>r.id));
 if(!needs.length)add('requirements-empty',1,'acceptance','No acceptance requirements are recorded.','Agree observable behavior and success criteria before declaring the handoff implementation-ready.');
 for(const r of needs){
  const number=requirementNumber(project,r.id),task=[`TASK-ACCEPTANCE-${handoffKey(r.id)}`],key=handoffKey(r.id);
  if(r.source!=='user')add(`requirement-proposed-${key}`,1,'acceptance',`${number} remains proposed.`,'Confirm, revise or explicitly defer this requirement; do not promote it through generation.',task,[],[r.id]);
  const missing=(r.links||[]).filter(id=>!resources.rows.some(row=>row.id===id));
  if(!r.links?.length||missing.length)add(`traceability-${key}`,2,'traceability',`${number} has ${missing.length?'references to missing components':'no component links'}.`,'Map the requirement to relevant components or record why it is project-wide; do not guess the mapping.',task,[],[r.id]);
  // A scalar measure omits workload/window/negative cases, so never marks acceptance ready.
  add(`acceptance-${key}`,2,'acceptance',`${number}: executable acceptance evidence is not supplied.`,r.measure?'Define workload, measurement window, first-output versus completed-response boundary and repeatable positive/negative cases.':'Agree an observable pass/fail criterion, fixtures and evidence location.',task,r.links||[],[r.id]);
 }
 for(const q of (project.openQuestions||[]).filter(q=>q.status==='open'))add(`question-${handoffKey(q.id)}`,1,'decision',q.question,'Resolve or explicitly defer this question with an owner and affected tasks.');
 const order=['scope','architecture','placement','availability','security','decision','cost','acceptance','traceability','implementation','integration'];
 findings.sort((a,b)=>a.priority-b.priority||order.indexOf(a.area)-order.indexOf(b.area)||a.id.localeCompare(b.id));
 return {
  format:'atmem.handoff-assessment',version:1,designRevision:project.revision,
  status:'engineering_required',
  stages:{design:findings.some(f=>f.priority===1)?'decisions_required':'review_required',infrastructure:resources.gaps.length===0&&resources.rows.length?'generated_implementation_unverified':resources.rows.some(r=>r.implemented&&!r.existing)?'partial_implementation':'not_implemented',localValidation:'not_attached',cloudPlan:'not_run',staging:'not_verified',production:'approval_not_attached'},
  counts:{components:resources.rows.length,generatedFoundations:resources.rows.filter(r=>r.foundation).length,connections:resources.connections.length,priorityDecisions:findings.filter(f=>f.priority===1).length},
  nextAction:findings.find(f=>f.priority===1)?.action||'Review component engineering work and confirm the implementation scope.',
  findings,
  evidencePolicy:'Generated documents and asserted decisions are design evidence only. Schema validation, mock tests, account plans and deployed-system tests require separate receipts tied to the exact configuration. This export does not ingest implementation evidence.',
 };
}
export function handoffMarkdown(report){
 return `# Handoff readiness\n\nStatus: engineering required. No deployment readiness is implied.\n\n## Next action\n\n${report.nextAction}\n\n## Evidence stages\n\n${Object.entries(report.stages).map(([k,v])=>`- ${k}: ${v}`).join('\n')}\n\n${report.evidencePolicy}\n\n## Decisions and engineering gaps\n\n${report.findings.map(f=>`### ${f.id} — priority ${f.priority}\n\n${f.message}\n\nAction: ${f.action}\n\nTasks: ${f.taskIds.join(', ')}`).join('\n\n')}\n`;
}
