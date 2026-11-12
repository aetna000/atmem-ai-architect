# Implementation Spec Kit

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

This is an implementation handoff derived from the requirements, decisions and architecture. It is part of the specification, not a replacement for the requirements. It is a generated work breakdown, not evidence of completed code.

## Handoff readiness

10 priority decisions; infrastructure: generated_implementation_unverified. See readiness.md and readiness.json for linked gaps and evidence boundaries.

Next action: Record included and excluded use cases before sizing or implementation.

## Intended outcome

Build a public website assistant that answers questions from our twenty public help articles, cites the articles it used, and says when it does not know. We need to update and remove articles. It must not answer from private sources. Use Azure. Recommend a coherent system and the engineering choices. Ask only a small material business question when needed; do not make me configure the system.

## Confirmed design decisions

- platform.cloud: azure

## Implementation sequence

1. Confirm scope, country/region and open decisions.
2. Prepare the repository, toolchain and CI.
3. Define contracts for each connection.
4. Implement or reference each component.
5. Implement integrations locally; run static and mock checks continuously.
6. With explicit account authorization, review the real plan and costs; obtain separate staging deployment approval.
7. Deploy staging, verify live integrations, requirements and recovery; prepare separately approved production release.

Dependencies in tasks.json govern execution. Independent component tasks can proceed after their prerequisites; diagram cycles do not create circular build dependencies. Never execute every task blindly when a prerequisite is blocked.

## Infrastructure coverage

- Website visitors (faq-visitors): External browser — no infrastructure to provision; connection behavior still requires validation; tools, External client.
- Public help assistant (faq-app): Public-only cited FAQ source, browser, private catalog, separate editor/runtime roles and regional model transport generated; destination behavior unverified; azure, australiaeast.
- Authorized article editor (faq-editor): Existing public catalog editor — provider-native role/group input and separate conditional editor CLI generated; actual access unverified; tools, External operator.

## How to use this kit

Read contracts.md and tasks.md. Use tasks.json for machine-readable dependencies and acceptance checks. Keep progress.json as the implementation journal. Start by reporting the next actionable task and the most consequential unknown. Refine this plan into repository-specific code/file changes once the repository and runtime are known; do not pretend those details were provided.

## Traceability

Requirements retain their own IDs and statements in context.json. Task links reference those IDs and the original component/edge IDs. Keep source requirements distinct from implementation decisions. Record changes in decision-log.md and reconcile substantive scope changes with the user.


Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

# Handoff readiness

Status: engineering required. No deployment readiness is implied.

## Next action

Record included and excluded use cases before sizing or implementation.

## Evidence stages

- design: decisions_required
- infrastructure: generated_implementation_unverified
- localValidation: not_attached
- cloudPlan: not_run
- staging: not_verified
- production: approval_not_attached

Generated documents and asserted decisions are design evidence only. Schema validation, mock tests, account plans and deployed-system tests require separate receipts tied to the exact configuration. This export does not ingest implementation evidence.

## Decisions and engineering gaps

### scope-boundary — priority 1

No explicit scope boundary is recorded.

Action: Record included and excluded use cases before sizing or implementation.

Tasks: TASK-SCOPE

### decision-cloud.region — priority 1

The deployment region is not independently confirmed.

Action: Record an explicit cloud.region decision. Proposed diagram placement is not approval.

Tasks: TASK-SCOPE

### decision-data.country — priority 1

The data country and processing boundary is not independently confirmed.

Action: Record an explicit data.country decision. Proposed diagram placement is not approval.

Tasks: TASK-SCOPE

### requirement-proposed-61692d61727469636c652d6c6966656379636c65 — priority 1

REQ-004 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d61727469636c652d6c6966656379636c65

### requirement-proposed-61692d6661712d6361706163697479 — priority 1

REQ-007 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d6661712d6361706163697479

### requirement-proposed-61692d6661712d66696c652d696e67657374696f6e — priority 1

REQ-008 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d6661712d66696c652d696e67657374696f6e

### requirement-proposed-61692d6c6f636174696f6e2d7472616e73706172656e6379 — priority 1

REQ-005 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d6c6f636174696f6e2d7472616e73706172656e6379

### requirement-proposed-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279 — priority 1

REQ-006 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279

### requirement-proposed-61692d7075626c69632d736f757263652d626f756e64617279 — priority 1

REQ-002 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d7075626c69632d736f757263652d626f756e64617279

### requirement-proposed-61692d737570706f727465642d616e737765722d6f722d6162737461696e — priority 1

REQ-003 remains proposed.

Action: Confirm, revise or explicitly defer this requirement; do not promote it through generation.

Tasks: TASK-ACCEPTANCE-61692d737570706f727465642d616e737765722d6f722d6162737461696e

### budget-target — priority 2

No budget constraint is recorded.

Action: Agree a budget or explicitly document that no budget limit was specified; do not invent a price target.

Tasks: TASK-COST-BASELINE

### cost-coverage — priority 2

3 cost worksheet gaps remain; unpriced resources are not free.

Action: Complete usage assumptions and dated regional price sources; reconcile all billable dimensions with the reviewed plan.

Tasks: TASK-COST-BASELINE, TASK-COST

### acceptance-61692d61727469636c652d6c6966656379636c65 — priority 2

REQ-004: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d61727469636c652d6c6966656379636c65

### acceptance-61692d6661712d6361706163697479 — priority 2

REQ-007: executable acceptance evidence is not supplied.

Action: Define workload, measurement window, first-output versus completed-response boundary and repeatable positive/negative cases.

Tasks: TASK-ACCEPTANCE-61692d6661712d6361706163697479

### acceptance-61692d6661712d66696c652d696e67657374696f6e — priority 2

REQ-008: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d6661712d66696c652d696e67657374696f6e

### acceptance-61692d6c6f636174696f6e2d7472616e73706172656e6379 — priority 2

REQ-005: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d6c6f636174696f6e2d7472616e73706172656e6379

### acceptance-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279 — priority 2

REQ-006: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279

### acceptance-61692d7075626c69632d736f757263652d626f756e64617279 — priority 2

REQ-002: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d7075626c69632d736f757263652d626f756e64617279

### acceptance-61692d737570706f727465642d616e737765722d6f722d6162737461696e — priority 2

