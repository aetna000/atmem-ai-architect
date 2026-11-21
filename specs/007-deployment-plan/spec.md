# Feature Specification: Deployment plan

**Feature Branch**: `007-deployment-plan`

**Created**: 2026-11-05

**Status**: Draft (plan JSON and Pulumi metadata scaffold exist)

**Input**: Journey step 5 — "Prepare a reviewable deployment plan and, as the product matures, support deployment to the selected provider. Keep the user in control of changes." First release — "Test the deployment path with a controlled example; automate broader deployment in stages."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A reviewable plan (Priority: P1)

The user generates a deployment plan for an environment (staging, production): ordered steps, resources to create per step, prerequisites (accounts, permissions, quotas), checks before and after each step, and rollback. The plan is infrastructure-as-code (Pulumi) plus a human-readable step list. Nothing runs.

**Acceptance Scenarios**:

1. **Given** a design with unresolved blockers (003), **Then** the plan is generated but marked not ready, with blockers listed.
2. **Given** a plan, **Then** each step lists required permissions as least-privilege policy statements for review.

---

### User Story 2 — Controlled deployment of one example (Priority: P2)

For the first validated provider and one representative scenario, the user previews (`pulumi preview`-equivalent) and then applies the plan to a sandbox account, step by step, approving each step. AtMem AI Architect shows the outcome and records it as evidence.

**Acceptance Scenarios**:

1. **Given** a preview, **Then** the user sees resources to add/change/delete before any apply.
2. **Given** an apply, **Then** it requires explicit approval per step and can be stopped between steps.
3. **Given** a failed step, **Then** subsequent steps don't run and rollback guidance is shown.

### Edge Cases

- Credentials: obtained from the provider's standard CLI/SDK chain at run time; never stored in the project.
- Drift between design and deployed state: shown as a diff; never auto-applied to the design.

## Requirements *(mandatory)*

- **FR-001**: Plans MUST be generated from project data and be reviewable before any execution.
- **FR-002**: Execution MUST be opt-in per environment and per step [NEEDS CLARIFICATION: how far release 1 automates execution — OD-5].
- **FR-003**: Release 1 deploys only the first validated provider [NEEDS CLARIFICATION: OD-1] and only the representative scenarios [NEEDS CLARIFICATION: OD-2].
- **FR-004**: Every execution MUST be logged with who approved it, what ran and the result.

## Success Criteria *(mandatory)*

- **SC-001**: The controlled example deploys to a sandbox and tears down cleanly 10 times in a row.
- **SC-002**: Zero executions without explicit approval in audit logs.

## Assumptions

- Pulumi remains the IaC path; provider-native resources replace the current metadata components once a provider is validated.
