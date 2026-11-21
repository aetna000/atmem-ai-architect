# Detailed implementation tasks

Snapshot e8135c50-0e2d-4b7d-b8b8-0f89dc92c540 · design r1 · generated 2026-11-10T08:00:00.000Z

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
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/BUILD.md, terraform/tests/invoice.tftest.hcl
- Requirements: project-wide

### Implementation steps

1. Inspect the destination repository and its instructions before changing files. Preserve existing conventions and useful implementation.
2. Use the supplied Python 3.13 Linux/amd64 API/worker and isolated parser images. Read terraform/applications/block_696e766f696365/BUILD.md and TESTING.md. Install the exact provider test-requirements.lock in a Linux Python environment or build Dockerfile.tests. Run tests/start-local-fixture.py only against an existing local Unix Docker socket, then tests/run.py with the owned loopback fixture. Keep SDK environments isolated. Do not ask the user to choose a port, command, queue or runtime already implemented here.
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
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/BUILD.md, terraform/tests/invoice.tftest.hcl
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

## TASK-CONTRACT-73746166662d75706c6f6164 — Define Staff browser → Invoice intake and review

- Phase: Contracts
- Status: todo
- Depends on: TASK-SCOPE
- Components: browser, invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Read the implemented browser-https contract in spec-kit/interfaces.json, retaining original component/edge IDs and requirements.
2. Inspect invoice_http.py and invoice_identity.py: raw PDF upload, immutable server-owned storage references, live SQL membership, revision-bound review/approval and denied uploader approvals. Run the shipped HTTP/identity/browser tests.
3. Keep synthetic protocol fixtures separate from independently authorized destination acceptance. Preserve unsupported edge/contract requirements as generator work; never rename/remove them to obtain a pass.

### Deliverables

- Versioned contract for edge staff-upload
- Contract tests and fixtures

### Done when

- Producer and consumer responsibilities and failure behavior are explicit.
- Contract tests cover valid input, invalid input and denied access.

## TASK-CONTRACT-617070726f7665642d616374696f6e — Define Invoice intake and review → Existing accounting service

- Phase: Contracts
- Status: todo
- Depends on: TASK-SCOPE
- Components: invoice, accounting
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Read the implemented approved-accounting-api contract in spec-kit/interfaces.json, retaining original component/edge IDs and requirements.
2. Inspect approved_http_destination.py and workflow_worker.py: existing accounting endpoint/scope/credential inputs, exact normalized-action-v1 request/receipt, approval digest, stable key, bounded TLS call and uncertain-outcome fencing. Run local TLS/worker/recovery tests; do not infer actual vendor API compatibility.
3. Keep synthetic protocol fixtures separate from independently authorized destination acceptance. Preserve unsupported edge/contract requirements as generator work; never rename/remove them to obtain a pass.

### Deliverables

- Versioned contract for edge approved-action
- Contract tests and fixtures

### Done when

- Producer and consumer responsibilities and failure behavior are explicit.
- Contract tests cover valid input, invalid input and denied access.

## TASK-RESOURCE-62726f77736572 — Integrate existing Staff browser

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-73746166662d75706c6f6164
- Components: browser
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Responsibility from the board: Not recorded; clarify before writing application behavior.
2. Verify Staff browser on tools in To be selected; check current provider documentation for region availability, quotas and supported integration methods.
3. Review the generated resources, runtime source and scoped permissions. Run shipped application/mock tests, then obtain account-plan and deployed acceptance evidence. Existing model bindings require reviewed regional model IDs.
4. Preserve the external browser; no resource or import is required.
5. Define and test its HTTPS/application interactions, including denied access and unavailable service behavior.
6. Implement the component’s application behavior and configuration, including access checks, error handling, logging and health checks where applicable.
7. Cover linked requirements: No requirements are linked; confirm expected behavior and traceability.
8. Add focused unit and contract tests. Record any unavailable dependency or remaining engineering gap instead of marking the task complete.

### Deliverables