REQ-003: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-61692d737570706f727465642d616e737765722d6f722d6162737461696e

### acceptance-7265712d6261646434613632 — priority 2

REQ-001: executable acceptance evidence is not supplied.

Action: Agree an observable pass/fail criterion, fixtures and evidence location.

Tasks: TASK-ACCEPTANCE-7265712d6261646434613632

### traceability-7265712d6261646434613632 — priority 2

REQ-001 has no component links.

Action: Map the requirement to relevant components or record why it is project-wide; do not guess the mapping.

Tasks: TASK-ACCEPTANCE-7265712d6261646434613632

### existing-6661712d656469746f72 — priority 2

Authorized article editor: existing-system contract and access are unverified.

Action: Identify system owner, tenant/location, supported APIs and permitted read scopes; document a reference contract instead of recreating the system.

Tasks: TASK-RESOURCE-6661712d656469746f72

### existing-6661712d76697369746f7273 — priority 2

Website visitors: existing-system contract and access are unverified.

Action: Preserve the external browser; no resource or import is required.

Tasks: TASK-RESOURCE-6661712d76697369746f7273


# Component and interface contracts

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

The board describes intent. These contracts must be completed before integrations are declared implemented.

## Component faq-visitors: Website visitors

- Responsibility: Existing visitor browsers outside provisioning scope. Submit questions over HTTPS and receive answers with article citations or an explicit abstention. No visitor account is proposed.
- Service: Web browser
- Provider / placement: tools / External client
- Ownership: Existing system; confirm access and ownership
- Implementation task: TASK-RESOURCE-6661712d76697369746f7273
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Preserve the external browser; no resource or import is required.
- Define and test its HTTPS/application interactions, including denied access and unavailable service behavior.

## Component faq-app: Public help assistant

- Responsibility: Proposed composed public-faq-app on Azure App Service. Owns the browser/API, private Azure Blob Storage versioned public-article catalog, regional Azure model transport and separate editor/runtime identities; these are internal module resources, not additional independent deployments.

Included scope: anonymous visitor questions, cited answers or explicit abstention, and authorized CLI publication/update/deletion of twenty supplied public UTF-8 article files under 30 KB each. Only approved public articles may ground answers. Private-source ingestion, arbitrary URL fetching and visitor editing are excluded. No visitor account is required. Additional business actions, private enterprise access and general workflows are outside this proposed scope.

Retrieval recommendation: bounded keyword ranking inside the application over the current curated catalog, supplying at most two complete retrieved articles to the model. This avoids a separate managed search service, embeddings pipeline and vector database for this small collection. Keyword matching can miss paraphrases; qualify it with representative questions before launch. Do not claim semantic search or guaranteed factual accuracy. Treat questions and articles as untrusted data. Validate returned source membership and exact supporting quotes, and abstain when support is insufficient; valid citations alone do not prove entailment.

The authorized editor CLI conditionally adds, updates and removes articles. Conflicting writes fail; in-flight source changes withhold affected answers, and there is no cached-source fallback. Runtime has read-only catalog access. Exact editor identity and scoped destination permissions remain required, unverified inputs. Files are already UTF-8, so no PDF extraction or source connector is proposed.

Capacity evidence: user expects about 1,000 questions per day and five at once. Use approximately 30,000 questions per 30-day month only as an estimating convention. Propose one small always-on App Service instance initially, subject to measured capacity, model quota and destination review; no SKU or availability guarantee is established. The implementation admits at most five concurrent requests per instance; overload must be bounded and visibly rejected or retried rather than silently exceeding that limit. Built-in bounds remain 100 public articles, 30000 bytes per article, 2000-byte questions and two complete retrieved articles. Verify supplied file byte sizes against that exact limit. Do not treat these bounds as an invoice cap.

Location: Australia is preferred, not a confirmed Australian-only processing rule. Australia East (australiaeast) is proposed for application and storage, not approved. Australian application/storage placement does not establish model inference location. Before inference, verify exact Azure model/version, deployment type, availability, quota, processing geography, retention and abuse-monitoring policy. Do not silently select Global or Data Zone inference, overseas fallback or cross-region recovery. Present proposed processing outside Australia for user review. One region is proposed; zone redundancy and regional recovery are not established. Visitor browsers may be outside Australia.

Operations proposals: exclude question text and article bodies from application logs; record request outcomes, latency, errors, abstentions and catalog revision identifiers. Platform/model logging and retention need separate verification. Provide an editor runbook for conditional changes and reviewed recovery from a known catalog revision, with deliberate deletion semantics so deleted content is not silently restored. Operational ownership, response-time expectations and recovery targets remain open. Public endpoint abuse controls and spending alerts require implementation review; concurrency limits alone do not prevent sustained spend.

Acceptance work: bind checks to the emitted artifact; test anonymous question access, denial of unauthorized catalog writes, editor add/update/delete and stale-write conflicts, removed-source exclusion, source changes during a request, citation membership/supporting quotes, unsupported-question abstention, prompt-injection cases, catalog/model failures, five concurrent requests and overload behavior. Evaluate representative paraphrases and real-model answer support separately from scripted tests. Build, scan and test the emitted pinned Python 3.13 image; review native provider configuration, destination permissions and an account-specific plan. No exported artifact, runtime report, live model test or deployment evidence is supplied here.

Price evidence: Azure Retail Prices API result dated 2026-11-09 quotes Australia East Blob Storage Hot LRS base storage at USD 0.02/GB-month, covering only the base tier up to 51200 GB. Source: https://prices.azure.com/api/retail/prices?%24filter=serviceName+eq+%27Storage%27+and+armRegionName+eq+%27australiaeast%27+and+meterName+eq+%27Hot+LRS+Data+Stored%27+and+priceType+eq+%27Consumption%27+and+productName+eq+%27Blob+Storage%27 . Twenty files imply less than approximately 0.0006 GB of raw article text, an upper bound rather than measured billed storage; catalog encoding and retained versions add storage. Current prices are missing for App Service compute, the exact model's input/output tokens, storage operations, transfer, logging and recovery storage. Model/token usage is unknown. External browsers and the existing editor are reference actors with no proposed hosted resource charge; their devices, connectivity and editor labor are outside the cloud subtotal. Monthly cloud running costs remain incomplete. One-off build/consulting effort, rates and exclusions are separately unestimated.
- Service: Azure App Service
- Provider / placement: azure / australiaeast
- Ownership: Proposed component
- Implementation task: TASK-RESOURCE-6661712d617070
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Confirm the exact azure service, deployment mode, region and supported resource types using current primary documentation.
- Specify runtime/artifact, identity, network paths, secrets, capacity, health checks and operational owner; resolve whether this is infrastructure or a responsibility within another application.
- Document service-specific failure modes, retention/recovery and acceptance tests; do not substitute a similarly named service or another provider.

