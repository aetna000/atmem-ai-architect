# Implementation Spec Kit

Snapshot b3d76c90-d37f-4688-87e4-0ae74d9ffd3c · design r1 · generated 2026-11-10T08:00:00.000Z

This is an implementation handoff derived from the requirements, decisions and architecture. It is part of the specification, not a replacement for the requirements. It is a generated work breakdown, not evidence of completed code.

## Handoff readiness

5 priority decisions; infrastructure: generated_implementation_unverified. See readiness.md and readiness.json for linked gaps and evidence boundaries.

Next action: Record included and excluded use cases before sizing or implementation.

## Intended outcome

Recorded project goal (scope requires confirmation): Twenty staff upload PDF invoices up to 10 MB, 500 per day in bursts of twenty. Extract supplier/date/total/currency. Three reviewers approve before the existing accounting system receives an idempotent action. Preserve originals and audit history for 90 days in Australia. Uncertain outcomes and poison work must be recoverable.

## Confirmed design decisions

None recorded.

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

- Staff browser (browser): External staff browser — authenticated workflow channel generated; no browser infrastructure to provision; tools, To be selected.
- Invoice intake and review (invoice): Composed invoice API/worker/parser, durable SQL queue, private originals, review authorization, guarded accounting delivery and operating tasks generated; destination behavior remains unverified; gcp, australia-southeast1.
- Existing accounting service (accounting): Existing service reference — preserve without provisioning/import; actual connection acceptance required; tools, To be selected.

## How to use this kit

Read contracts.md and tasks.md. Use tasks.json for machine-readable dependencies and acceptance checks. Keep progress.json as the implementation journal. Start by reporting the next actionable task and the most consequential unknown. Refine this plan into repository-specific code/file changes once the repository and runtime are known; do not pretend those details were provided.

## Traceability

Requirements retain their own IDs and statements in context.json. Task links reference those IDs and the original component/edge IDs. Keep source requirements distinct from implementation decisions. Record changes in decision-log.md and reconcile substantive scope changes with the user.

## Invoice delivery phases

Read invoice-delivery.md and the concrete TASK-INVOICE-* dependencies. The emitted
source supplies runtime, parser, queue, identities and operating jobs. Validate it
locally, then separately authorize state/account planning, foundation, image
publication, SQL/staff bootstrap, schedule/alert acceptance and application release.
Do not ask the user to invent already supplied commands or clear scope gates.