- Infrastructure/reference implementation for component browser
- Application/configuration and tests for Staff browser

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-RESOURCE-696e766f696365 — Validate generated Invoice intake and review

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-73746166662d75706c6f6164, TASK-CONTRACT-617070726f7665642d616374696f6e
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Preserve this responsibility and linked requirements: Signed-in staff upload invoices; separate reviewers approve a revision before accounting delivery. Durable work, source evidence, uncertain-outcome recovery and 90-day retention are required..
2. Inspect terraform/main.tf.json, invoice-contract.json and resource-schedule.json. This composition generates the API, worker, isolated PDF parser, private originals/SQL queue, native staff identities and separate operating tasks. Additional drawn scope remains visible and blocks incomplete exports.
3. Read terraform/applications/block_696e766f696365/invoice_http.py, invoice_identity.py, invoice_processing.py, invoice_worker.py, approved_http_destination.py and workflow_schema.sql. Current SQL user/reviewer/supervisor admission is separate from valid native login.
4. Run the portable tests and independent image/parser checks; retain exact source, dependency, image and tool hashes. Local fixture/model/identity protocols do not prove native cloud behavior or extraction quality.
5. Keep API, worker, parser and operator credentials/permissions separate. Populate destination secret references outside Terraform/source; never give model/parser/public tools operator launch or SQL administrator authority.
6. Follow the explicit foundation → immutable image publication → manual SQL/bootstrap/membership → operating schedule/alert acceptance → application release sequence. Cloud access, publication, apply and migrations each require existing authorization.
7. Record the actual requirement-to-test outcomes, remaining destination/compatibility/security findings and approved owner decisions. No task is complete on generation alone.

### Deliverables

- terraform/applications/block_696e766f696365/runtime/parser sources and locks
- terraform/main.tf.json and native tests/invoice.tftest.hcl
- Protected local acceptance receipts and exact image/security evidence

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-RESOURCE-6163636f756e74696e67 — Integrate existing Existing accounting service

- Phase: Components
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN, TASK-COST-BASELINE, TASK-CONTRACT-617070726f7665642d616374696f6e
- Components: accounting
- Generated files: No implementation files generated yet
- Requirements: invoice-approval

### Implementation steps

1. Responsibility from the board: Externally owned service; endpoint/credential and exact idempotency contract are supplied/verified by its administrator. Never provision a replacement.
2. Verify Existing accounting service on tools in To be selected; check current provider documentation for region availability, quotas and supported integration methods.
3. Review the generated resources, runtime source and scoped permissions. Run shipped application/mock tests, then obtain account-plan and deployed acceptance evidence. Existing model bindings require reviewed regional model IDs.
4. Preserve this externally managed service without creating or importing it.
5. Document its owner, endpoint, identity and integration contract; test actual connections separately.
6. Implement the component’s application behavior and configuration, including access checks, error handling, logging and health checks where applicable.
7. Cover linked requirements: Requirement: Only a reviewer can approve the current extraction revision before accounting delivery; ordinary uploaders cannot approve.
8. Add focused unit and contract tests. Record any unavailable dependency or remaining engineering gap instead of marking the task complete.

### Deliverables

- Infrastructure/reference implementation for component accounting
- Application/configuration and tests for Existing accounting service

### Done when

- Behavior matches confirmed requirements and agreed interface contracts.
- No placeholders, missing IAM rules or unimplemented handlers are presented as complete.
- Resource changes and existing-system boundaries are reviewed.

## TASK-INTEGRATION-73746166662d75706c6f6164 — Wire Staff browser to Invoice intake and review

- Phase: Integration
- Status: todo
- Depends on: TASK-CONTRACT-73746166662d75706c6f6164, TASK-RESOURCE-62726f77736572, TASK-RESOURCE-696e766f696365
- Components: browser, invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Read the implemented browser-https contract in spec-kit/interfaces.json, retaining original component/edge IDs and requirements.
2. Inspect invoice_http.py and invoice_identity.py: raw PDF upload, immutable server-owned storage references, live SQL membership, revision-bound review/approval and denied uploader approvals. Run the shipped HTTP/identity/browser tests.
3. Keep synthetic protocol fixtures separate from independently authorized destination acceptance. Preserve unsupported edge/contract requirements as generator work; never rename/remove them to obtain a pass.

### Deliverables

- Integration implementation staff-upload
- Local contract/mock test evidence

### Done when

- Local behavior matches the contract; live verification remains pending.
- Failure paths are tested with fixtures and recoverable state.

## TASK-INTEGRATION-617070726f7665642d616374696f6e — Wire Invoice intake and review to Existing accounting service

