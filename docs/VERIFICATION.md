# Consulting delivery verification — 2026-11-05

- `npm test`: 91 passing tests, including ROM/detailed-charge replacement, split token pricing, mixed-currency refusal, missing and stale inputs, incomplete totals kept distinct from zero, consulting ranges, resource ownership, stable Terraform addresses, snapshot manifests, credential refusal and project 2.2 round trips.
- `npm run test:server`: 24 passing tests. No boundary/schema change; estimate and infrastructure summaries use existing read-only discovery/question context types. The architect prompt now explains the staged estimate and handoff.
- `npm run test:browser`: existing full journey plus `scripts/delivery-smoke.mjs`. Tested chat/drawing, four-cloud proposals and decisions, review and acceptance records, ROM → detailed charges, separate consulting cost, mixed currencies, AWS resource coverage, actual ZIP downloads and content, revised estimates in regenerated packs, undo/redo/branching edits, cancellation of reset, save-before-reset, re-open and mobile without horizontal overflow. Model sessions and prices in browser tests are synthetic; no live model request or provider price is claimed.
- Desktop delivery and mobile estimate screenshots were inspected. Extra charge and consulting forms are collapsed until requested. Unused shared usage fields are hidden; deployment review status is distinguished from incomplete implementation.
- `npm run build`: passes. Existing React Flow directive and bundle-size advisories remain non-fatal.
- `npm run test:terraform`: generated native S3 foundations validated with Terraform 1.17.1 and hashicorp/aws 6.72.0. Mock AWS provider tests cover refusal before approval, a reviewed standalone S3 foundation plan and refusal of an unfinished application even after approval. No cloud plan against a real provider and no apply.
- Terraform CLI downloaded from releases.hashicorp.com into a temporary QA directory and checked against the published SHA256. No new application dependency was added.
- The delivery pack carries a unique snapshot ID, design revision, timestamp, editable project, specification, diagram, architecture/deployment document, decisions, estimate JSON, resource schedule, handoff and Terraform sketch. Exports are generated from current data; changes to non-diagram inputs are identified by a new snapshot even when design revision stays the same.
- Current implementation coverage: proposed explicit AWS S3 buckets and associated public-access, encryption and versioning resources. Other services, existing-resource integration, application code, IAM and every drawn connection remain enumerated engineering work. The review gate blocks incomplete sketches. Cloud deployment and live pricing are not connected.

## Previous milestone

# Local integration verification — 2026-11-01

- `npm test`: 26 passing tests, covering five fixture patterns, graph failures, import boundaries, upstream catalogue/templates/parsers/layout/formatter, proposal revisions, Pulumi metadata handling and request projection.
- `npm run test:server`: 16 passing tests, including Host/Origin/token boundaries, credential memory handling, strict proposals, upstream retry behaviour, and local CLI adapter command construction.
- `node scripts/smoke.mjs`: browser checks pass for connected runs, failure propagation and payloads, Google Cloud proposals, tool insertion/failure, local persistence, architecture imports, upstream templates, front-panel indicators/scenario controls, run cancellation, JSON plans, Pulumi scaffold download/snapshot import, connection disclosures, mobile layout, and zero external browser requests during the zero-key smoke flow.
- A scoped axe check of the initial desktop workspace reports no WCAG A/AA violations after correcting contrast. This is not a complete accessibility certification of every dialog and state.
- `npm run build`: passes. React Flow's ignored `use client` directive and a bundle-size advisory are non-fatal build messages.
- `npm audit`: zero reported Node vulnerabilities at verification time. `pip check`: no broken Python requirements. These are not a complete security audit or a Python vulnerability scan.
- Claude Opus 5.5: design consultation completed through the official installed client; exact model confirmed in its returned usage metadata. The resulting brief is in `CLAUDE_5_5_DESIGN_REVIEW.md`.
- Live account requests: Claude Code (`claude-opus-5-5`) and Codex (`default`) returned valid architecture responses. Copilot reached a model but initially rejected an optional-field response schema; the adapter was changed to strict required fields and a live Copilot SDK response then passed the shared response model.
- Verified client versions: Claude Code 2.1.281, Codex CLI 0.166.0, Copilot CLI 1.0.103 (SDK 1.0.28), Gemini CLI 0.46.0.
- Gemini CLI transport starts but reports an authentication requirement on this workstation. It needs the user's official `gemini` sign-in before live use; no successful Gemini account request is claimed.
- Direct API adapters are constructor/import and boundary-tested, not live-tested with private API keys. No customer API keys were supplied or used.
- No cloud workload calls, AWS Labs MCP execution, live pricing, Pulumi CLI command, infrastructure deployment, atmem.ai change or new hosted publication was performed.

The local browser server is intended to remain running for the user's review. The earlier private Sites preview is an older milestone and was not updated by this integration.
