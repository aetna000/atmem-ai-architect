# Native engineering session and restart recovery

Local checkpoint, 2026-11-11 Australia/Sydney. Programme task GE-002 remains in progress.

Reusable capability: project-bound, backend-neutral durable session/turn lifecycle with
an exact Codex adapter configuration, bounded turn-history reconciliation and explicit
uncertain outcomes. It applies to arbitrary engineering intent and workspaces; no
production dispatch depends on the reservation example, domain or benchmark case.
The reservation domain below is a small unfamiliar file/tool-work transfer probe,
not an evaluation-matrix implementation or an engine-quality score.

## Findings and repairs

1. The interrupted probe attempted restart before any native turn. Codex 0.167.1
   returned `-32600`, with the diagnostic `no rollout found for thread id ...`.
   A returned empty thread ID alone does not establish durable history. The original
   `native-probe.py` is retained as the known-failing diagnostic, not a passing check.
2. After a real engineering turn, the thread could be resumed, but dropping resume
   configuration overrides failed the exact model/effort/workspace acknowledgement.
   The adapter now reasserts the selected reasoning effort and execution policy on
   resume, then verifies the response. It does not weaken the checks or fall back.
   `native-engineering-before-fix.log` preserves that actual rejection. The initial
   successful two-turn receipt/log are retained separately.
3. Completion notifications are not a durable control-plane acknowledgement. A turn
   completed while the coordinator disconnected could leave its stored state running.
   Resume now queries metadata-only turn history for the exact owned turn and records
   completed, failed or interrupted state transactionally. An active turn stays active.
   Missing, malformed, cyclic or over-limit history remains uncertain; no intent is
   replayed to repair it.
4. The inherited transport's event waiter is qualified for timeout, cancellation and
   closure; SQLite reservations preserve intent across restart and prevent duplicate
   starts after lost acknowledgements.

## Actual checks

From the repository root:

```sh
.venv/bin/python -m unittest server.tests.test_codex_app_server server.tests.test_engineering_sessions server.tests.test_codex_engineering_backend -v
.venv/bin/python specs/029-general-purpose-engine/evidence/20261111-portable-sessions/native-engineering-probe.py
.venv/bin/python specs/029-general-purpose-engine/evidence/20261111-portable-sessions/verify-native-artifacts.py
```

The second command uses the signed-in native CLI and performs two model turns. It
uses synthetic data and a temporary project workspace; no cloud services or deployment
credentials are involved. It overwrites the latest probe receipt/log if rerun. Archive
existing evidence before a new qualification run. The third command is entirely local,
verifies captured file hashes, runs the captured generated suite and a separate oracle.

- `unit-tests.log`: **39 local tests passed**, including protocol doubles, coordinator
  restart/recovery, exact adapter policy rejection and pagination/error counterexamples.
- `native-engineering-receipt.json` and `native-engineering.log`: **passed** on installed
  Codex 0.167.1 with `gpt-6.1-sol`, effort `high`. First turn generated reservation code
  and tests using actual file/shell tools. The probe deliberately bypassed coordinator
  terminal handling, leaving its stored state running; it restarted worker/store,
  reconciled native history to completed, then extended the same files in a second turn.
- `independent-artifact-check.json`: exact captured file digests verified; **9 generated
  tests and 16 independently authored behavioral checks passed** in a fresh local folder.
- `source-manifest.json`: SHA-256 identities of the checkpoint's source and probe files,
  interpreter/CLI versions and commands. This is a source/evidence identity record,
  not a signed release or deployed-system receipt.

## Limits and next work

No release or quality percentage is established. There is no public/browser engineering
endpoint yet. Project registration and authenticated scope must come from a trusted
control plane, and the control database must be outside model-writable workspaces.
Native sandbox acknowledgements and rejection tests are not an independent hostile
workspace/tool isolation qualification or hosted tenant-isolation proof. The remote
worker test uses a protocol double, not deployed infrastructure.

Fresh empty native threads remain nonresumable after worker loss; this must be handled
before release 1. A start whose acknowledgement is lost remains durably `starting`, with
its intent retained and automatic resubmission blocked; automatic start reconciliation
is not implemented. History search is bounded to 20 pages of at most 100 turns and
loads no message content. Active work is not assumed to survive process termination.
Resume can establish terminal status from history; it does not establish successful
application validation, Terraform correctness, tool-output capture or deployment.

Next GE-002 work: empty-session lifecycle, uncertain-start reconciliation, independent
workspace/tool isolation, reviewed-skill execution and artifact/evidence integration,
then streamed UI/steering. GE-001A's paired same-model baseline and independent
Terraform/block/connection/system emulation remain required before alpha.1.