## Component faq-editor: Authorized article editor

- Responsibility: Existing authorized operator outside provisioning scope; exact identity and destination permissions remain required inputs, not verified identities. Supplies twenty public UTF-8 help-article files under 30 KB each through the generated management CLI, then publishes, updates and removes catalog entries. Only public content is permitted. Conditional writes reject stale edits. This operational interface is separate from anonymous visitor access; it is not a browser editing endpoint. Editor ownership and recovery procedures remain to be assigned.
- Service: Existing authorized operator
- Provider / placement: tools / External operator
- Ownership: Existing system; confirm access and ownership
- Implementation task: TASK-RESOURCE-6661712d656469746f72
- Still to specify: runtime/configuration, identities, input/output schemas, health checks, failure behavior and operational owner.

- Identify system owner, tenant/location, supported APIs and permitted read scopes; document a reference contract instead of recreating the system.
- Specify identity mapping, source permissions, pagination/rate limits, update/delete events and maximum synchronization lag.
- Define credential rotation, outages and recovery; test revoked access and unavailable sources using approved fixtures before live integration.

## Interfaces

### faq-visitors-to-app: faq-visitors → faq-app

- Drawn payload/purpose: HTTPS questions → cited answers or “I don’t know”
- Contract task: TASK-CONTRACT-6661712d76697369746f72732d746f2d617070
- Integration task: TASK-INTEGRATION-6661712d76697369746f72732d746f2d617070
- Still to specify: protocol, schema/version, authentication, authorization, retries, timeouts, idempotency, error semantics, observability and test fixtures.

### faq-editor-to-app: faq-editor → faq-app

- Drawn payload/purpose: Authorized CLI: publish, update and remove public articles
- Contract task: TASK-CONTRACT-6661712d656469746f722d746f2d617070
- Integration task: TASK-INTEGRATION-6661712d656469746f722d746f2d617070
- Still to specify: protocol, schema/version, authentication, authorization, retries, timeouts, idempotency, error semantics, observability and test fixtures.


# Detailed implementation tasks

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

All tasks start as todo. This is a project-specific draft work breakdown; confirm unresolved decisions before dependent work.

## TASK-SCOPE — Confirm implementation scope and unresolved decisions

- Phase: Clarify
- Status: todo
- Depends on: none
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Read START_HERE.md, specification.md, project.atmem-ai-architect.json and spec-kit/context.json; summarise the intended outcome in your own words.
2. Review the existing brief, decisions and spec-kit/questions.md. Reuse answers, recommend routine engineering choices, and consolidate only consequential unresolved business decisions into a small question; record provenance.
3. Resolve conflicts between requirements, diagram and decisions explicitly. Confirm proposed requirements before treating them as agreed constraints.
4. Record repository, language/runtime, cloud account owner, environment, country/region and authorization boundaries. Keep unknowns explicit.

### Deliverables

- Implementation scope and decision log
- Answered or explicitly deferred questions, with affected tasks identified

### Done when

- Confirmed scope and acceptance expectations are recorded.
- No proposed requirement or unselected cloud is silently promoted to an agreed decision.

## TASK-SETUP — Prepare repository, toolchain and CI

- Phase: Foundation
- Status: todo
- Depends on: TASK-SCOPE
- Components: project-wide
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/BUILD.md, terraform/tests/public-faq.tftest.hcl
- Requirements: project-wide

### Implementation steps

