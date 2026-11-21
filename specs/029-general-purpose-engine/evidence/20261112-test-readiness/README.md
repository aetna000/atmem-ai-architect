# Test readiness and explicit implementation action

User reported that Test attempted work before code existed and then left “Build” unexplained. The shared readiness function now identifies known missing compiler implementation/connections before the request. The hook blocks manual and automatic emulation requests in that state, while the entry action opens the panel with the implementation step. Readiness is not stored as an executed report or pass. Supported designs continue to execute the existing checker; runtime failures remain visible.

The panel names code generation explicitly, offers “Implement and test this design”, and uses the existing project-bound native implementation/test request. If that implementation service is unavailable in the session, it says so and offers an actual downloadable repair task. That fallback does not implement the application or qualify its tests. No promise that arbitrary generation will succeed. No cloud operations.

Applicability: missing application code or unimplemented connections across domains/providers; no project names or email dispatch. Existing access/identity corrective mentoring is preserved. This is a partial flow repair: actual provider/model availability, runtime capabilities, material choices, generation failure/recovery and full end-to-end journeys need continued qualification. No new release increment or original-project pass.

Validation: 555 JS tests pass, production build passes (existing large-bundle warning). Browser fixture uses the actual React components/hook and synthetic projects, with test endpoint intercepted: missing-code run invokes zero requests; implementation invokes its callback once; unavailable-service task downloads; supported design sends one request and displays returned checks. Both current source and live frozen preview modules pass. This does not prove native generation succeeds or exercise the private owner project.

Reproduce against a running Vite preview: `node scripts/engine-evaluation/check-test-readiness.mjs http://localhost:5285`. The fixture intercepts only its synthetic page and test request; no owner page/storage/project writes or inference.

Activated only frontend guidance/hook/panel/entry imports at http://localhost:5285 with explicit cache invalidation for frozen sources. No CSS or backend restart. Refresh to load. Rollback: restore five files from `.local/external-artifacts/test-readiness/v1/before`, then refresh with a new entry import URL. Prior proposal-title fix remains in the live main file.

The first source browser fixture used a named CommonJS ReactDOM export incorrectly; fixed fixture imports. First live fixture loaded a different prebundle React instance and failed hooks; fixture now resolves the preview's actual React runtime. These fixture failures did not change application behavior.
