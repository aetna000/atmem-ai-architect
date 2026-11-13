# Generation lifecycle validation — 2026-11-13

- Root cause: EngineeringPanel reported only its HTTP action busy flag; a running backend session was ignored after the request returned.
- Real Chromium, synthetic transports: restore a running session, receive fileChange progress, verify both Run buttons remain disabled beyond the polling interval; transition the job to idle and verify both enable. Prerequisite titles remain accessible and action families stay isolated.
- `node scripts/project-checks-smoke.mjs`: passed.
- `npm test`: 585 passed. `npm run build`: passed (existing chunk-size advisory). No backend changes.
- Existing local user job observed read-only: idle/completed, 302 journal entries and 53 workspace files. No restart/resubmission. Finalization reported verification incomplete/failed; the visible status now says “Files generated · Checks need attention”. Completion does not prove application acceptance.
- Frontend build updates candidate5306; refresh to receive it. Maintenance PR5 remains separate from the published npm0.2.0.
