# Project-scoped validation jobs and visible evidence — 2026-11-11

This checkpoint connects the isolated local executor to immutable artifacts, durable
project jobs and the Engineering UI. It is reusable validation infrastructure, not an
accepted release, a measured quality increase or acceptance of any original project.
Original independent acceptance remains **0/28**; all ten release subgoals remain open.

## Capability, interface and evidence boundaries

`server/validation_jobs.py` supervises checks independently of HTTP lifetime and native
generation. The server operator registers a validator ID/label, cached immutable image,
explicit executable/arguments, platform and time budget. Browser requests supply only
authorized project/session/artifact IDs and a registered validator ID. They cannot
select images, commands, host paths, daemons or credentials. Artifact ownership and
stored byte digest are verified before starting work.

Each durable receipt binds artifact SHA-256, registered validator specification,
executor policy hash and worker identity. Duplicate requests reuse an existing job;
retrying a finished job requires an explicit request. A changed check definition or
policy gets a different contract digest and preserves old evidence as historical.
Queued/running work on supervisor restart becomes `recovery_required`; it is not
inferred stopped, passed or replayed. Cleanup must be confirmed against the original
local worker. A different worker is refused. Failed cleanup stays uncertain. Shutdown
signals bounded cancellation and waits for worker cleanup before closing the store.

The first durable adapter is single-supervisor SQLite. Hosted workers need explicit
transactional ownership/leases and separately qualified tenant isolation. The worker
interface remains separate from project authorization. No deployment, cloud account
access, registry pull/build/push or global Docker context changes are required.

Project POST routes cover validator catalog, start/list/get/recover and captured
artifact discovery. Existing loopback host/origin/Bearer and saved-project checks apply.
No raw command endpoint is exposed. Missing local Docker access leaves generation
available and checks unavailable; it does not imply a pass or trigger a network fallback.

The UI restores captured packages and check history after reopening. Results apply to
the exact captured bytes. An older native turn's package is marked as not covering the
current work; older check definitions are marked historical. Skipped checks stay
incomplete and zero-test results stay failed/incomplete. Users can explicitly retry,
recover a check and save its digest-bound report. Passing local generated tests does
not establish full project acceptance. Existing graph/compiler gates are preserved.

## Validation observed

- `full-server-tests.log`: **323 passed**, no skips. Includes job ownership across
  tenants/projects, immutable bytes, deduplicated starts, explicit retry, contract
  changes, restart/worker-identity/uncertain-cleanup behavior, cancellation, mismatched
  receipts and strict server-only registration. Route tests reject browser commands,
  images, endpoints and non-boolean retry values; failures do not expose diagnostics.
- `full-js-tests.log`: **374 passed**, no skips. `build.log`: production build passed;
  existing Vite bundle-size/directive warnings remain.
- `browser-results.json` and screenshots: actual Playwright UI against explicit fixture
  service/model responses. Covers original native job lifecycle, restored packages,
  validation observation across reload without resubmission, skipped/zero-test status,
  historical definitions, explicit retry, recovery without replay and report downloads.
  `before-locator-fix-browser.log` retains a test-only ambiguous locator failure:
  the running label appeared both on a disabled button and its result row.
- `controller-probes/`: six actual isolated-container policy/counterexample probes on
  the current executor. Private HTTP succeeds; host/external networking, source writes,
  raw sockets, host mounts/socket/environment access remain denied. Timeout, skipped
  evidence, zero tests, output overflow and traversal remain failed/incomplete.
  Earlier checkpoint evidence was restored after rerun output initially targeted its
  old default folder; new receipts are retained here and the probe now accepts an
  explicit evidence directory.
- `runtime-recovery-receipt.json`: two real named containers were observed running.
  Cancelling one removed only that job while the peer stayed running. Recovery then
  removed the exact peer without replay. Repeated recovery confirmed absence. The
  pre-existing local qualification containers were left in place.

## Real browser/native/artifact/check workflow

`live-workflow/` contains actual output from `gpt-6.1-sol` / `high` on an independent
non-cloud audit-line summary module. The browser used real authenticated API routes,
native file/tool work, immutable pinned-input capture and digest-verified download.
The newly connected job service executed the generated package in the cached isolated
Linux Python 3.13.18 runtime: **12 tests passed, zero skips**. Closing/reloading restored
the same package and receipt without submitting another check. A downloaded JSON report
binds artifact/contract digests. Desktop/mobile layouts were inspected.

`before-hmr-recovery-*` retains the interrupted first observation: running the build
rewrote generated runtime bundles and Vite refreshed the browser, closing its dialog.
The native job continued and completed exactly once. The corrected observer resumed
that existing native run and finished capture/check/report actions; no generation was
replayed. The receipt records this resumption rather than claiming a new inference.
The selected integration source hashes stayed unchanged during the resumed workflow.

`independent-library-check.py` and `live-workflow/independent-*` provide **15 separately
authored behavioral checks** on the downloaded immutable module: exact counts, Unicode,
empty/whitespace lines, maximum limits, rejected types/oversize and input preservation.
No source was repaired and no inference was used for these checks.

`inspect-native-skill.py` reads the completed owned native turn through the native
read-only history API. Its narrow receipt confirms one accepted native run, exact
model/effort, and a successful tool command whose output contains the complete pinned
composition skill. Only hashes, status and item counts are retained; no raw native
handle, commands, tool contents or credentials are copied into evidence. Actual skill
reading is proven; architecture quality is not inferred from invocation.

The module workflow is an integration/transfer test with an explicit function contract,
not an uncoached architecture quality result or a full cloud application. It does not
prove Python 3.12 managed SDK compatibility, identity/provider/service connections,
regional data guarantees, original ticket-system acceptance or hosted SaaS isolation.

## Manual test / configuration / rollback

Running implementation preview: `http://127.0.0.1:5274`, sidecar port 8866, separate local
data in `.local/engineering-preview`. Select an explicit model/effort, open Engineering,
generate files, capture a settled package and choose a registered package check. Close
and reopen: the artifact and check report remain. Review output and save the report.
Run again only when an explicit retry is intended. Recover any uncertain prior job
before starting another check for that package. No release/tag is offered yet.

Operator settings add `ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_ENDPOINT` (the existing
owned local Unix daemon) and `ATMEM_ARCHITECT_ENGINEERING_VALIDATORS` (JSON list of
reviewed registrations) to the previous local startup settings. The preview's nonsecret
registration is in `.local/engineering-preview/operator-validators.json`. The model
does not receive this configuration or the Docker socket. The current registration is
root-level Python unittest discovery; other test layouts/runtimes require appropriate
reviewed contracts and remain visibly unsupported/incomplete rather than silently skipped.

Rollback: stop this preview's launcher, remove the optional validator registration and
run checkpoint `ac8895b` from a separate checkout. Preserve project databases, artifact
bytes and evidence. Older code does not erase the added validation tables or receipts.

Next: qualify an uncoached complete architecture brief through the current native UI,
including generated Terraform and application connections; integrate relevant reviewed
knowledge and automated validation/repair ownership. Complete every Release 1 gate
before tagging/handing over its local candidate. Do not turn evaluation cases into
production recipes or require cloud deployment for the local programme.