- Phase: Integration
- Status: todo
- Depends on: TASK-CONTRACT-617070726f7665642d616374696f6e, TASK-RESOURCE-696e766f696365, TASK-RESOURCE-6163636f756e74696e67
- Components: invoice, accounting
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Read the implemented approved-accounting-api contract in spec-kit/interfaces.json, retaining original component/edge IDs and requirements.
2. Inspect approved_http_destination.py and workflow_worker.py: existing accounting endpoint/scope/credential inputs, exact normalized-action-v1 request/receipt, approval digest, stable key, bounded TLS call and uncertain-outcome fencing. Run local TLS/worker/recovery tests; do not infer actual vendor API compatibility.
3. Keep synthetic protocol fixtures separate from independently authorized destination acceptance. Preserve unsupported edge/contract requirements as generator work; never rename/remove them to obtain a pass.

### Deliverables

- Integration implementation approved-action
- Local contract/mock test evidence

### Done when

- Local behavior matches the contract; live verification remains pending.
- Failure paths are tested with fixtures and recoverable state.

## TASK-INTEGRATION-LIVE-73746166662d75706c6f6164 — Verify live Staff browser → Invoice intake and review

- Phase: Staging verification
- Status: todo
- Depends on: TASK-STAGING, TASK-INTEGRATION-73746166662d75706c6f6164
- Components: browser, invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Exercise edge staff-upload with approved staging services and representative sanitized data.
2. Verify identity, permission revocation, denied access, timeouts, duplicate events and recovery against the agreed contract.
3. Record deployed versions, trace IDs, commands and results; unavailable account/source access remains blocked.

### Deliverables

- Live integration evidence staff-upload

### Done when

- The authorized staging integration has observed results.
- Mock results are not substituted for live evidence.

## TASK-INTEGRATION-LIVE-617070726f7665642d616374696f6e — Verify live Invoice intake and review → Existing accounting service

- Phase: Staging verification
- Status: todo
- Depends on: TASK-STAGING, TASK-INTEGRATION-617070726f7665642d616374696f6e
- Components: invoice, accounting
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json, spec-kit/interfaces.json
- Requirements: project-wide

### Implementation steps

1. Exercise edge approved-action with approved staging services and representative sanitized data.
2. Verify identity, permission revocation, denied access, timeouts, duplicate events and recovery against the agreed contract.
3. Record deployed versions, trace IDs, commands and results; unavailable account/source access remains blocked.

### Deliverables

- Live integration evidence approved-action

### Done when

- The authorized staging integration has observed results.
- Mock results are not substituted for live evidence.

## TASK-ACCEPTANCE-696e766f6963652d617070726f76616c — Verify Requirement: Only a reviewer can approve the current extraction revision before accounting delivery; ordinary uploaders cannot approve.

- Phase: Acceptance
- Status: todo
- Depends on: TASK-SCOPE, TASK-STAGING, TASK-RESOURCE-696e766f696365, TASK-RESOURCE-6163636f756e74696e67, TASK-INTEGRATION-LIVE-73746166662d75706c6f6164, TASK-INTEGRATION-LIVE-617070726f7665642d616374696f6e
- Components: invoice, accounting
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Basis: Not recorded; rationale: Clarify with the user.
2. Agree an observable pass/fail criterion with the user before declaring this requirement verified.
3. Create repeatable positive and negative scenarios and record the command, environment, result and evidence path.
4. For performance, security or residency claims, use suitable measurements or configuration evidence; a diagram or mock does not prove compliance.

### Deliverables

- Acceptance test and evidence for Requirement

### Done when

- The agreed criterion has a reproducible result.
- Unconfirmed requirements and unavailable tests remain explicitly unresolved.

## TASK-INFRA-VALIDATION — Complete and validate the Terraform deployment

- Phase: Verification
- Status: todo
- Depends on: TASK-INFRA-STATIC, TASK-RESOURCE-62726f77736572, TASK-RESOURCE-696e766f696365, TASK-RESOURCE-6163636f756e74696e67, TASK-INTEGRATION-73746166662d75706c6f6164, TASK-INTEGRATION-617070726f7665642d616374696f6e
- Components: project-wide
- Generated files: terraform/main.tf.json, terraform/.terraform.lock.hcl, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/BUILD.md, terraform/tests/invoice.tftest.hcl
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
- Depends on: TASK-INFRA-VALIDATION, TASK-SECURITY-DESIGN, TASK-INVOICE-SOURCE-696e766f696365, TASK-INVOICE-STATE-696e766f696365
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
- Depends on: TASK-CLOUD-PLAN, TASK-COST, TASK-INVOICE-APPLICATION-696e766f696365
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
- Depends on: TASK-SECURITY-DESIGN, TASK-STAGING, TASK-RESOURCE-62726f77736572, TASK-RESOURCE-696e766f696365, TASK-RESOURCE-6163636f756e74696e67, TASK-INTEGRATION-LIVE-73746166662d75706c6f6164, TASK-INTEGRATION-LIVE-617070726f7665642d616374696f6e
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
- Depends on: TASK-INFRA-VALIDATION, TASK-SECURITY, TASK-ACCEPTANCE-696e766f6963652d617070726f76616c, TASK-INTEGRATION-LIVE-73746166662d75706c6f6164, TASK-INTEGRATION-LIVE-617070726f7665642d616374696f6e
- Components: project-wide
- Generated files: No implementation files generated yet
- Requirements: project-wide

