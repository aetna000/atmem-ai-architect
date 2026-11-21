# Generic engineering jobs checkpoint — 2026-11-11

This is runnable Release 1 implementation work, not an accepted alpha release or
measured quality improvement. The original independently accepted project count
remains **0/28**; all ten release subgoals remain unaccepted.

## Reusable capability and contracts

`server/engineering_jobs.py` supervises backend-neutral project sessions independently
of an HTTP request. A browser disconnect cannot cancel the reservation/acknowledgement
transition. Progress is committed to a project-scoped journal and replayed with an
opaque sequence cursor. Quiet native observation windows continue watching. Duplicate
starts are rejected; uncertain starts are reconciled through native message identity,
never replayed. A new turn reconnects an idle backend before reserving intent.

Steering intent is journaled completely before delivery with a native client message
UUID. Browser disconnects do not cancel delivery. A lost acknowledgement remains
explicitly uncertain; the saved update is not automatically resent. Native acknowledgement
does not prove the requirement has been implemented. Interruption remains a request
until a matching terminal event arrives. Events lost before journal commit are a
disclosed recovery gap, not reconstructed as an invented transcript.

`server/engineering_artifacts.py` captures arbitrary files without executing them.
It rejects symlinks, hardlinks, special files, unsafe names, changing files and explicit
byte/entry limits without saving a partial package. Immutable ZIP bytes and file digests
are stored outside the model workspace. Capture checks server-pinned project evidence
and reviewed skill digests. Worker caches and tooling are excluded explicitly in the
manifest. Completion/capture never establishes independent validation.

The HTTP adapter resolves scope from a saved, non-binned local project; clients cannot
supply tenants, native handles, host paths, commands or tool roots. Every endpoint uses
the existing loopback host/origin/Bearer boundary. The local owner authorization adapter,
SQLite store, artifact storage and subprocess transport must be replaced/qualified for
hosted operation. No browser CLI or model credentials are required. Browser draft keys
are project-bound; unsent updates survive closing/reloading and are cleared only after
acknowledgement. A failed update retains its full draft.

The server operator may register read-only local code/tool directories and exact tools
using `ENGINEERING_TOOL_ROOTS` and `ENGINEERING_TOOLCHAIN` settings. Tool paths must fall
under registered roots; native effective-policy verification still runs before use.
The model sees `.tools/toolchain.json`, not server configuration/credentials. No whole
project recipe or scenario identifier selects the engine's output language.

## Evidence and counterexamples

- `live-api-probe.py`, `live-api-receipt.json`, `live-events.json` and
  `live-generated-package.zip`: actual in-process ASGI HTTP requests through the new
  job service to signed-in `gpt-6.1-sol` / `high`, generating a non-cloud measurement
  library with local tests. A separately authored 15-case behavioral oracle passed
  under the qualified native command policy. Package bytes match the capture/download
  digest. Worker/store restart recovered the same public session with one accepted
  request; progress was durably replayed. This transfers outside the AWS ticket brief.
- The live process loaded before the final steering journal, pinned-input guard and
  tool-registration additions. Separate tests cover those changes; this receipt alone
  does not establish acceptance of the final source. An independent post-capture check
  confirms that the live package retained its original project and skill digests.
- `before-probe-thread-fix-*`: retained failed probe. Model work completed, but the
  probe read SQLite on the test client's wrong thread before independent verification.
  The corrected probe uses the ASGI portal; no SQLite thread safeguards were weakened.
- `live-ui-receipt.json`, `live-ui-ready.png`: actual browser, real loopback service,
  project save, native session/policy/tool registration and reopening the same job.
  No inference turn was submitted in this smoke test. The unsent draft survives reload.
- `live-browser-work/`: actual browser-to-native CommonJS inventory-library generation
  on unchanged source, with a new batch-processing demand delivered during the turn.
  Closing/reloading retained one original start and one acknowledged steering update.
  The package passed pinned-input capture and the browser digest check. A separate
  oracle on the downloaded immutable code passed **15 behavioral checks** under the
  same native sandbox, without source repair or a second inference turn. Source
  hashes, request/update, journal events, ZIP, manifest, screenshot and separate live
  and independent receipts are retained. This is integrated product evidence on a
  non-cloud domain, not acceptance of a ticket/cloud system.
- `browser-results.json`, desktop/mobile screenshots: real Playwright interactions
  against explicit fixture backend/model responses; exact selection, start once,
  failed/successful steering, retained unsent draft, reload recovery/progress replay,
  capture boundary and digest-verified download. These are not live model tests.
