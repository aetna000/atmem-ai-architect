# Validation — 2026-11-13

- `npm run build`: passed; standard existing large-chunk warning remains.
- `npm test`: 585 tests passed, including accepted placement and deduplicated AWS region actions.
- Full server suite using the existing qualified developer interpreter: 520 tests completed, 508 passed and 12 optional/platform tests skipped. This includes real AtMem 2.3.14 memory tests. A fresh minimal uv developer environment lacked optional emulation dependencies and could not run two macOS interpreter-copy tests; those failures are environment-dependent and are retained in local logs, not represented as passes there.
- Focused public pricing tests: six passed. Real Google public HTML verified Iowa’s Standard single-region storage hourly rate. Returned quote retains source SHA, hourly unit, 730-hour planning conversion and excluded charges; GB/GiB conversion remains in the client provenance.
- `node scripts/checklist-smoke.mjs`: real Chromium passed pending feedback, disabled duplicate actions, pointer/wait cursors, checklist destinations and StarPrompt link/dismissal/snooze.
- Live isolated candidate at http://127.0.0.1:5306: actual public Google storage quote applied; selected us-central1 reused; checklist region navigation reached the focused input in under three seconds; zero page errors.
- Actual managed runtime HTTP response: AtMem 2.3.14 core SDK, ready. Installation used hash-locked AtMem 2.3.14 and AtFlows 0.1.8.
- A synthetic SQLite store created through the original 2.3.10 worker was read through 2.3.14 with its record and identity preserved. No user database was migrated by this test.
- Six locked runtime distributions’ actual wheel legal files regenerated; pip is not part of this uv-managed distributed memory runtime.
- Original installed Orca integration: actual npm 0.2.0 startup, browser tab, saved-project API, complete ZIP, authenticated handoff, real CLI registration and real spec opening passed. Plugin release 0.1.0 is separate from this maintenance source and still pins published Architect 0.2.0.

Screenshots: checklist-opening.png, star-prompt.png, iowa-storage-live.png. Synthetic projects and public prices only. No cloud plan/deployment or paid model generation is established. This source candidate is not an npm release.
