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