- Server regressions include wrong tenant/project, duplicate start, uncertain delivery,
  cancellation during acknowledgement, quiet workers, reconnect failure before
  reservation, foreign instruction inheritance, dead cached native transports,
  unsafe/oversized artifact entries and missing/changed pinned inputs.
- `full-js-tests.log`: 374 tests, no skips. `full-server-tests.log` records the full
  current server suite (**309 passed, no skips**). `operator-tools-tests.log`, `focused-server-tests.log` and
  `artifact-guard-tests.log` retain focused checks; `build.log` records the production
  build. Existing Vite bundle-size warnings remain.

## Frozen comparison observation

The corrected pair at `.local/engine-paired/20261111-verified-arm-pair` finished with
identical client input, model/effort, local tools and 900-second budgets, using its
frozen source rather than this later product implementation. The native arm completed
31 files in 848.79 seconds; the native-plus-composition-skill arm was interrupted at
900.154 seconds with 28 files. `*-comparison.json` and `paired-manifest.json` retain
the exact hashes/status. Both partial and complete artifacts remain unchanged.

Offline replay uses copied artifacts and recreated trusted tools, not source repairs:
`scripts/engine-evaluation/replay-local.py`. No inference is used. Both outputs pass
Terraform format, mirror-only init and provider-schema validation. Native's generated
18 Python tests and eight Node tests pass. Specialized's 13 Python tests and seven Node
tests pass, but **one HTTP test class is skipped because the worker denies loopback
binding**. Its Python check is marked incomplete, not passed, despite exit code zero.
The original replay log retains the command exit interpretation; `*-replay/receipt.json`
explicitly separates exit success from skipped coverage.

These are generated unit/synthetic transport checks, not independent whole-system
acceptance. Native also reports its real HTTP smoke blocked. The pair does not include
live AtMem retrieval or the new UI, public documentation access, genuinely unseen
holdouts or independent semantic/system checks. Shared-host load and a single ordered
pair cannot establish a latency advantage. No specialized quality/speed advantage is
supported. Do not accept either project or tune scenario recipes from this observation.

## Local manual test card

The running preview is `http://127.0.0.1:5274` (sidecar `127.0.0.1:8866`), with its own
local project/control data under `.local/engineering-preview`. It is an implementation
checkpoint, not a released/tagged candidate. `live-ui-receipt.json` records its actual
smoke check. Other existing local app processes are left in place.

1. Select an explicit Codex model and reasoning level in Connections.
2. Open **Engineering**, then **Open engineering job**. The current project is saved
   before the server freezes its project evidence and reviewed composition skill.
3. Describe a small non-cloud module or implementation. Observe progress; add updates
   while it runs. A failed request retains the draft. Stop requests remain pending
   until observed. Closing the dialog/browser does not resubmit the original work.
4. Reopen Engineering to recover the existing job, inspect the complete progress log,
   and capture/download its package after the turn settles. A partial/interrupted
   package stays labeled accordingly. Download verifies both receipt and response hashes.
5. Run independent local checks before treating a package as accepted. The UI does not
   project arbitrary generated source onto the existing graph or waive its existing gates.

To reproduce startup use the existing `npm run local`, with server settings
`ATMEM_ARCHITECT_ENABLE_ENGINEERING=1`, `ATMEM_ARCHITECT_PORT=5274`,
`ATMEM_ARCHITECT_SIDECAR_PORT=8866`, `ATMEM_ARCHITECT_HOME` set to separate control data,
and operator-reviewed JSON values for `ATMEM_ARCHITECT_ENGINEERING_TOOL_ROOTS` and
`ATMEM_ARCHITECT_ENGINEERING_TOOLCHAIN`. The running preview's non-secret resolved
registrations are recorded in `.local/engineering-preview/operator-toolchain.json`.
Native CLI 0.167.1 and its beta named-profile behavior were qualified on this macOS
host; other operating systems and hosted workers need independent qualification.

Rollback: stop this preview's launcher, unset `ENABLE_ENGINEERING`, and run the prior
checkpoint `aade0a5` in a separate checkout if needed. Preserve control DBs and artifact
receipts; do not delete user projects or rewrite generated evidence.

## Next required work

Independently assess the emitted ticket packages and their block/connection/user
journeys. Add a controlled backend validator/emulator path that can exercise actual
local HTTP/service composition without granting the model host networking or Docker
access. Extend real browser/native qualification to Terraform and knowledge
retrieval; freeze genuine holdouts. Only then assess
Release 1 against its complete manual/automated gates. No cloud deployment is required.
