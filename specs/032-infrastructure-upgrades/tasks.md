# Tasks: infrastructure upgrade maintenance

Development is authorized. `progress.json` records current execution and evidence; checkboxes mark only fully accepted task deliverables. Dependencies remain explicit.

## Phase 1 — R0 setup/research

- [x] T001 Inspect existing engine/worker integration and select pinned HCL/parser/Terraform/provider/schema/upgrade-guide contracts in `specs/032-infrastructure-upgrades/research.md`; measure blocked executable-construct coverage; deliver exact supported schema-removal/type-error migration matrix (deprecation warnings are not failing controls), local R3 identity/polling contract and R4 governance conflict record before code.
- [x] T002 Freeze a real breaking-upgrade baseline, version-only failure, independently specified candidate oracle, distinct-composition holdout and unsupported, forbidden CI/source/data-source/provisioner, secret egress and module-release/range-drift cases in `tests/maintenance/fixtures/` and `specs/032-infrastructure-upgrades/evidence/qualification.json` (T001).

## Phase 2 — R0/R1 foundations

- [x] T003 Implement isolated tool/network/credential/resource profiles in `server/maintenance/workers.py` and `server/tests/test_maintenance_isolation.py`; deliver per-OS isolation matrix and prove hostile provider/test cannot read host secrets or escape; unqualified OS execution blocked (T001).
- [x] T004 Implement strict versioned records, SQLite transactions/fencing, tenant scoping, existing project-format maintenance-section migration and permission-free export/import in `server/maintenance/models.py`, `store.py` and `server/tests/test_maintenance_store.py` (T001).

## Phase 3 — US1 / R1 local migration

Goal: meaningful checked single-root patch, original unchanged. Independent test: frozen baseline/control/candidate and counterexample.

- [x] T005 [US1] Implement immutable allowlisted source snapshots and AST inventory with unknown references in `server/maintenance/inventory.py` and `server/tests/test_maintenance_inventory.py` (T002,T004).
- [x] T006 [US1] Implement reviewed recipe applicability/digests and bounded backend-neutral patch authoring, independent patch safety and confirmed secret-filtered source-selection/derived-request model egress in `server/maintenance/recipes.py`, `catalog/`, `planner.py`, `patches.py` and `server/tests/test_maintenance_recipes.py` (T002,T004,T005).
- [x] T007 [US1] Implement baseline/control/candidate independent receipts,3-attempt repair budgets and atomic tenant/project/credential-owner spend reservations and stale-input invalidation in `server/maintenance/verification.py`, `budget.py` and `server/tests/test_maintenance_verification.py` (T003,T006).
- [x] T008 [US1] Implement local routes, concise accessible panel and export/import in `server/maintenance_routes.py`, `src/maintenance/model.mjs`, `MaintenancePanel.jsx`, `tests/maintenance/model.test.mjs` and `scripts/maintenance-smoke.mjs` (T007).
- [x] T009 [US1] Run clean baseline/holdout/hostile/cancel qualification, all existing gates and owner test card; publish exact support/evidence in `specs/032-infrastructure-upgrades/evidence/r1.json` and `quickstart.md` (T008).

## Phase 4 — US2 / R2 coordinated migrations

Goal: module+consumer migration with an executable compatible order. Independent test: module, two consumers, unrelated repo and different composition.

- [x] T010 [US2] Implement explicit dependency graph/private-module unknowns/aliases/constraints/cycle detection in `server/maintenance/graph.py` and `server/tests/test_maintenance_graph.py` (T005,T009).
- [x] T011 [US2] Implement digest-bound candidate module overlays, actual-release mapping, module_release_pending/observation/equality/consumer-reverification states, per-wave authorization and compatible merge sequence in `server/maintenance/planner.py`, `patches.py` and `server/tests/test_maintenance_campaign.py` (T007,T010).
- [x] T012 [US2] Add graph/campaign review, simulated local operator release with tag-mismatch/range-drift denials and independent 30-snapshot affected-set/scale/partial-merge tests in `src/maintenance/MaintenancePanel.jsx`, `tests/maintenance/`, `scripts/maintenance-smoke.mjs` and `specs/032-infrastructure-upgrades/evidence/r2.json` (T011).

## Phase 5 — US3 / R3 repository delivery

Goal: explicit exact-patch confirmation produces real coordinated PRs without duplicate or unauthorized writes.

- [x] T013 [US3] Implement selected-repository customer-token OS-keychain broker/read scopes/bounded polling and token revocation, per-owner scopes, proposal-ref allowlist and keychain-unavailable denial and remote snapshot adapter in `server/maintenance/github_adapter.py` and `server/tests/test_maintenance_github.py` (T004,T012).
- [x] T014 [US3] Implement preview/expiring confirmation/write-ahead intent/fenced reconciliation and human-edit stop, CI/unknown-automation per-action disclosure and real released-module observation in `server/maintenance/publication.py`, `server/maintenance_routes.py` and `server/tests/test_maintenance_publication.py` (T013).
- [x] T015 [US3] Implement campaign publication/status/partial-merge workflow in `src/maintenance/MaintenancePanel.jsx`, `tests/maintenance/model.test.mjs` and `scripts/maintenance-smoke.mjs` (T014).
- [ ] T016 [US3] Obtain separate explicit disposable-repository write authorization, run real network/timeout/revocation/protection/human-commit/default-branch-denial-on-unprotected-repo/conditional-ref-race/cross-install-campaign-conflict/module-release-wave qualification and retain sanitized evidence in `scripts/maintenance-github-acceptance.py` and `specs/032-infrastructure-upgrades/evidence/r3.json` (T015).

## Phase 6 — US4 / R4 recurring service

Goal: bounded recurring preparation independent of customer activity, no automatic PR confirmation.

- [ ] T017 [US4] Implement egress_confirmation_required on source changes, opt-in schedules/cursors/holds/recipe-withdrawal/dedup/spend reservation/recovery in `server/maintenance/scheduler.py`, `budget.py` and `server/tests/test_maintenance_scheduler.py` (T016).
- [ ] T018 [US4] Resolve hosted/local governance alignment explicitly, then implement tenant-qualified storage/worker/broker/signed-webhook/retention adapters in `hosted/maintenance.py`, `hosted/tests/test_maintenance.py` and `specs/032-infrastructure-upgrades/decision-log.md` (T003,T004,T017).
- [ ] T019 [US4] Qualify two-tenant isolation,30-repository load/replay/cancellation/deletion/backup expiry and actual cost bounds in `hosted/tests/test_maintenance.py`, `scripts/maintenance-smoke.mjs` and `specs/032-infrastructure-upgrades/evidence/r4.json` (T018).

## Final phase — release packaging (repeat per increment)

- [ ] T020 Re-run applicable current/prior acceptance, installed-platform/build/notice/security checks; supply owner artifact/manual card/rollback and update `specs/032-infrastructure-upgrades/progress.json`, `releases.md`, package notes and README before separately authorized stable publication (T009 for R1; T012 for R2; T016 for R3; T019 for R4).

## Dependencies and parallel opportunities

R0 T001 -> T002,T003,T004; T003 and T004 can run independently after contracts agree. US1 T005–T009 -> US2 T010–T012 -> US3 T013–T016 -> US4 T017–T019. No child-agent parallel work is required; paths overlap in later stories. Within a story, independent fixture/oracle review may occur alongside implementation but cannot be written solely by the patch author or consume its expected answer. T020 repeats at each release gate rather than waiting until R4.

MVP is US1/R1 after all R0 gates. Do not implement the recurring cloud service first. Each later story adds a complete independently demonstrable outcome on prior released foundations.
