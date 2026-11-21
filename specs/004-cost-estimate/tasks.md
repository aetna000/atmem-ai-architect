# Tasks: Cost estimate

## Done (release-1 slice)

- [x] T001 Drivers per component role/kind with units and formulas in `src/estimate.mjs` (FR-002)
- [x] T002 Usage inputs with provenance: entered, discovery fact (dated), or stated assumption (FR-001)
- [x] T003 Unit prices only as entered, each with source and date; missing input or price → line excluded and estimate incomplete (FR-003, FR-005); mixed currencies refused
- [x] T004 Low / expected / high with explicit, editable factors; top three drivers; budget comparison in the same currency (FR-004, US2)
- [x] T005 Estimate view; estimate in the project file (2.1.0) and in the deployment document (FR-006)
- [x] T006 Tests in `tests/journey.test.mjs`; browser smoke Estimate section

## Remaining

- [ ] T007 Saved what-if scenarios (US2)
- [ ] T008 Price-book import from file; provider page retrieval with URL and date when connected (US3)
- [ ] T009 Price review date at 90 days
- [ ] T010 Default price book for the first validated provider (OD-1)
