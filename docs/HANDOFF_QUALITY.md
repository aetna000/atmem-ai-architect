# Engineering handoff review — 2026-11-07

This change improves generated handoffs across projects. It does not implement a deployable enterprise assistant or expand native Terraform coverage beyond the existing S3 foundation.

## Repeated review cycles

1. Source review and reproductions: an explicit Lambda service labelled “S3 migration processor” generated S3; generic OpenSearch silently selected Serverless; seven accepted design ADRs were missing from implementation context; accepted country suppressed the region question. Corrected resolution, decision preservation and independent placement questions, with regression tests.
2. Export review across providers and integration graphs: added shared readiness assessment, linked engineering gaps, service-specific component guidance and architect feedback. Split local integration tests from live tests, added early security/cost/static tasks, and introduced explicit account planning and staging prerequisites. Added evidence boundaries, placement contradictions, cost/security findings and shared-application mapping checks. Condensed repeated App Runner eligibility findings into one decision.
3. Browser and provider checks: verified readiness navigation, generated ZIP contents and snapshot identity. The browser test exposed mobile grid overflow; changed the flexible grid track to allow shrinking without hiding content. Terraform's repeated provider download exhausted available disk; reran successfully with the already downloaded official provider. The test runner now strips cloud/CLI environment overrides and cleans temporary provider binaries, retaining small fixtures and locks.

The final matrix includes 13 synthetic scenarios (empty, S3, explicit Lambda with misleading label, ambiguous service, three search modes, shared application, knowledge base, three non-AWS providers and cyclic RAG), plus an external handoff regression. Each undergoes export invariants and reordered-input identity checks. Results: [handoff-review-results.json](handoff-review-results.json). No customer artifact is copied into this repository.

## What now reaches an engineer

- `spec-kit/readiness.md` and `.json`: prioritised gaps with task/component/requirement references, next action and separate evidence stages.
- All accepted decisions, including design ADRs, without treating their proposed regions/services as approved deployment choices.
- Specific engineering work for S3, Lambda, search modes, Bedrock, guardrails/knowledge bases, App Runner, ECS, DynamoDB, SQS, CloudWatch and external systems. Other providers retain explicit service-selection work rather than borrowed AWS implementation.
- Stable resource/connection gap identifiers, requirement traceability gaps, shared deployment-unit questions and current reviewed App Runner eligibility guidance.
- An executable dependency graph: scope → local foundation/design/cost → implementation/mocks → account plan → cost reconciliation → authorized staging → live integration/acceptance/recovery → separately approved release.
- The same high-priority findings in architect context and the Outputs view.

## Validation

- `npm test`: 131 passed, including nine new handoff-quality regression tests.
- `npm run test:server`: 53 passed; local integration/fixture tests, not cloud deployment.
- `node scripts/handoff-check.mjs <external-project>`: 14 scenarios × two invariant passes; no mutation, dangling task references, dependency cycles, or reordered identity drift.
- `scripts/terraform-check.mjs` with `.venv/bin/terraform`: schema validation and three mock-plan scenarios passed using hashicorp/aws 6.72.0. No real AWS plan or apply. The earlier disk-space failure was not counted as a pass.
- `npm run test:browser`: full suite passed (dictation fixtures, isolated real AtMem journey with model/quote fixtures, delivery/export/readiness/mobile scenarios).
- `npm run build`: passed; existing upstream `use client` and large-bundle warnings remain.
- `git diff --check`: clean.

## Remaining product work

Native generation is still S3-only. Full workload modules, deployable application artifacts, typed deployment-unit configuration, complete current service/model/price coverage, and ingestion of signed or otherwise verifiable implementation receipts require further features. The report deliberately cannot claim those are complete. Live model interview quality and actual customer cloud permissions, quotas, latency, residency and recovery were not evaluated by deterministic fixture tests.

A production-grade handoff needs customer decisions and implementation evidence as well as a better generator. Next expansion should choose one supported deployable reference architecture, define its typed inputs and ownership boundaries, implement its complete infrastructure/application modules, and validate in an explicitly authorized staging account before marking that capability deployable.
