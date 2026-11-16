# Research and decisions — 2026-11-16

## Product capability

Decision: prepare meaningful infrastructure migrations, not just notifications/version bumps. Rationale: AWS Health already identifies lifecycle events/affected resources; Renovate already updates Terraform dependencies. A strong model can perform isolated migrations; enduring value would require reliable inventory, coordination, validation and maintenance. Alternatives considered: provider alert feed (insufficient), architecture handoff (already core), performance optimization laboratory (large execution expansion).

Primary references checked during concept research:
- https://docs.renovatebot.com/modules/manager/terraform/ — updates providers/modules/constraints; do not claim that version updates are unique.
- https://docs.aws.amazon.com/health/latest/ug/aws-health-account-views.html — events and affected resource state; repo intent remains different from actual deployment.
- https://developer.hashicorp.com/terraform/language/syntax/configuration — parser must support actual HCL, not diagram regex.

## Execution and adapters

Decision: backend-neutral local core first, separate scoped GitHub broker and isolated check executor. Rationale: existing worker sessions provide integration candidates, not assurance that arbitrary repo tests are safe. Alternatives: run tests in checkout (rejected ambient secret/host risk), give GitHub token to agent (rejected), website diagram parser as authority (rejected incomplete language semantics).

Decision: Terraform AWS provider migration first with a reviewed per-recipe version matrix. Choose exact real source/target pair, parser/tool versions and migration oracle in T001/R0 using pinned official upgrade guides and reproducible failure. These are explicit research deliverables before coding, not fabricated resolved compatibility facts. If exact pair cannot demonstrate a meaningful change, R1 cannot begin.

Decision: use isolated overlays for proposed local/shared modules and record their digests; original Git/registry addresses in final patch require real version publication and human confirmations. Alternatives: invent a release tag or change customer module source to temporary disk (rejected).

## Governance and release

Decision: stable 0.3.0–0.6.0 proposals, no alpha/beta; numbers subject to current latest at release. Workstream does not reset027–029. Existing older constitution's local-only wording requires explicit alignment before hosted R4; plan cannot silently amend it. Owner-approved feature scope supplies authority for this specification, not production writes.

## Research backlog with blocking outputs

T001 must pin provider upgrade guide/source commits, Terraform tool hashes, parser/license decision, affected-schema diff, unsupported patterns and expected success/failure checks. T002 freezes fixtures and holdout. T003 qualifies worker isolation. R0 closes only when all outputs have receipts. No deployment plan/data migration qualification is inferred from local tests.
