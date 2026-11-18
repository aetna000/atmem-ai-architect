# Implementation plan

## Current owner-directed product path

Embed the existing review engine in AtMem AI Architect, with real project memory
for approved policies/results and the current Review/engineering UI for actions.
Keep CLI/MCP as interoperable worker adapters. Preserve existing generation,
requirements, documents, design and receipt validation; do not replace them with
a separate checking application.

Deliver and qualify in dependency order:

1. Real Codex Specify -> Plan -> Tasks execution, proving automatic MCP review,
   fail-without-tasks and pass-with-tasks outcomes on an owned synthetic project.
2. Exact approved policy snapshots and results in AtMem, with project isolation,
   audit identity, stale revision rejection and no approximate-policy recall.
3. Native Review controls, live activity, Code it gating, and backend enforcement
   against the saved design/policy binding. Package the engine with Architect.
4. Graphical implementation/evidence views using existing engineering events and
   authenticated artifact mappings; no invented percentages or test passes.
5. Specification/task/file/test binding in both directions, persistent invalidation,
   agent-worktree reconciliation, and evidence-backed chat status. Extend the
   existing architecture-work contracts rather than introducing a second project.
6. Actual browser/backend/memory tests, generation/installed-package regressions,
   source-bound manual card and a clear list of unqualified scalability/providers.

The initial standalone candidate plan below records earlier implementation scope.

Base: origin/main 7601a8e. Worktree: architect-review-hook; branch feat/architecture-review-hook. Infrastructure upgrades from PR #11 are consolidated into PR #13; actual R3 remote acceptance remains a separate gate.

Build the reviewer as a small independently installable Python package under the supplied folder, using existing pinned jsonschema, PyYAML and MCP dependencies. Keep the original PLAN.md as supplied evidence. Reuse Architect's backend-neutral contract and verification discipline, not its stateful generation pipeline: a review must not create project memory, run provider binaries or execute source hooks.

Implement bounded policy parsing, effective Terraform desired-state traversal and evidence-first checks; cost/model adapters are explicit operator opt-ins. Model output is advisory evidence validated independently and cannot clear deterministic violations or unknown infrastructure facts. A supplied plan snapshot is not proof of deployment, account state or actual uptime.

Test positive, negative and unknown cases, child modules/aliases, destroys, computed values, malformed/hostile rules, exceptions, budget currency/coverage and prompt injection. Exercise actual stdio initialization/tools/call via the installed SDK. Test CLI/CI artifact binding and install both workflow adapters into disposable local projects. Record exact versions and distinguish fake cost/model adapters from live vendor evidence.

Package a local candidate and create a reviewable PR. Do not tag/publish/deploy or submit public catalog messages without the owner's publication instruction.

## PR #11 / #13 reconciliation

Keep PR #13 as the single combined review. Merge the infrastructure-upgrades history without rewriting either branch. Preserve R1/R2 local migration and module/consumer workflows, R3 default-closed GitHub publication, native rules/AtMem/Spec Kit bindings, packaging and independent evidence boundaries. PR #11 becomes superseded once its head is an ancestor of the pushed combined branch.

Resolve both context contracts together: original project bytes remain authoritative, while general-model handoff/task snapshots exclude private maintenance source. Retain explicit original and projected context hashes. Never relabel an older policy receipt as current. Keep the original R2 receipt and re-run the offline campaign on the reconciled source; record it separately in evidence/reconciled-campaign.json.

Qualification includes complete JavaScript/server suites, hosted process checks, real offline single/multi-repository browsers, fake-GitHub publication browser, native rules browser and a clean installed candidate containing both features. Actual GitHub customer-repository acceptance, semantic requirement conformance, R4 scheduling and publication/deployment remain outside this reconciliation.