### Implementation steps

1. Exercise the intended outcome: Twenty staff upload PDF invoices up to 10 MB, 500 per day in bursts of twenty. Extract supplier/date/total/currency. Three reviewers approve before the existing accounting system receives an idempotent action. Preserve originals and audit history for 90 days in Australia. Uncertain outcomes and poison work must be recoverable.
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

## TASK-INVOICE-SOURCE-696e766f696365 — Qualify the emitted invoice package locally

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-SETUP, TASK-SECURITY-DESIGN
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Read terraform/applications/block_696e766f696365/TESTING.md. Use the exact isolated provider test lock; run shipped tests on an owned loopback PostgreSQL fixture with nonce validation. Never use a client/cloud database.
2. From terraform/, run terraform init -backend=false, terraform validate and terraform test. Retain full native positive/negative-plan evidence; mocks do not inspect an account.
3. Build/test exact runtime, test and parser images from pinned bases/wheels/native packages. Test actual text/scanned PDF extraction, malformed/encrypted/oversize/page-limit behavior, extraction evidence validation, duplicate delivery/restart, review denial, approval edits, uncertain action recovery and expired-only cleanup.
4. Record dependency/security findings and source/image digests. Fix generator causes and regenerate, never hand-edit a single exported bundle.

### Deliverables

- Portable local suite receipt
- Native schema/mock, image/parser, security and failure-path evidence

### Done when

- Checks target this complete emitted source/dependency set.
- Failed, unavailable, stale or fixture-only results remain explicit.

## TASK-INVOICE-STATE-696e766f696365 — Verify protected state and environment custody

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-SCOPE
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Read terraform/STATE.md and backend.hcl.example. Production references its reviewed provider-specific protected state/lock backend, with no account/state deployment implicit.
2. Review actual state residency/custody, per-project/environment access, sensitive computed provider values, encryption and version recovery. Supply authentication only through the approved environment chain.
3. With explicit platform-access authorization, verify lock conflict/owner-safe unlock/recovery on an isolated test state. Do not migrate/adopt existing state or disable locking to bypass failure.

### Deliverables

- State owner/access/residency/recovery record
- Protected reviewed backend configuration; never in source

### Done when

- Actual state protocol and ownership/locking/recovery are evidenced before account planning.

## TASK-INVOICE-FOUNDATION-696e766f696365 — Apply only the reviewed invoice foundation

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-CLOUD-PLAN, TASK-COST
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Obtain explicit foundation apply authorization for the exact current plan. Set applications_enabled=false, operations_enabled=false and maintenance_enabled=false.
2. Verify new owned regional database/private routing, original store/lifecycle, registry, native identity and secret-reference configuration. Preserve external accounting, existing organization routes/groups and state.
3. Retain actual resources/identities and rollback/deletion protections; native resource existence does not prove application/SQL/model behavior.

### Deliverables

- Authorized foundation receipt and exact resource inventory

### Done when

- Reviewed foundation is observed; no application or scheduled privileged work is prematurely enabled.

## TASK-INVOICE-IMAGES-696e766f696365 — Publish qualified immutable API/worker and parser images

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-INVOICE-SOURCE-696e766f696365, TASK-INVOICE-FOUNDATION-696e766f696365
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Use the exact tested runtime/parser digests, registry namespace and supply-chain evidence. Obtain publication authorization; publish without mutable tags in runtime inputs.
2. Review open high-severity findings, native model availability/processing policy, host architecture and native parser redistribution notices. Do not represent cached scans or local protocol mocks as production approval.

### Deliverables

- Authorized immutable image publication and security decision records

### Done when

- The actual owned repository contains the qualified digests and unresolved findings have accountable decisions.

