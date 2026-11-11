# Explicit root state custody

GE-005 checkpoint; no new release or original full-project qualification. Three
runnable increments,1/28 full local originals, zero owner acceptances and unknown
overall quality remain the current programme counts.

`before.json` records the256727b counterexample: an unrelated HTTP state destination,
backend password and TLS bypass could be injected at the composition root without
a fatal finding. `after.json` records rejection of the equivalent mutation.
Neither probe contacted the synthetic destination.

The reusable mechanism now carries an explicit, versioned state choice in
`project.extensions.terraformState` through project-file save/reload, backend
generation, independent admission, native engineering context and the Spec Kit.
State backend selection is independent of application target provider. Existing
invoice defaults remain an explicit compatibility adapter over shared protected
S3, Azure Blob, GCS and HTTP backend contracts. No platform store is provisioned.

The contract records per-environment backend, owner, intended residency and linked
decision ID. These are design records: a missing/Proposed/Accepted decision never
proves storage location, access, locking, recovery or migration approval. Generated
state metadata keeps those claims unverified and review defaults false. Root
acceptance blockers remain; children cannot select state for the composition.
Independent inspection rejects unselected backend changes, credential/TLS/locking
overrides, private state/plan/input artifacts, forged acceptance and altered owner
or scope. Committed backend examples remain environment-specific placeholders.

Changing the state contract invalidates prior context review while preserving its
original snapshots/evidence. `TASK-STATE-CUSTODY` supplies exact files, checks,
responsibilities and migration/rollback boundaries; account planning depends on
that task. `sample-handoff-task.json` is actual generated output from the public
cross-provider fixture, not a handwritten replacement. No UI was added or changed.

Validation:

- `js-tests-current.log`:520 passed, no failures/skips, including nine state
  regressions covering16 provider/backend combinations, persistence, mutations,
  context invalidation, handoff dependencies and environment separation.
- `build-final.log`: production build passed. Backend Python source remains the
  prior429-test source; no new execution of that suite is claimed here.
- `native-v1/summary.json`:18 actual generated roots passed Terraform1.17.1
  init with backend disabled and validate:16 provider/backend combinations,
  an unfamiliar five-unit cross-provider composition and standalone Google/S3.
  This is native configuration/schema evidence, not backend connectivity.
- `service-*-final/receipt.json`: actual service generation, independent admission
  and native unit checks passed for AWS/GCS16, Azure/HTTP18, Google/S3 15,
  IBM/Azure19 mock plans,68 total. These exercise selected backends differing
  from the application provider. Direct service invocation does not establish
  HTTP/auth, model-inference or application-runtime acceptance.
- `generated-final-manifest.json` and `final-artifact-comparison.json`: final
  native configuration/test/lock bytes match the18 qualified roots. Five HTTP
  example files changed to correct staging namespaces after native validation;
  their final bytes are independently inspected by the current generator/service.
  Native checks were not rerun or counted again for those example corrections.
- `source-manifest.json` binds exact source bytes. `references.json` records four
  reviewed primary backend references and snapshot hashes. Bulk packages, cached
  providers and source snapshots remain on MEM0.

The first new test attempt used the wrong project-reader return shape and omitted
Spec Kit fixture arguments; retained `state-tests.log` shows those failures, and
`state-tests-v2.log` shows the corrected public-API harness passing. Subsequent
inspection found/fixed an HTTP staging example retaining PRODUCTION in its path.
Earlier intermediate test/service results are not added to final totals.

Reproduce by generating a fresh MEM0 directory with
`compile-state-custody-probes.mjs`, then `check-state-custody-probes.py` against
that directory and a fresh evidence directory. It runs only init -backend=false
and validate. No backend credentials, cloud reads/plans/apply, state migration,
lock/recovery test or deployment occurred. Actual custody remains unverified;
local lock/recovery protocol qualification and deeper ownership/lifecycle parity
remain engine work. Cloud access is not required to continue the local programme.
The full28/unfamiliar block, connection and system evaluation remains required.
