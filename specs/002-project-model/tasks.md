# Tasks: Project model and project file

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/project-file.schema.json](contracts/project-file.schema.json)

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

- [x] T001 [P] Records module: requirement, assumption, open question constructors and sanitisers in `src/records.mjs`
- [x] T002 [P] Decision revision and history (`reviseDecision`, `currentDecision`, `decisionHistory`) in `src/records.mjs`
- [x] T003 Extend `cleanEngagement` / `keepEngagement` for `needs`, `assumptions`, `openQuestions`, `extensions`, and decision `subject` / `supersedes` / `supersededBy` / `reason` in `src/engagement.mjs`

## Phase 2: User Story 1 — Save and reopen (P1) 🎯 MVP

- [x] T004 [P] [US1] Tests: round-trip for every template, v1 migration, newer-major refusal, unknown-field preservation, size limits, credential refusal in `tests/project-file.test.mjs`
- [x] T005 [US1] `toProjectFile`, `fromProjectFile`, `migrate`, `findCredentials` in `src/project-file.mjs`
- [x] T006 [US1] Menu: "Save project file" / "Open project file" use the new format; notify when a file was upgraded, in `src/main.jsx`

## Phase 3: User Story 2 — Requirements, assumptions, open questions (P1)

- [x] T007 [P] [US2] Tests for sanitisers, link flags and measure validation in `tests/records.test.mjs`
- [x] T008 [US2] `RequirementsView` (requirements, assumptions, open questions) in `src/EngagementViews.jsx`; Design sub-view "Requirements" in `src/main.jsx`
- [x] T009 [US2] Block detail lists linked requirements and assumptions in `src/main.jsx`
- [x] T010 [US2] Read-only `context` in `src/local-agent.mjs`, `server/contracts.py`, `server/architect.py`; contract test in `server/tests/test_boundary.py`

## Phase 4: User Story 3 — Decisions keep their history (P2)

- [x] T011 [P] [US3] Tests: three-step revision chain, reason required, single current decision per subject in `tests/records.test.mjs`
- [x] T012 [US3] Decisions view: subject field, "Revise" with reason, superseded history collapsed under the current decision, in `src/EngagementViews.jsx`

## Phase 5: User Story 4 — Agent and canvas share one model (P2)

- [x] T013 [US4] `keepEngagement` keeps new records on proposals and templates (covered by T003); regression test in `tests/maintenance.test.mjs`

## Phase 6: Polish

- [x] T014 Browser smoke: add requirement + assumption, revise a decision, save file, clear storage, open file, verify in `scripts/smoke.mjs`
- [x] T015 Client pack prints requirements, assumptions, open questions and decision history in `src/pack.mjs` (bridge until 005)
- [x] T016 Update README and `specs/README.md` status
