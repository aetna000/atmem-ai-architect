# Generic intake, recovery, evaluation and worker checkpoint

2026-11-11, Australia/Sydney. GE-001A and GE-002 remain in progress. No release,
measured quality percentage, full project acceptance or cloud deployment is claimed.

## Reusable changes

- The consultation policy covers software systems, including non-AI work, and no
  longer simultaneously demands a question after every short answer.
- A bare dollar symbol retains unknown currency. Explicit currency codes/symbols
  remain distinct; country does not silently choose the currency.
- Oversized and excess-file saved updates block without crashing or discarding
  text/references. The browser shows the issue and can return the update to the
  draft without overwriting another draft. Explicit edits persist without replay.
- A missing native thread may be replaced only when the control store proves the
  public session has never accepted a run. Public session identity is preserved.
- Every native start carries the durable run UUID as client message identity.
  Recovery matches that identity in bounded history; it never resubmits intent or
  infers acceptance from similar text. Missing/ambiguous evidence remains uncertain.
- The optional native worker uses a versioned, named permission profile. It denies
  host reads except minimal runtime/explicit trusted code roots, keeps writes within
  the project and permits private Unix IPC only beneath its short temp directory.
  An active deny-all network proxy is necessary to propagate that IPC allowance;
  the profile's `network.enabled=true` is **not** an unrestricted egress grant.
- Worker startup verifies effective filesystem, shell, network and external-tool
  configuration. Existing MCP declarations are explicitly disabled; disabled rows
  may still appear in the native status API and must expose no tools/resources.
  Original shell override values are never copied; known overrides are blanked.
  The generic backend identity binds this policy, preventing a legacy-policy fallback.

Applicability: arbitrary project intent and engineering work. No production change
uses benchmark IDs, expected answers, a business-family selector or a new scenario
recipe. Transfer/counterexamples include three unrelated budget contexts, a generic
reservation workspace, queued updates with conflicting resource bounds, wrong-scope
or ambiguous message identities and hostile read/network/configuration attempts.

## Executed evidence

- `intake-tests.log`: **32 JavaScript checks passed** (intake/discovery/consultation).
- `server-tests.log`: **75 focused local checks passed** (protocol/coordinator/adapter/worker
  policy/independent aggregator/abstraction). These are component tests, not 28 cases.
- `browser-results.json`, `browser.log`, `intake-*.png`: real browser/persistence tests
  pass for oversized and five-file saved updates, protected unsent drafts, explicit
  edit/send, retained originals and reload without replay. Model/session are fixtures.
  The first failed browser probe used an invalid revision-0 fixture and is retained
  as `browser-invalid-fixture.log`; the corrected fixture uses the actual project contract.
- `empty-session-receipt.json`: actual native worker/store restart without inference;
  an unused, unsaved native thread is replaced while the public session remains stable.
  This is not continuation of the same native thread. The earlier legacy probe's
  misleading continuity wording is retained only as an **unqualified** raw receipt.
- `lost-start-receipt.json`: one actual native file/tool turn, its start acknowledgement
  deliberately withheld, worker/store restart, and recovery by exact client UUID.
  **One start request; zero work replay.** Default native adapter, not hosted isolation.
- `sandbox-receipt.json`: three actual legacy `command/exec` write/network checks.
- `read-profile-receipt.json`: twelve actual named-profile checks pass, including positive
  file/temp work; sibling and symlink read denial; sibling write denial; loopback and
  reserved raw-IP denial; foreign Unix-socket and Unix-symlink escape denial; real cached AWS provider init/schema validation; one native
  provider mock plan; and effective external-tool disablement. No cloud account used.
- Full regression: **370 JavaScript tests and 281 server tests passed**, no skips. These are repository regressions, not complete-project acceptance.
- Production build passed. Existing Vite dependency-directive and bundle-size warnings
  remain; they are not runtime/quality acceptance.

The named-profile probe uses explicit trusted code directories and synthetic canaries.
This establishes the recorded local command boundary on the installed native CLI,
not complete model-tool parity, hosted OS/tenant isolation, arbitrary tool safety,
cloud behavior or correctness of a generated application. Control databases must stay
outside model-writable workspaces. Native profile support is beta and fails closed.