## TASK-INVOICE-BOOTSTRAP-696e766f696365 — Initialize owned SQL and admit verified staff

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-INVOICE-IMAGES-696e766f696365
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Keep application/maintenance flags false; enable only operations_enabled with the qualified runtime image. Review terraform/OPERATING_JOBS.md and exact operator_deployment output.
2. With separate operator launch/SQL authority, run the fixed initialize task and observe completion plus initialized:true. Never give the application/model an administrator credential.
3. Admit exact native staff subjects and separate SQL user/reviewer/supervisor memberships. Native login alone is not reviewer authority. Populate separate existing accounting/model/parser secret/policy references as documented, outside Terraform/source.
4. Verify native private SQL TLS, role marker/grants, duplicate bootstrap, denied runtime schema/audit mutations and wrong-account/identity behavior.

### Deliverables

- Observed owned bootstrap and membership/secret-reference acceptance

### Done when

- Fresh owned schema and correct restricted roles are evidenced; no unrelated deployment or role was adopted.

## TASK-INVOICE-OPERATIONS-696e766f696365 — Verify scheduled cleanup and actionable monitoring

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-INVOICE-BOOTSTRAP-696e766f696365
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Run fixed maintain/monitor tasks and inspect real successful count/status-only receipts. Verify actual native logging destination and existing on-call recipients/delivery.
2. Enable maintenance only after bootstrap. For IBM, explicitly run install-schedules and check-schedules through the isolated CLI context; these are owned Knative sources outside Terraform, and the boolean alone does not pause/delete installed timers.
3. Observe actual hourly monitor/daily cleanup and inject an approved synthetic failure/missing-run condition. Verify alert evaluation/first-sample or zero-sample behavior and real notification delivery.
4. Review 90-day access/retention eligibility, object versions, SQL backups and lifecycle lag; exercise the separate isolated restore/reconciliation procedure without replaying uncertain accounting effects.

### Deliverables

- Native schedule/task/monitor/alert and restore evidence

### Done when

- Ready timer configuration is distinguished from job completion and on-call delivery.
- Retention/restore/recovery limits remain explicit; no universal exact erasure claim.

## TASK-INVOICE-APPLICATION-696e766f696365 — Release and test the complete staff invoice journey

