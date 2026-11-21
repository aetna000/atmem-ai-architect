# Generation lifecycle validation — 2026-11-13

- Root cause: EngineeringPanel reported only its HTTP action busy flag; a running backend session was ignored after the request returned.
- Real Chromium, synthetic transports: restore a running session, receive fileChange progress, verify both Run buttons remain disabled beyond the polling interval; transition the job to idle and verify both enable. Prerequisite titles remain accessible and action families stay isolated.
- `node scripts/project-checks-smoke.mjs`: passed.
- `npm test`: 585 passed. `npm run build`: passed (existing chunk-size advisory). No backend changes.
- Existing local user job observed read-only: idle/completed, 302 journal entries and 53 workspace files. No restart/resubmission. Finalization reported verification incomplete/failed; the visible status now says “Files generated · Checks need attention”. Completion does not prove application acceptance.
- Frontend build updates candidate5306; refresh to receive it. Maintenance PR5 remains separate from the published npm0.2.0.

## Live progress and previous snapshots

Owner follow-up: while a new run edits files, the card was showing the preceding captured package and telling the user to regenerate. Label it Previous snapshot and state that new files are being generated; file-link status also waits for the current run. Repair is only available for the current completed snapshot.

Add an animated, indeterminate progress bar during running/recovery, with the actual latest activity as its accessible value text. No percentage is invented; backend work has no known total. Reduced-motion users get a static indicator. The bar disappears on completion. Chromium verifies its role, activity, animation and completion lifecycle alongside the previous-snapshot message. Build and focused browser test passed.
