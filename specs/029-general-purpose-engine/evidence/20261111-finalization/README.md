# Completed-turn local verification checkpoint

361 server tests and 375 JavaScript tests pass without skips. Production build and
desktop/mobile browser fixture pass. Six actual isolated-runtime probes pass their
expected outcomes. This is an implementation checkpoint; 0/10 releases and 0/28
original projects are accepted. Bounded model repair is not implemented here.

## Reusable capability

An operator may register `applicability` alongside an existing validator, containing
nonempty `anyOf` and optional `allOf`/`noneOf` lists of relative POSIX file globs.
`*` stays within one path segment; whole-segment `**` spans zero or more segments.
Only regular files in the immutable manifest count. Rules have bounded counts and
length, reject traversal/absolute/ambiguous patterns, and cannot specify executable
commands. No project ID, business domain or cloud inference selects a check.

`POST /api/engineering/validation/plan` accepts the existing scoped artifact request.
It does not execute. Its digest-bound result retains every operator decision as
selected, not_applicable, unavailable or manual_only. Missing rules remain manual
only; existing explicit starts remain available. Rules are part of the validator
contract hash; historical manual-only hashes retain compatibility. File eligibility
does not establish runtime compatibility, test discovery or requirement coverage.
Tests that discover zero cases still fail in the existing runtime adapter.

After verified native completion (including exact-history reconciliation), the job
supervisor synchronously captures settled files with original pinned inputs before
another local intent can start. It records a durable finalization and schedules
registered applicable checks on those bytes. Failed capture does not hide native
completion. Check/report failure, skips, no available applicable check, or changed
operator contracts retain needs_attention. Only current, available, digest/contract-
bound passed receipts produce local_checks_passed. That status is explicitly not
independent requirement or whole-system acceptance. New user work supersedes old
finalization evidence. Interrupted/failed turns do not trigger automatic capture.

`POST /api/engineering/finalizations` reads owned history. Restart/cancellation leaves
checking work recovery_required; there is no implicit model/check replay, recapture,
new-worker cleanup or automatic pass. Existing check recovery/manual capture remain
available. Finalization-level retry/reconciliation and bounded model repair are
pending. The UI observes saved verification updates and automatically discovers
their packages. Recorded updates are labeled as recorded evidence; later manual
checks or operator definitions can differ. Native output and the saved graph still
have separate review surfaces.

## Evidence and transfer

`runtime/receipt.json` records exact implementation/worker/policy hashes and operator
registrations; each case retains source ZIP/manifest, plan, check reports and events.
Rainfall Python tests and a museum notice exercised through actual loopback HTTP
and Chromium select different appropriate runtimes. Deliberate assertion failure,
matching empty suite, skipped test, and no matching tests all remain needs_attention.
The lifecycle is an explicit fixture; execution uses actual cached immutable Linux
images and the previously reviewed browser policy with Chromium sandbox requested.
No native inference, downloads, cloud operations, hosted isolation, client-system
or 28-case acceptance is claimed by these probes. Earlier development attempts
remain in `.local/engine-product/finalization-runtime*`; confirmed evidence uses
the `-verified` runtime source hashes. Server tests include foreign-owner rejection,
lost terminal history reconciliation, original-worker restart debt, new-intent
supersession and changed operator policy while a check runs.

The actual uncoached primary Build architecture run is separately observing frozen
commit 3b80eb4 on ports5275/8867 with gpt-6.1-sol/high and the original exposed AWS
brief plus three natural updates. It has no new finalizer code, and is neither a
holdout nor a comparison with the earlier shorter runs. Its output remains unaccepted.

## Manual review / rollback

Start the local preview using `scripts/engineering-preview.py` and explicit existing
operator tool/runtime registrations. Add reviewed file applicability to copies of
the operator validators, for example `{"anyOf":["test_*.py"]}` for root discovery
or `{"anyOf":["**/*.test.mjs"]}` for Node discovery. Complete a fresh native task;
inspect its automatic package, exact check reports, recorded update and reload
continuity. Start another request while a check runs and verify the old package
does not cover it. Repeat with a deliberate failing/empty suite and retain failures.
No auto model repair is offered by this checkpoint. Use the generic runtime probe's
`--help` for reproducible controller tests on already cached reviewed images.

Rollback: stop only this owned preview, retain its data/evidence, and run an isolated
worktree at 3b80eb4 with separate app data. New tables are additive; do not delete
the original journals or artifacts. No version/tag or accepted candidate is created.
