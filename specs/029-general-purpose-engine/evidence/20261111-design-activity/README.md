# Design-first and public architecture activity — alpha.2.1 patch

Owner instruction: Design starts the journey; Build is its implementation outcome.
Show inspectable agent turns while Architecting. This patch adds a public activity
timeline with observed context/skill selection, exact model/effort and attempts,
validated public replies, real host tool/cache statuses, format repairs and response
readiness. Private reasoning, raw prompts and rejected protocol output are excluded.

Design opens on startup/project selection/reload even with stale Build preferences.
An empty design cannot start a new build. Build this design binds the current saved
context; additional instructions are optional, existing jobs remain recoverable and
blank follow-up updates cannot submit duplicate build intents. Queued restored
requests remain paused. Opening Design does not prepare voice or submit inference.

## Validation

- `npm test`:408 JavaScript tests,0 failures/skips (`js-tests.log`).
- `npm run test:server`:423 server tests,0 failures/skips (`server-tests.log`).
- `npm run build`:pass; existing large-chunk advisory retained (`build.log`).
- `node scripts/architecture-activity-check.mjs`:actual browser/UI/storage with
  explicit fixture session/model, intermediate timeline visible before final reply,
  reload/history/no replay, exact selection, direct Design-to-Build starts once,
  empty-design gate and desktop/mobile. `activity-browser.json` and screenshots.
- `node scripts/engineering-browser-check.mjs`:full context/save failure/retained
  draft/recovery/artifact/check/download regression under the new Design entry point.
  `engineering-browser.json`.
- `node scripts/architecture-work-check.mjs`:shared-work invalidation/export/artifact
  linking/ownership/no replay regression with explicit Build navigation.
  `work-browser.json`.
- New backend tests exercise the real bounded host loop and AtMemArchitect response
  validation with a deterministic native adapter:format repair, three actual adapter
  calls across two host passes, project.read and validated public messages. Duplicate
  identity stops inference; cross-project reads fail; pagination preserves all events;
  restart marks unfinished activity unknown; observer failure does not replay or
  suppress a successful response. These are local mocked-adapter tests, not live
  model inference or architecture/runtime acceptance.

Initial browser fixture failed because it assumed activity could not be polled before
submission. The UI correctly polls then handles404 before the turn is reserved. The
fixture now explicitly models that race; failed output is retained under `.local/`
and excluded from passes.

## Boundaries and handoff

Activity references travel in the project file; details stay in the owning service's
SQLite store. Older services remain compatible but cannot reveal unrecorded details.
Service restart never replays uncertain work. Current host authorization is local
session/project scope; hosted tenant authorization remains a separate requirement.
This patch adds no roadmap increment or complete-system acceptance:2/10 runnable
increments before this patch,1/28 originals locally qualified,0 owner acceptances,
95% quality unproven. GE-004 composition remains next.

The runnable record will bind the frozen source, new local preview, exact startup
command and observed checks. Keep alpha.2 at5283 and alpha.1.1 at5280 unchanged for
rollback. The shared5282 development service and its unrelated project stay intact.
No cloud account, deployment or remote publication is involved.