## Evaluation protocol and live comparison

`benchmarks/engine/evaluation-contract.json` freezes an engineering measurement
protocol around the owner's 95% target: 28 original cases; all critical checks per
project; noncritical reporting within each provider/difficulty stratum; exact artifact
and evidence bindings; and identical model/effort/tool/budget conditions for pairs.
It is not a new customer SLA, a measured score or a waiver of independent review.

`scripts/engine-evaluation/assess.py` imports no generator and verifies receipt coverage,
levels and hashes. It does not itself execute or certify the semantic verifiers.
Its counterexamples reject skipped/missing/mocked runtime claims, modified artifacts,
escaped/symlinked evidence and duplicate identities. Applied to the historical original
baseline, it reports **0/28 qualified**, all required independent acceptance records
missing. This is a new assessment of prior artifacts, not 28 new executed projects.

Initial 300-second pair: `.local/engine-paired/20261111-first-same-model/`.
Both arms timed out with partial files (10/12). They inherited source-repository
instructions and lacked peer-read isolation. This is a retained diagnostic, **not a
clean native baseline** and not evidence of a quality advantage. The initially recorded
source hashes were restored exactly after later recovery edits; the reconstruction
method and hash checks are recorded there. No input/output or recorded hash was changed.

The next isolated run, `.local/engine-paired/20261111-isolated-same-model/`,
corrected the source/permission setup but exposed a driver bug: a tool-directory loop
shadowed the arm name with `Frameworks`, preventing specialization. The native arm
reached its 900-second limit with 27 partial files. The operator stopped the exact
frozen runner, retained the native artifact and seven partial files from the other
workspace, and recorded `qualification-limits.json`. This run also cannot support a
comparison. No result was accepted or rewritten to manufacture a pass.

The driver now has a differential regression and final assertions for exact arm labels,
identical input/model/effort, native skill absence and specialized skill presence/hash.
Cancellation preserves partial artifacts and cannot start another arm. A new corrected
run is active under `.local/engine-paired/20261111-verified-arm-pair/`, with
`gpt-6.1-sol`, effort `high`, the same brief and 900-second execution budget per arm.
It re-executes immutable source, uses unrelated short temporary workspaces and the
read-restricted worker, rejects inherited external instructions, and records live
protocol events. The only specialization is the reviewed general composition skill;
this is not the full AtMem retrieval/product path. Check result files before reporting
completion and independently assess outputs before counting a project. This is one
shared-development-host diagnostic pair, not a statistical latency comparison.

Unseen-family holdouts and the complete final 28-case repair/evaluation remain open.
Visible original scenarios and internal diagnostics are not blinded holdouts. Broader
knowledge, service availability, cost and whole-system emulation remain explicit work.

## Reproduction and next action

From repository root:

```sh
node --test tests/work-intake.test.mjs tests/journey.test.mjs tests/consultation.test.mjs tests/consultation-context.test.mjs
.venv/bin/python -m unittest server.tests.test_codex_app_server server.tests.test_engineering_sessions server.tests.test_codex_engineering_backend server.tests.test_codex_worker_policy server.tests.test_engine_evaluation server.tests.test_abstraction -v
node scripts/engine-intake-browser-check.mjs
.venv/bin/python specs/029-general-purpose-engine/evidence/20261111-engine-intake-recovery/read-profile-probe.py
```

The empty-session and lost-start probes are alongside the read-profile probe; only
lost-start invokes a model. Archive existing receipts before reruns. No probe pass
clears a project acceptance gate or releases alpha.1.

Next: inspect the frozen isolated pair and independently check its emitted files;
complete model-tool and local validator integration; then expose project-bound
engineering jobs, durable progress/steering and exact artifact capture through the
backend and UI. Preserve the current recipe implementations as regressions while
building the general engineering path. Continue the ten dependency-ordered releases
and original 28 plus unfamiliar combinations; do not resume specialized expansion.

[Official native permission-profile reference](https://learn.chatgpt.com/docs/permissions)
explains profile, command-network and separate tool controls. Actual local receipts,
not the documentation alone, support this checkpoint's enforcement observations.
