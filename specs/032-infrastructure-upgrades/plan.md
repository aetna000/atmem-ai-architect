# Implementation Plan: Infrastructure upgrade maintenance

**Date**: 2026-11-16 | **Branch**: spec/infrastructure-upgrade-maintenance | **Spec**: spec.md
**Status**: Design proposal. See releases.md for gated increments; no implementation authorized in this planning turn.

## Summary

Build a persistent migration project inside Architect. Separate repository inventory, reviewed recipes, model-generated patches, independent verification and remote publication behind explicit contracts. Existing generation exports are inputs/evidence, never overwritten customer fixtures. New reusable mechanisms must demonstrate another composition and a failure case.

## Technical context

Reuse Python 3.11+ FastAPI sidecar contracts and React19/Vite workspace. New core under `server/maintenance/`; pure UI state under `src/maintenance/`. Strict versioned records; local SQLite implementation and storage protocol; hosted adapter qualifies separately. No new dependency selected without license/security and notices review. Parse HCL with a real structured parser selected in T001; the website's lightweight diagram extractor is neither a compiler nor a dependency authority.

Initial provider: Terraform AWS. Resolve exact baseline/target pairs from current official schemas and upgrade guides during R0; never treat all major versions as supported. Provider executables are untrusted and run only in isolated bounded workers. No execution with operator cloud or Git credentials. R3 uses a customer-owned fine-grained GitHub token stored in an OS keychain and bounded polling; no vendor App key or inbound webhook exists locally. Repository tests require explicit execution permission and a reviewed command/network profile; local copies alone are not a sandbox.

Reference qualification scope: one migration recipe, shared module + two consumers + unrelated repo, a structurally different holdout, blocked/error fixtures and 30-repository discovery scale. No rollout date promised before measured effort.

## Constitution check (before and after design)

CONSTITUTION.md is read as the owner-established governing engineering standard; `.specify/memory/constitution.md` retains required I–VIII checks. Owner's explicit request now authorizes local development of this adjacent maintenance workflow; no silent amendment of either file.

I control: isolated proposals; exact diff approval for remote publication; no deployment. II honesty: pinned official sources, qualified costs and evidence. III one model: versioned MigrationProject references snapshots, decisions, patches and receipts; export/import required. IV local/least privilege: local-first core and scoped adapters; hosted runner is a later proposal requiring compatibility review of the older local-only wording. V depth: AWS recipe first, matrix expansion only with evidence. VI memory: events/supersession/private isolation. VII UI: existing canvas with concise maintenance overlay and expandable evidence, 20-word explanations, keyboard/mobile WCAG2.2AA. VIII tests: independently executable oracles plus unit/contracts/browser and all existing required gates.

Generic-engine instruction: review already exists under029; T001 rechecks integration boundaries and records conflicts before specialized implementation. This is a new owner-directed workstream, not a claim that 029's generality/28-project programme is finished. Remote recurring fleet service remains gated until local-first/hosted governance alignment is explicitly resolved before hosted R4. Complexity: no additional general framework or rewrite; reuse existing workers only after their actual isolation contracts are qualified for hostile customer repositories.

## Proposed source structure

- `server/maintenance/models.py`, `store.py`: strict records, transactional leases, import/export.
- `inventory.py`, `graph.py`: immutable checkout/allowlisted paths, AST references and uncertainty.
- `recipes.py`, `catalog/`: signed/digest-pinned reviewed recipe applicability and primary-source receipts.
- `planner.py`, `patches.py`: backend-neutral patch drafting, path/semantic scope controls.
- `verification.py`, `workers.py`: baseline/control/candidate runners, receipts and repair bounds.
- `publication.py`, `github_adapter.py`: write-ahead intent, confirmation, reconciliation, scoped credentials.
- `scheduler.py`, `budget.py`: opt-in repeat matching and durable budget admission.
- `server/maintenance_routes.py`: sidecar contract; remote server adapter separate from core.
- `src/maintenance/{model.mjs,MaintenancePanel.jsx}`: concise migration views; integrate `src/main.jsx` only after locating its actual workflow boundary.
- `tests/maintenance/`, `server/tests/test_maintenance_*.py`, `scripts/maintenance-smoke.mjs`: qualification and regression.

Names are proposed deliverables, not claims these files exist. Existing `server/engineering_jobs.py`, `server/local_validation.py`, `server/terraform_routes.py` and hosted workers are integration candidates, not automatically trusted/reused security primitives.

## Execution flow and evidence

Snapshot -> explicit graph -> applicable recipe -> approved compute budget -> baseline/control checks -> proposed patches -> candidate checks/repair -> exact diff review -> coordinated PR operations -> observation/reconciliation -> later source updates invalidate/recompute. Unsupported input may produce inventory but never ready status. Recipe changes invalidate applicability and candidate evidence.

Version-only control must demonstrate the break being fixed, independently of the patch author. Oracle cases freeze before repair tuning; record exposure. Test-definition changes are reviewed separately; cannot erase a baseline failure or weaken accepted assertions. Checks run without apply/import/state mutation; remote module/network fetches are allowlisted and pinned, never arbitrary URL execution. Full cloud plans/runtime tests are optional future evidence classes, requiring separately approved credentials and scope.

## Delivery dependencies

R0 qualifies real breaking recipes and security boundaries. R1 delivers a complete local single-repo migration. R2 adds multi-repo module/consumer correctness. R3 adds explicitly confirmed GitHub publication and recovery. R4 adds recurring fleet preparation and qualified hosted scheduling. Each gate reruns earlier invariants and packages a stable candidate with reproducible fixtures, evidence, owner test card, limits and rollback. See tasks.md for task-level dependencies.

## Validation and measurement

Independent expected graphs, version-only failures, separate candidate checks, mutation/counterexamples, changed-head/recipe/oracle invalidation, hostile repositories, credential egress, tenant crossover, remote failure reconciliation, and actual authorized disposable GitHub acceptance. Record worker/tool/model/effort/cost identities. No mutation of public artifacts or customer repositories during qualification. Performance goals from spec are gates; hardware/data and observed timings must accompany any result.
