# Interactive consultation validation — 2026-11-05

Requirements now use a concise working summary and conversational clarification. The former editing form has been removed. Existing canvas structure, right-click menus, comments and block interactions remain. Estimate worksheet inputs are optional and collapsed.

Verified locally:

- `npm test`: 96 passing tests for project/model/diagram/estimate/delivery behavior, selective requirements and price provenance.
- `npm run test:server`: 39 passing tests, including genuine AtMem 2.3.10 persistence, supersession, scope isolation, outage replay/idempotence, forgetting history, opt-out, bounded tools, hash-checked skills and authenticated routes.
- `npm run test:browser`: isolated browser journey over actual HTTP routes and AtMem storage, followed by deterministic delivery export scenarios. Model responses and numeric quotes are fixtures. Covers empty start, idea-to-diagram, right-click comments/live response, no requirement form, answer-driven requirement changes, four-cloud comparisons and decisions, conversational usage, dashboard/history/profile, forget preview/cancel/confirm, opt-out, save/reset/reopen, delivery ZIP regeneration, undo/redo and mobile overflow.
- `npm run build`: succeeds; existing React Flow module-directive and large-bundle advisories remain.

A separate native Claude account request failed because the account had reached its session limit. It does not establish live model behavior or memory-assisted quality. No cloud was deployed. Automated prices cover selected AWS/Azure storage rates; GCP needs catalog API access and IBM needs a sourced quote. A complete cloud bill still requires model, compute, networking and other service charges.

Screenshots of the tested fixture journey are under `docs/screenshots/`. These are local synthetic designs, not user project data.
