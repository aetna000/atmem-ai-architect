# Native-first Build intake implementation checkpoint

346 server tests and 375 JavaScript tests pass with no skips. Production build and
real Chromium fixture checks pass; desktop/mobile screens are retained. This is an
implementation checkpoint, not alpha.1, an accepted original project or quality score.
Actual native generation on this new UI/source remains a separate qualification.

## Reusable behavior and invariants

With engineering enabled and Codex selected, Build is the primary workspace. One
Start action saves the current project, creates a session with exact model/effort,
and submits the complete request to that session. A save failure retains the draft
and creates/starts no native work. Opening, typing and navigating do not infer intent
to start work. Existing sessions keep their pinned selection. A new build waits for
pending design work rather than snapshotting a concurrently changing design.

The conversation renders complete ordered requests and streamed model replies,
separately from tool-progress and acceptance. Saved requests survive journal/store
restart; legacy accepted events recover text only from their exact owned durable run
ID. Unknown or foreign history is never invented. Steering without a delivery
acknowledgement remains visibly uncertain. Drafts persist per project, view switches
and reload observe existing jobs/artifacts/checks without replaying work.

Design views remain available, including their existing graph, conversation, voice,
attachments and review controls. Build pauses legacy queued inference/auto-coaching
and voice preparation, preserves queued intent and prevents hidden canvas shortcuts
from editing the design. Native output and the saved design are still separate review
surfaces; automatic shared work-model/canvas reconciliation belongs to GE-003.
Disabling engineering retains the original Design path. No browser CLI, path, native
handle, command, image or credential selector is introduced.

Transfer/counterexamples: sensor/measurement intent with existing-system preservation,
long complete request history, actual primary-view navigation/reload/drafts, save
failure before any native request, uncertain steering, exact foreign-run rejection,
legacy queued intent without background planner calls, unavailable/skipped/zero/stale
checks, and desktop/mobile overflow. Fixture model/download data are explicit; those
are not real generation or complete-system evidence.

The small reviewed corpus adds one dated model/API/region/feature intersection record
from the pinned primary Nova Lite card, with account/quality/retention/quota/price
limits. It is model-specific evidence, not a default model choice or cloud-generic
feature claim. Provider/freshness/complete-record negatives pass. Raw source HTML stays
in the local review cache; this is not an account lookup or new customer requirement.
Existing records and requirements are unchanged.

## Reproducible local preview

`scripts/engineering-preview.py --help` describes explicit app data, ports, tool roots,
registered validators, reviewed isolation profiles and owned Unix daemon configuration.
It does not install tools/images, inspect cloud accounts or deploy. Vite cache is
instance-local, so frozen evaluation worktrees can reuse installed packages while
isolating model observations from ongoing development HMR.

For this machine the already prepared operator files are in
.local/engineering-preview/operator-toolchain.json, operator-validators.json and
operator-isolation-profiles.json. They contain paths/registrations, not credentials.
Use an explicit owned validator Unix endpoint. Local CLI remains a development
backend transport, not a requirement for a future hosted app's browser clients.

Next: real fresh UI/native architecture generation and ordered follow-ups on a
frozen instance, then generic final-artifact applicability/check/repair supervision.
Keep full requirement/system acceptance independent of model completion and authored
tests. The 28-project baseline and ten accepted releases remain at zero.
