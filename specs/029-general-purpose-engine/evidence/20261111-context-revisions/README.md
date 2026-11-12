# Immutable current-context transfer

Engine source: `e68aec7c68d69fe0822e303d18ce9bd924720d0f`. GE-003 remains
in progress. No alpha.2, new original-case acceptance, quality percentage or hosted
qualification is claimed. Original local acceptance remains **1/28**.

## Implemented behavior

Build saves before each client start/update and includes the exact saved-file
SHA-256. Under the submission lock, the service validates and stores the authorized
snapshot outside the native workspace, attaches its immutable revision to the
reserved request UUID, and rejects intervening saves before inference. The adapter
sends unchanged client text plus a separate labelled context evidence envelope.
Original workspace files/pins and automatic repair behavior remain intact.

Exact bytes, Unicode, ownership and existing scope are retained. Reversions append
history; consecutive identical bytes reuse it. Lost acknowledgements preserve
request/revision identity and never cause automatic replay. Full bounds, source
handling and local-versus-hosted limits are in
`docs/architecture/architecture-work-model.md`.

## Validation

* 393 JavaScript tests, 404 backend tests, no skips; production build passes with
  the existing large-chunk warning. Exact logs are adjacent.
* Focused local tests cover cross-project/session/tenant boundaries, corruption,
  stale saves, finite/lossless JSON, explicit byte/history limits, separate exact
  adapter inputs, original pin preservation and lost start/steer acknowledgements.
* Actual browser fixtures pass: save before first work and updates, digest binding,
  save failure retains the draft and prevents steering, reload/recovery, transcript,
  download/check behavior, shared-model scoped invalidation and mobile layout.
  Model/backend responses in these browser fixtures are explicit doubles.
* Actual native transfer uses **gpt-6.1-sol/high**, one session and two completed
  turns. A saved river-depth requirement changes from millimetres to centimetres.
  The client prompt is identical; the new unit arrives through the saved-context
  revision. Both downloaded packages pass 18 independent contract assertions under
  the isolated Linux controller. The original package fails the new contract.
* Native history matches both exact request UUIDs and full context envelopes with
  control-store snapshots/digests. The two artifacts retain identical original
  pinned inputs. Eleven native tool callbacks occurred. No runtime source changed
  during the run; `native/source.json` records every server/UI/skill source digest.
* An actual idle service/native-adapter restart recovers the same session/selection,
  both revisions and identical final capture manifest. The native run count stays
  two; zero inference requests are replayed. See `native/restart-recovery.json`.

Native packages, manifests, history, initial/changed project files, controller
receipts and the old-package counterexample are retained under `native/`. Their
SHA-256 values are in `native/receipt.json`. No generated export was patched.
This is an evaluator-authored transfer fixture, not a blinded holdout or one of the
28 originals. It tests module behavior, context delivery and recovery, not a full
cloud application or shared-model reconciliation.

## Retained evaluator failure

The first package passed all 18 assertions, but the evaluator incorrectly demanded
`testsReported == 18` from a plain `node -e` command. The controller only populates
that field for supported test-runner commands. Preserve the failing log and original
receipt. The corrected evaluator checks successful completion and its own emitted
18-assertion count; no assertion or source requirement was removed. Its explicit
`--continue-completed` path verifies/reuses the same completed request/package, then
submits only the new centimetre request. No first-turn inference was replayed.
The final evaluator hash is recorded separately from the frozen engine source.

## Remaining work and rollback

Context attachment does not prove design agreement, implementation completeness,
test acceptance or semantic reconciliation. The initial `project-context.json` is
still historical evidence. Add artifact-bound mapping proposals with current-context
and cross-project guards, retained revision history and independent graph/file/
requirements/evidence reconciliation before delivering alpha.2. Qualify the actual
UI/native round trip for those semantics; preserve the existing compiler's scope.

The development preview on port5281 uses an isolated app home under
`.local/context-revision-preview/e68aec7`; it is not a released candidate. The frozen
alpha.1.1 candidate on port5280 and its rollback instructions remain unchanged in
`docs/LOCAL_ENGINEERING.md`. Existing DBs migrate additively; do not delete or rewrite
native thread history, original artifacts or pinned inputs to roll back.
