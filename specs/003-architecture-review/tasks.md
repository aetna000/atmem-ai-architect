# Tasks: Architecture review

## Done (release-1 slice)

- [x] T001 Deterministic, provider-neutral rules v1.0.0 in `src/review.mjs`: SEC-001 GenAI path without guardrail (blocker), SEC-002 sensitive data without residency, SEC-003 automated actions without approval, REL-001 no model monitoring, REL-002 existing-system failure behaviour, AVL-001, PRF-001, SCL-001, MNT-001 unmeasurable NFRs, MNT-002 unowned decisions, CST-001 no budget, DSN-001 sketch-only blocks
- [x] T002 Findings carry rule id + version, attribute, severity, rationale, action, components, source, status; recomputed on every change (FR-002, FR-005)
- [x] T003 Accept risk with reason and owner, persisted by rule + components (US1 scenario 3)
- [x] T004 Review view grouped by quality attribute; component chips open the block; "Add target" creates a measurable requirement (US2)
- [x] T005 Tests in `tests/journey.test.mjs`; browser smoke Review section

## Remaining

- [ ] T006 Evaluate measurable requirements against inputs (met / at risk / not met / unknown) (FR-004)
- [ ] T007 Trade-off findings with options and consequences (US3)
- [ ] T008 Provider-specific rules with document sources, gated by OD-1 (FR-006)
- [ ] T009 Agent-generated findings labelled and confirmable