1. Inspect the destination repository and its instructions before changing files. Preserve existing conventions and useful implementation.
2. Use emitted Python 3.13 applications/* source and BUILD.md. Install hash-locked runtime and test requirements in isolated provider environments and run faq_acceptance.py -v. Build, scan and test the exact pinned Linux/amd64 image; obtain authorization before publishing it to the reviewed existing registry. Supply its qualified digest. Supply reviewed destination and model/policy inputs from deployment.tfvars.json.example. Runtime, port, public-only retrieval, citations/abstention, source freshness, private catalog read role and separate editor grants are generated; do not ask the user to invent them. Seed only a reviewed genuinely public UTF-8 directory using public_catalog_admin.py init. Updates/deletions require inspecting the version and confirming the native conditional write. Test unknown questions, prompt injection, concurrent edits and in-flight source changes. Source/schema/mock checks are not real cloud IAM, model quality or deployed evidence. Keep AWS and IBM SDK environments separate; cloud access/plans/deployment require authorization.
3. Pin dependencies and Terraform/provider versions; configure formatting, linting, unit tests and secret scanning in CI.
4. Document local setup and use non-secret example configuration. Store secrets in the chosen secret manager or approved environment.

### Deliverables

- Repository structure and setup guide
- CI configuration and dependency locks

### Done when

- A clean checkout can install dependencies and run the documented local checks.
- CI executes actual tests and does not require production credentials.

## TASK-COST-BASELINE — Agree usage assumptions and an initial cost envelope

- Phase: Foundation
- Status: todo
- Depends on: TASK-SCOPE
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Record workload volumes, concurrency, document sizes, model token assumptions, retention and budget or explicitly deferred budget decisions.
2. Identify every proposed billable dimension, including networking, logs, backups, model/embedding requests, third-party licences and one-off delivery effort.
3. Use dated regional primary prices or quotes where available; show missing rates and currency boundaries without invented totals.

### Deliverables

- Initial cost model and assumptions
- Unpriced dimensions and budget decision

### Done when

- Unknown charges remain explicit.
- Capacity and cost assumptions are reviewed before service implementation.

## TASK-SECURITY-DESIGN — Define trust boundaries and deployment units

- Phase: Foundation
- Status: todo
- Depends on: TASK-SCOPE
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Map user identity, source permissions, data classification and every storage/processing destination; identify authoritative claims and failure behavior.
2. Map logical components to physical deployment units and preserve accepted consolidation decisions; name implementation and operational owners.
3. Agree network/egress, secrets, encryption, retention and recovery requirements before implementation; record alternatives and unresolved risks.

### Deliverables

- Threat model and deployment-unit map
- Security decisions and unresolved risks

### Done when

- Each trust boundary and physical unit has an owner.
- Proposed controls are not marked implemented.

## TASK-INFRA-STATIC — Establish local infrastructure checks

- Phase: Foundation
- Status: todo
- Depends on: TASK-SETUP
- Components: project-wide
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/BUILD.md, terraform/tests/public-faq.tftest.hcl
- Requirements: project-wide

### Implementation steps

1. Select a tested Terraform version and provider constraints; initialize with backend disabled and retain the dependency lock file.
2. Configure format, schema, secret and policy checks in CI without cloud credentials; add mock tests for resource and gate invariants.
3. Run these checks on every implementation change; record command, version, configuration identity and limitations.

### Deliverables

- Local CI checks and lock file
- Static/mock validation evidence

### Done when

- Checks run locally without account access.
- Schema and mocks are reported independently from account plans and deployed tests.

## TASK-CONTRACT-6661712d76697369746f72732d746f2d617070 — Define Website visitors → Public help assistant

- Phase: Contracts
- Status: todo
- Depends on: TASK-SCOPE
- Components: faq-visitors, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Inspect connection faq-visitors-to-app: HTTPS questions → cited answers or “I don’t know”. Determine whether it is an API call, event, batch job or data access path.
2. Specify request/event schema, response/output schema, ownership, authentication, authorization and data classification.
3. Agree timeout, retries, idempotency, failure behavior and observability; define versioning and compatibility rules.
4. Write an executable contract test and representative sanitized fixtures. Do not invent endpoint names, payload fields or service guarantees as settled facts.

### Deliverables

- Versioned contract for edge faq-visitors-to-app
- Contract tests and fixtures

### Done when

- Producer and consumer responsibilities and failure behavior are explicit.
- Contract tests cover valid input, invalid input and denied access.

## TASK-CONTRACT-6661712d656469746f722d746f2d617070 — Define Authorized article editor → Public help assistant

- Phase: Contracts
- Status: todo
- Depends on: TASK-SCOPE
- Components: faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Inspect connection faq-editor-to-app: Authorized CLI: publish, update and remove public articles. Determine whether it is an API call, event, batch job or data access path.
2. Specify request/event schema, response/output schema, ownership, authentication, authorization and data classification.
3. Agree timeout, retries, idempotency, failure behavior and observability; define versioning and compatibility rules.
4. Write an executable contract test and representative sanitized fixtures. Do not invent endpoint names, payload fields or service guarantees as settled facts.

### Deliverables

- Versioned contract for edge faq-editor-to-app
- Contract tests and fixtures

### Done when

- Producer and consumer responsibilities and failure behavior are explicit.
- Contract tests cover valid input, invalid input and denied access.

## TASK-RESOURCE-6661712d76697369746f7273 — Integrate existing Website visitors

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-6661712d76697369746f72732d746f2d617070
- Components: faq-visitors
- Generated files: No implementation files generated yet
- Requirements: ai-public-access-editor-boundary

### Implementation steps

1. Responsibility from the board: Existing visitor browsers outside provisioning scope. Submit questions over HTTPS and receive answers with article citations or an explicit abstention. No visitor account is proposed.
2. Verify Web browser on tools in External client; check current provider documentation for region availability, quotas and supported integration methods.
3. Review the generated resources, runtime source and scoped permissions. Run shipped application/mock tests, then obtain account-plan and deployed acceptance evidence. Existing model bindings require reviewed regional model IDs.
4. Preserve the external browser; no resource or import is required.
5. Define and test its HTTPS/application interactions, including denied access and unavailable service behavior.
6. Implement the component’s application behavior and configuration, including access checks, error handling, logging and health checks where applicable.
7. Cover linked requirements: REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.
8. Add focused unit and contract tests. Record any unavailable dependency or remaining engineering gap instead of marking the task complete.

### Deliverables

- Infrastructure/reference implementation for component faq-visitors
- Application/configuration and tests for Website visitors

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-RESOURCE-6661712d617070 — Validate generated Public help assistant

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-6661712d76697369746f72732d746f2d617070, TASK-CONTRACT-6661712d656469746f722d746f2d617070
- Components: faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-public-source-boundary, ai-supported-answer-or-abstain, ai-article-lifecycle, ai-location-transparency, ai-public-access-editor-boundary, ai-faq-capacity, ai-faq-file-ingestion

### Implementation steps

1. Responsibility from the board: Proposed composed public-faq-app on Azure App Service. Owns the browser/API, private Azure Blob Storage versioned public-article catalog, regional Azure model transport and separate editor/runtime identities; these are internal module resources, not additional independent deployments.

Included scope: anonymous visitor questions, cited answers or explicit abstention, and authorized CLI publication/update/deletion of twenty supplied public UTF-8 article files under 30 KB each. Only approved public articles may ground answers. Private-source ingestion, arbitrary URL fetching and visitor editing are excluded. No visitor account is required. Additional business actions, private enterprise access and general workflows are outside this proposed scope.

Retrieval recommendation: bounded keyword ranking inside the application over the current curated catalog, supplying at most two complete retrieved articles to the model. This avoids a separate managed search service, embeddings pipeline and vector database for this small collection. Keyword matching can miss paraphrases; qualify it with representative questions before launch. Do not claim semantic search or guaranteed factual accuracy. Treat questions and articles as untrusted data. Validate returned source membership and exact supporting quotes, and abstain when support is insufficient; valid citations alone do not prove entailment.

The authorized editor CLI conditionally adds, updates and removes articles. Conflicting writes fail; in-flight source changes withhold affected answers, and there is no cached-source fallback. Runtime has read-only catalog access. Exact editor identity and scoped destination permissions remain required, unverified inputs. Files are already UTF-8, so no PDF extraction or source connector is proposed.

Capacity evidence: user expects about 1,000 questions per day and five at once. Use approximately 30,000 questions per 30-day month only as an estimating convention. Propose one small always-on App Service instance initially, subject to measured capacity, model quota and destination review; no SKU or availability guarantee is established. The implementation admits at most five concurrent requests per instance; overload must be bounded and visibly rejected or retried rather than silently exceeding that limit. Built-in bounds remain 100 public articles, 30000 bytes per article, 2000-byte questions and two complete retrieved articles. Verify supplied file byte sizes against that exact limit. Do not treat these bounds as an invoice cap.

Location: Australia is preferred, not a confirmed Australian-only processing rule. Australia East (australiaeast) is proposed for application and storage, not approved. Australian application/storage placement does not establish model inference location. Before inference, verify exact Azure model/version, deployment type, availability, quota, processing geography, retention and abuse-monitoring policy. Do not silently select Global or Data Zone inference, overseas fallback or cross-region recovery. Present proposed processing outside Australia for user review. One region is proposed; zone redundancy and regional recovery are not established. Visitor browsers may be outside Australia.

Operations proposals: exclude question text and article bodies from application logs; record request outcomes, latency, errors, abstentions and catalog revision identifiers. Platform/model logging and retention need separate verification. Provide an editor runbook for conditional changes and reviewed recovery from a known catalog revision, with deliberate deletion semantics so deleted content is not silently restored. Operational ownership, response-time expectations and recovery targets remain open. Public endpoint abuse controls and spending alerts require implementation review; concurrency limits alone do not prevent sustained spend.

Acceptance work: bind checks to the emitted artifact; test anonymous question access, denial of unauthorized catalog writes, editor add/update/delete and stale-write conflicts, removed-source exclusion, source changes during a request, citation membership/supporting quotes, unsupported-question abstention, prompt-injection cases, catalog/model failures, five concurrent requests and overload behavior. Evaluate representative paraphrases and real-model answer support separately from scripted tests. Build, scan and test the emitted pinned Python 3.13 image; review native provider configuration, destination permissions and an account-specific plan. No exported artifact, runtime report, live model test or deployment evidence is supplied here.

Price evidence: Azure Retail Prices API result dated 2026-11-09 quotes Australia East Blob Storage Hot LRS base storage at USD 0.02/GB-month, covering only the base tier up to 51200 GB. Source: https://prices.azure.com/api/retail/prices?%24filter=serviceName+eq+%27Storage%27+and+armRegionName+eq+%27australiaeast%27+and+meterName+eq+%27Hot+LRS+Data+Stored%27+and+priceType+eq+%27Consumption%27+and+productName+eq+%27Blob+Storage%27 . Twenty files imply less than approximately 0.0006 GB of raw article text, an upper bound rather than measured billed storage; catalog encoding and retained versions add storage. Current prices are missing for App Service compute, the exact model's input/output tokens, storage operations, transfer, logging and recovery storage. Model/token usage is unknown. External browsers and the existing editor are reference actors with no proposed hosted resource charge; their devices, connectivity and editor labor are outside the cloud subtotal. Monthly cloud running costs remain incomplete. One-off build/consulting effort, rates and exclusions are separately unestimated.
2. Verify Azure App Service on azure in australiaeast; check current provider documentation for region availability, quotas and supported integration methods.
3. Review the generated resources, runtime source and scoped permissions. Run shipped application/mock tests, then obtain account-plan and deployed acceptance evidence. Existing model bindings require reviewed regional model IDs.
4. Confirm the exact azure service, deployment mode, region and supported resource types using current primary documentation.
5. Specify runtime/artifact, identity, network paths, secrets, capacity, health checks and operational owner; resolve whether this is infrastructure or a responsibility within another application.
6. Document service-specific failure modes, retention/recovery and acceptance tests; do not substitute a similarly named service or another provider.
7. Implement the component’s application behavior and configuration, including access checks, error handling, logging and health checks where applicable.
8. Cover linked requirements: REQ-002: The assistant must use only the approved public-help-article catalog for retrieval and answer grounding, with no private-source ingestion or arbitrary URL retrieval.; REQ-003: When current approved articles do not adequately support an answer, the assistant must explicitly say it does not know rather than provide an unsupported answer.; REQ-004: Authorized editors must be able to publish, update and remove public articles through a separate management interface; conflicting edits must be rejected and answers must be withheld if their supporting sources change during processing.; REQ-005: Prefer Australian application hosting, article storage and model processing. Before enabling inference, document the selected model deployment's processing geography, retention, logging and recovery locations, identify unverified limitations, and present any proposed processing outside Australia for review. The preference must not be represented as confirmed Australian-only residency.; REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.; REQ-007: The application must support the expected workload of approximately 1,000 questions daily and five simultaneous questions, subject to artifact-bound load tests and verified model quotas; excess concurrency must receive controlled overload handling.; REQ-008: The editor workflow must accept the twenty supplied public UTF-8 article files, validate each against the implementation's exact 30000-byte limit, and reject invalid or oversized files explicitly without silent truncation.
9. Add focused unit and contract tests. Record any unavailable dependency or remaining engineering gap instead of marking the task complete.

### Deliverables

- Infrastructure/reference implementation for component faq-app
- Application/configuration and tests for Public help assistant

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-RESOURCE-6661712d656469746f72 — Integrate existing Authorized article editor

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-6661712d656469746f722d746f2d617070
- Components: faq-editor
- Generated files: No implementation files generated yet
- Requirements: ai-public-source-boundary, ai-article-lifecycle, ai-public-access-editor-boundary, ai-faq-file-ingestion

### Implementation steps

1. Responsibility from the board: Existing authorized operator outside provisioning scope; exact identity and destination permissions remain required inputs, not verified identities. Supplies twenty public UTF-8 help-article files under 30 KB each through the generated management CLI, then publishes, updates and removes catalog entries. Only public content is permitted. Conditional writes reject stale edits. This operational interface is separate from anonymous visitor access; it is not a browser editing endpoint. Editor ownership and recovery procedures remain to be assigned.
2. Verify Existing authorized operator on tools in External operator; check current provider documentation for region availability, quotas and supported integration methods.
3. Review the generated resources, runtime source and scoped permissions. Run shipped application/mock tests, then obtain account-plan and deployed acceptance evidence. Existing model bindings require reviewed regional model IDs.
4. Identify system owner, tenant/location, supported APIs and permitted read scopes; document a reference contract instead of recreating the system.
5. Specify identity mapping, source permissions, pagination/rate limits, update/delete events and maximum synchronization lag.
6. Define credential rotation, outages and recovery; test revoked access and unavailable sources using approved fixtures before live integration.
7. Implement the component’s application behavior and configuration, including access checks, error handling, logging and health checks where applicable.
8. Cover linked requirements: REQ-002: The assistant must use only the approved public-help-article catalog for retrieval and answer grounding, with no private-source ingestion or arbitrary URL retrieval.; REQ-004: Authorized editors must be able to publish, update and remove public articles through a separate management interface; conflicting edits must be rejected and answers must be withheld if their supporting sources change during processing.; REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.; REQ-008: The editor workflow must accept the twenty supplied public UTF-8 article files, validate each against the implementation's exact 30000-byte limit, and reject invalid or oversized files explicitly without silent truncation.
9. Add focused unit and contract tests. Record any unavailable dependency or remaining engineering gap instead of marking the task complete.

### Deliverables

- Infrastructure/reference implementation for component faq-editor
- Application/configuration and tests for Authorized article editor

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-INTEGRATION-6661712d76697369746f72732d746f2d617070 — Wire Website visitors to Public help assistant

- Phase: Integration
- Status: todo
- Depends on: TASK-CONTRACT-6661712d76697369746f72732d746f2d617070, TASK-RESOURCE-6661712d76697369746f7273, TASK-RESOURCE-6661712d617070
- Components: faq-visitors, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Review the generated browser-https contract for edge faq-visitors-to-app in spec-kit/interfaces.json and its linked emitted files. Supply only the documented destination inputs and verify the selected authorization boundary.
2. Configure least-privilege identities, network paths, secrets references and producer/consumer settings.
3. Implement and test the integration locally with sanitized fixtures and mocks, including timeout, retries, duplicate requests and denied access. Live verification follows authorized staging.
4. Record trace IDs, outputs and failure cases; distinguish mocked contract checks from tests against real services.

### Deliverables

- Integration implementation faq-visitors-to-app
- Local contract/mock test evidence

### Done when

- Local behavior matches the contract; live verification remains pending.
- Failure paths are tested with fixtures and recoverable state.

## TASK-INTEGRATION-6661712d656469746f722d746f2d617070 — Wire Authorized article editor to Public help assistant

- Phase: Integration
- Status: todo
- Depends on: TASK-CONTRACT-6661712d656469746f722d746f2d617070, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72
- Components: faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Review the generated public-catalog-edit contract for edge faq-editor-to-app in spec-kit/interfaces.json and its linked emitted files. Supply only the documented destination inputs and verify the selected authorization boundary.
2. Configure least-privilege identities, network paths, secrets references and producer/consumer settings.
3. Implement and test the integration locally with sanitized fixtures and mocks, including timeout, retries, duplicate requests and denied access. Live verification follows authorized staging.
4. Record trace IDs, outputs and failure cases; distinguish mocked contract checks from tests against real services.

### Deliverables

- Integration implementation faq-editor-to-app
- Local contract/mock test evidence

### Done when

- Local behavior matches the contract; live verification remains pending.
- Failure paths are tested with fixtures and recoverable state.

## TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070 — Verify live Website visitors → Public help assistant

- Phase: Staging verification
- Status: todo
- Depends on: TASK-STAGING, TASK-INTEGRATION-6661712d76697369746f72732d746f2d617070
- Components: faq-visitors, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Exercise edge faq-visitors-to-app with approved staging services and representative sanitized data.
2. Verify identity, permission revocation, denied access, timeouts, duplicate events and recovery against the agreed contract.
3. Record deployed versions, trace IDs, commands and results; unavailable account/source access remains blocked.

### Deliverables

- Live integration evidence faq-visitors-to-app

### Done when

- The authorized staging integration has observed results.
- Mock results are not substituted for live evidence.

## TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070 — Verify live Authorized article editor → Public help assistant

- Phase: Staging verification
- Status: todo
- Depends on: TASK-STAGING, TASK-INTEGRATION-6661712d656469746f722d746f2d617070
- Components: faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Exercise edge faq-editor-to-app with approved staging services and representative sanitized data.
2. Verify identity, permission revocation, denied access, timeouts, duplicate events and recovery against the agreed contract.
3. Record deployed versions, trace IDs, commands and results; unavailable account/source access remains blocked.

### Deliverables

- Live integration evidence faq-editor-to-app

### Done when

- The authorized staging integration has observed results.
- Mock results are not substituted for live evidence.

## TASK-ACCEPTANCE-7265712d6261646434613632 — Verify REQ-001: Every answer shows its sources

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: req-badd4a62

### Implementation steps

1. Basis: Not recorded; rationale: Clarify with the user.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-001

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d7075626c69632d736f757263652d626f756e64617279 — Verify REQ-002: The assistant must use only the approved public-help-article catalog for retrieval and answer grounding, with no private-source ingestion or arbitrary URL retrieval.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-app, faq-editor
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-public-source-boundary

### Implementation steps

1. Basis: “It must not answer from private sources.”; rationale: Prevents private information or unrelated sources entering publicly accessible answers.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-002

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d737570706f727465642d616e737765722d6f722d6162737461696e — Verify REQ-003: When current approved articles do not adequately support an answer, the assistant must explicitly say it does not know rather than provide an unsupported answer.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-supported-answer-or-abstain

### Implementation steps

1. Basis: “says when it does not know”; rationale: An explicit abstention avoids presenting unsupported generated content as an authoritative help answer; model behavior still needs acceptance testing.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-003

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d61727469636c652d6c6966656379636c65 — Verify REQ-004: Authorized editors must be able to publish, update and remove public articles through a separate management interface; conflicting edits must be rejected and answers must be withheld if their supporting sources change during processing.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-article-lifecycle

### Implementation steps

1. Basis: “We need to update and remove articles.” The editor access boundary and conflict handling are proposed engineering choices.; rationale: Keeps public answers aligned with current content and prevents conflicting edits or deleted content from being served through stale fallbacks.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-004

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d6c6f636174696f6e2d7472616e73706172656e6379 — Verify REQ-005: Prefer Australian application hosting, article storage and model processing. Before enabling inference, document the selected model deployment's processing geography, retention, logging and recovery locations, identify unverified limitations, and present any proposed processing outside Australia for review. The preference must not be represented as confirmed Australian-only residency.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-location-transparency

### Implementation steps

1. Basis: User statement: “Australia is preferred; make model/data-location limitations explicit.” Proposed placement applies to faq-app and its owned storage/model integration.; rationale: An Australian hosting region alone does not establish where inference, monitoring or recovery processes data; explicit evidence prevents an unsupported residency claim.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-005

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279 — Verify REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d76697369746f7273, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-visitors, faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-public-access-editor-boundary

### Implementation steps

1. Basis: “Anonymous website visitors; an authorized editor manages the articles.” Existing components faq-visitors, faq-editor and faq-app.; rationale: Preserves the intended public user journey while keeping catalog modification outside anonymous visitor access.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-006

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d6661712d6361706163697479 — Verify REQ-007: The application must support the expected workload of approximately 1,000 questions daily and five simultaneous questions, subject to artifact-bound load tests and verified model quotas; excess concurrency must receive controlled overload handling.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-faq-capacity

### Implementation steps

1. Basis: “About 1,000 questions per day and five at once.”; rationale: Provides a concrete capacity acceptance case without inventing a response-time or availability commitment.
2. Implement a check for simultaneous_questions_supported >= 5 questions; specify test data, workload, measurement window and environment.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-007

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-ACCEPTANCE-61692d6661712d66696c652d696e67657374696f6e — Verify REQ-008: The editor workflow must accept the twenty supplied public UTF-8 article files, validate each against the implementation's exact 30000-byte limit, and reject invalid or oversized files explicitly without silent truncation.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: faq-editor, faq-app
- Generated files: terraform/applications/block_6661712d617070/public_faq.py, terraform/applications/block_6661712d617070/public_catalog_store.py, terraform/applications/block_6661712d617070/public_faq_app.py, terraform/applications/block_6661712d617070/structured_http.py, terraform/applications/block_6661712d617070/structured_output.py, terraform/applications/block_6661712d617070/azure_structured.py, terraform/applications/block_6661712d617070/public_catalog_admin.py, terraform/applications/block_6661712d617070/web/index.html, terraform/applications/block_6661712d617070/web/app.css, terraform/applications/block_6661712d617070/web/app.js, terraform/applications/block_6661712d617070/faq_core_acceptance.py, terraform/applications/block_6661712d617070/faq_http_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_admin_acceptance.py, terraform/applications/block_6661712d617070/faq_catalog_store_acceptance.py, terraform/applications/block_6661712d617070/faq_acceptance.py, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/dependency-sources.json, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/test-dependency-sources.json, terraform/applications/block_6661712d617070/container-base.json, terraform/applications/block_6661712d617070/output-contract.json, terraform/applications/block_6661712d617070/faq-deployment.json, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/.dockerignore, terraform/applications/block_6661712d617070/BUILD.md, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/tests/public-faq.tftest.hcl
- Requirements: ai-faq-file-ingestion

### Implementation steps

1. Basis: “Twenty public UTF-8 help articles under 30 KB each, supplied as files. No private content.”; rationale: Defines the ingestion boundary and prevents unnecessary document extraction or connector infrastructure.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for REQ-008

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-INFRA-VALIDATION — Complete and validate the Terraform deployment

- Phase: Verification
- Status: todo
- Depends on: TASK-INFRA-STATIC, TASK-RESOURCE-6661712d76697369746f7273, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-6661712d656469746f722d746f2d617070
- Components: project-wide
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_6661712d617070/requirements.lock, terraform/applications/block_6661712d617070/test-requirements.lock, terraform/applications/block_6661712d617070/Dockerfile, terraform/applications/block_6661712d617070/BUILD.md, terraform/tests/public-faq.tftest.hcl
- Requirements: project-wide

### Implementation steps

1. Review terraform/resource-schedule.json and every coverage gap. Implement missing resources and integrations before clearing any unfinished-work gate.
2. Run terraform init -backend=false and terraform validate; retain the provider lock file and capture diagnostics.
3. Add Terraform tests for required policy/configuration invariants and for the review gate. Mock-provider tests must be labelled as mocked.
4. Implement remote state configuration, locking, environment boundaries and secret references; document state bootstrap separately. Do not access the account in this local validation task.
5. Capture local checks against the complete generated configuration; leave account-specific planning and deployment to the explicitly authorized tasks.

### Deliverables

- Completed infrastructure implementation
- Validation logs and mock-test results; no account-plan claim

### Done when

- Every intended resource and connection has implementation or an explicitly accepted exclusion.
- Schema checks pass; actual account-plan status is reported independently.
- No apply is executed merely because a ZIP was handed over.

## TASK-CLOUD-PLAN — Review an authorized account-specific infrastructure plan

- Phase: Planning
- Status: todo
- Depends on: TASK-INFRA-VALIDATION, TASK-SECURITY-DESIGN
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Obtain explicit authorization for target-account access; confirm account, region, deployment role and separate state bootstrap permissions.
2. Run a real Terraform plan; record tool/provider versions, configuration identity, account, region and protected plan artifact.
3. Review replacements, deletions, IAM, regional service/model availability and quotas; do not apply or treat a static check as a cloud plan.

### Deliverables

- Reviewed account-specific plan and access record

### Done when

- Plan corresponds to the intended account and exact configuration.
- Unavailable access remains blocked; no deployment is performed by this task.

## TASK-STAGING — Approve and deploy the staging candidate

- Phase: Staging
- Status: todo
- Depends on: TASK-CLOUD-PLAN, TASK-COST
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Present the reviewed plan, scope, security decisions, cost and rollback procedure for explicit staging deployment authorization.
2. Apply only the approved current plan through the agreed process; verify artifact versions, service health and endpoint access.
3. Record actual deployed resources and smoke-check results; failed provisioning or missing source access blocks dependent live tests.

### Deliverables

- Staging approval and deployment receipt
- Staging health and rollback evidence

### Done when

- Staging deployment is explicitly authorized and observed.
- Production authorization is separate; an exported sketch is not deployment evidence.

## TASK-SECURITY — Review security, resilience and operational readiness

- Phase: Verification
- Status: todo
- Depends on: TASK-SECURITY-DESIGN, TASK-STAGING, TASK-RESOURCE-6661712d76697369746f7273, TASK-RESOURCE-6661712d617070, TASK-RESOURCE-6661712d656469746f72, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Map trust boundaries, identities and sensitive data flows from the diagram. Verify least privilege, encryption, data residency and audit logging.
2. Implement backup/restore, retention/deletion and recovery behavior according to confirmed requirements; test restoration and failure handling.
3. Define service health metrics, alerts, runbooks and incident ownership. Verify logging does not expose secrets or sensitive user content.
4. Record unresolved security risks and obtain decisions from their owners.

### Deliverables

- Security review and remediation evidence
- Operational runbook and recovery test evidence

### Done when

- Confirmed security and resilience requirements have evidence.
- Open risks have owners and are not silently marked resolved.

## TASK-COST — Reconcile implementation and costs

- Phase: Verification
- Status: todo
- Depends on: TASK-CLOUD-PLAN
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Reconcile the resource schedule, actual Terraform plan and estimate.json. Identify every billable service and usage dimension.
2. Refresh official pricing or quotes for the selected region, currency, model and capacity; record dates and sources.
3. Separate recurring cloud cost, one-off implementation effort, missing rates and excluded support costs. Agree budgets and alerts.

### Deliverables

- Updated resource/cost inventory and cost assumptions

### Done when

- No unpriced component is counted as free.
- Cost ranges and assumptions match the intended deployment.

## TASK-E2E — Prove the complete user journey

- Phase: Verification
- Status: todo
- Depends on: TASK-INFRA-VALIDATION, TASK-SECURITY, TASK-ACCEPTANCE-7265712d6261646434613632, TASK-ACCEPTANCE-61692d7075626c69632d736f757263652d626f756e64617279, TASK-ACCEPTANCE-61692d737570706f727465642d616e737765722d6f722d6162737461696e, TASK-ACCEPTANCE-61692d61727469636c652d6c6966656379636c65, TASK-ACCEPTANCE-61692d6c6f636174696f6e2d7472616e73706172656e6379, TASK-ACCEPTANCE-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279, TASK-ACCEPTANCE-61692d6661712d6361706163697479, TASK-ACCEPTANCE-61692d6661712d66696c652d696e67657374696f6e, TASK-INTEGRATION-LIVE-6661712d76697369746f72732d746f2d617070, TASK-INTEGRATION-LIVE-6661712d656469746f722d746f2d617070
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Exercise the intended outcome: Build a public website assistant that answers questions from our twenty public help articles, cites the articles it used, and says when it does not know. We need to update and remove articles. It must not answer from private sources. Use Azure. Recommend a coherent system and the engineering choices. Ask only a small material business question when needed; do not make me configure the system.
2. Use representative sanitized data and authorized non-production services. Test normal operation, malformed input, denied access and dependency failures.
3. Run the full acceptance suite and report actual versus expected results, including latency/capacity only where targets were agreed.
4. Capture reproducible test commands and evidence. Keep failed, skipped and mocked scenarios distinguishable.

### Deliverables

- End-to-end tests and results
- Requirement-to-test traceability

### Done when

- Each confirmed requirement is covered or has an explicitly accepted unresolved gap.
- No mock-only result is reported as proof of a working cloud deployment.

## TASK-RELEASE — Prepare an approved release and operational handover

- Phase: Handover
- Status: todo
- Depends on: TASK-E2E, TASK-COST
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Prepare deployment, migration, rollback and recovery procedures; identify owners and required account access.
2. Present the reviewed plan, test evidence, unresolved risks and cost estimate for deployment approval.
3. Only after explicit approval, deploy through the agreed process, run smoke checks, and document rollback readiness.
4. Record released versions, operational ownership and next tasks. Update progress.json and the decision log with evidence.

### Deliverables

- Release checklist and approval record
- Deployment/rollback runbook and final handover

### Done when

- Release approval and access are explicit.
- Deployment status reflects observed outcomes; pending access is reported as blocked.


# Validation and acceptance plan

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

1. Repository: install from a clean checkout; run formatter, linter, unit tests and dependency/secret checks.
2. Contracts: test each edge’s schema, authentication and failure behavior using sanitized fixtures.
3. Infrastructure: validate completed Terraform; run mock policy/gate tests separately from an authorized account-specific plan.
4. Requirements: execute every TASK-ACCEPTANCE task against its agreed criterion.
5. System: run TASK-E2E with representative data in an authorized environment; verify failures, recovery and denied access.
6. Operations: verify alerts, backup/restore, rollback and ownership.

For each check record command, tool versions, environment, timestamp, expected result, observed result, evidence file and limitations. Never turn skipped tests into passes. Exported diagrams and earlier proof-of-concept samples are not live integration evidence.

## Requirement traceability

- REQ-001 (req-badd4a62) → TASK-ACCEPTANCE-7265712d6261646434613632; Recorded from user discussion
- REQ-002 (ai-public-source-boundary) → TASK-ACCEPTANCE-61692d7075626c69632d736f757263652d626f756e64617279; Proposed; needs confirmation
- REQ-003 (ai-supported-answer-or-abstain) → TASK-ACCEPTANCE-61692d737570706f727465642d616e737765722d6f722d6162737461696e; Proposed; needs confirmation
- REQ-004 (ai-article-lifecycle) → TASK-ACCEPTANCE-61692d61727469636c652d6c6966656379636c65; Proposed; needs confirmation
- REQ-005 (ai-location-transparency) → TASK-ACCEPTANCE-61692d6c6f636174696f6e2d7472616e73706172656e6379; Proposed; needs confirmation
- REQ-006 (ai-public-access-editor-boundary) → TASK-ACCEPTANCE-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279; Proposed; needs confirmation
- REQ-007 (ai-faq-capacity) → TASK-ACCEPTANCE-61692d6661712d6361706163697479; Proposed; needs confirmation
- REQ-008 (ai-faq-file-ingestion) → TASK-ACCEPTANCE-61692d6661712d66696c652d696e67657374696f6e; Proposed; needs confirmation