- Phase: Invoice delivery
- Status: todo
- Depends on: TASK-INVOICE-OPERATIONS-696e766f696365
- Components: invoice
- Generated files: terraform/applications/block_696e766f696365/durable_workflow.py, terraform/applications/block_696e766f696365/workflow_connection.py, terraform/applications/block_696e766f696365/workflow_contract.py, terraform/applications/block_696e766f696365/workflow_database.py, terraform/applications/block_696e766f696365/workflow_errors.py, terraform/applications/block_696e766f696365/workflow_process_stage.py, terraform/applications/block_696e766f696365/workflow_role_bootstrap.py, terraform/applications/block_696e766f696365/workflow_worker.py, terraform/applications/block_696e766f696365/invoice_document.py, terraform/applications/block_696e766f696365/invoice_extraction.py, terraform/applications/block_696e766f696365/invoice_object_store.py, terraform/applications/block_696e766f696365/invoice_http.py, terraform/applications/block_696e766f696365/invoice_identity.py, terraform/applications/block_696e766f696365/invoice_native.py, terraform/applications/block_696e766f696365/invoice_runtime_secrets.py, terraform/applications/block_696e766f696365/invoice_processing.py, terraform/applications/block_696e766f696365/invoice_parser_transport.py, terraform/applications/block_696e766f696365/invoice_stage.py, terraform/applications/block_696e766f696365/invoice_worker.py, terraform/applications/block_696e766f696365/invoice_web.py, terraform/applications/block_696e766f696365/approved_http_destination.py, terraform/applications/block_696e766f696365/structured_output.py, terraform/applications/block_696e766f696365/structured_http.py, terraform/applications/block_696e766f696365/policy_review.py, terraform/applications/block_696e766f696365/aws_json_model.py, terraform/applications/block_696e766f696365/azure_structured.py, terraform/applications/block_696e766f696365/gcp_structured.py, terraform/applications/block_696e766f696365/ibm_structured.py, terraform/applications/block_696e766f696365/invoice_parser_identity.py, terraform/applications/block_696e766f696365/invoice_retention.py, terraform/applications/block_696e766f696365/invoice_operations.py, terraform/applications/block_696e766f696365/invoice_operator.py, terraform/applications/block_696e766f696365/invoice_operator_core.py, terraform/applications/block_696e766f696365/invoice_configuration.py, terraform/applications/block_696e766f696365/invoice_maintenance.py, terraform/applications/block_696e766f696365/invoice_operator_job.py, terraform/applications/block_696e766f696365/workflow_schema.sql, terraform/applications/block_696e766f696365/invoice-web.html, terraform/applications/block_696e766f696365/invoice-web.css, terraform/applications/block_696e766f696365/invoice-web.js, terraform/applications/block_696e766f696365/rds-global-ca.pem, terraform/applications/block_696e766f696365/requirements.lock, terraform/applications/block_696e766f696365/dependency-sources.json, terraform/applications/block_696e766f696365/test-requirements.lock, terraform/applications/block_696e766f696365/test-dependency-sources.json, terraform/applications/block_696e766f696365/invoice-deployment.json, terraform/applications/block_696e766f696365/container-base.json, terraform/applications/block_696e766f696365/rds-ca-source.json, terraform/applications/block_696e766f696365/Dockerfile, terraform/applications/block_696e766f696365/.dockerignore, terraform/applications/block_696e766f696365/parser/invoice_document.py, terraform/applications/block_696e766f696365/parser/invoice_extraction.py, terraform/applications/block_696e766f696365/parser/structured_output.py, terraform/applications/block_696e766f696365/parser/invoice_parser_cli.py, terraform/applications/block_696e766f696365/parser/invoice_parser_service.py, terraform/applications/block_696e766f696365/parser/invoice_parser_identity.py, terraform/applications/block_696e766f696365/parser/parser-requirements.lock, terraform/applications/block_696e766f696365/parser/invoice-parser-python-lock.json, terraform/applications/block_696e766f696365/parser/invoice-parser-lock.json, terraform/applications/block_696e766f696365/parser/Dockerfile, terraform/applications/block_696e766f696365/parser/.dockerignore, terraform/applications/block_696e766f696365/BUILD.md, terraform/applications/block_696e766f696365/tests/invoice_extraction_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_storage_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_http_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_web_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_rpc_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_parser_identity_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_worker_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operations_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_acceptance.py, terraform/applications/block_696e766f696365/tests/invoice_operator_job_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_postgres_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_privileges_acceptance.py, terraform/applications/block_696e766f696365/tests/durable_fixture_tasks.py, terraform/applications/block_696e766f696365/tests/workflow_tls_destination_fixture.py, terraform/applications/block_696e766f696365/tests/start-local-fixture.py, terraform/applications/block_696e766f696365/test-fixtures/postgres-qualification-lock.json, terraform/applications/block_696e766f696365/test-fixtures/invoice-text.pdf.base64, terraform/applications/block_696e766f696365/test-fixtures/rds-global-ca.pem, terraform/applications/block_696e766f696365/test-scope.json, terraform/applications/block_696e766f696365/tests/run.py, terraform/applications/block_696e766f696365/TESTING.md, terraform/applications/block_696e766f696365/Dockerfile.tests, terraform/applications/block_696e766f696365/Dockerfile.tests.dockerignore, terraform/OPERATIONS.md, terraform/OPERATING_JOBS.md, terraform/existing-references.json, terraform/EXISTING-SYSTEMS.md, terraform/.terraform.lock.hcl, terraform/main.tf.json, terraform/deployment.tfvars.json.example, terraform/.gitignore, terraform/tests/invoice.tftest.hcl, terraform/README.md, terraform/invoice-deployment-boundary.json, terraform/invoice-contract.json, terraform/backend.hcl.example, terraform/STATE.md, terraform/generation-quality.json
- Requirements: invoice-approval

### Implementation steps

1. Obtain explicit application-release authorization for the exact current plan and digests. Enable applications_enabled only after native bootstrap/operations acceptance.
2. Exercise actual staff sign-in, upload/review/revision/approval, ordinary-uploader denial, extraction quality on representative invoices, duplicate bursts, restart recovery and preserved originals/history.
3. Independently verify existing accounting normalized-action-v1 compatibility and same-key idempotency before enabling uncertain replay. Check provider/residency/model-policy/identity/network paths and customer-data logging boundaries.
4. Retain original requirements and all meaningful limitations, failed checks and owner decisions; produce a deployment/rollback record without treating generated source as live acceptance.

### Deliverables

- Authorized application release and end-to-end evidence

### Done when

- Confirmed behavior and boundaries have actual results for this project; no unsupported requirement was removed.
