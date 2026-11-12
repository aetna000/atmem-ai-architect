# Lifecycle provenance and ownership checkpoint

GE-005 remains in progress. No release4 or additional complete-project acceptance
is claimed. Current counts remain three runnable increments,1/28 original full
local projects, zero owner acceptances and unknown measured quality.

`before.json` records48ec764 counterexamples: an explicit external reference lost
its reference record when an implementation marker was present; observed Pulumi
URNs disappeared during project conversion; root state-import instructions could
be injected without a fatal consistency finding. These were static probes only.

The engine now preserves bounded full Pulumi URN/type provenance in the versioned
`extensions.externalReferences` contract, through project-file save/reload, native
context and root exports. Inputs/outputs/secrets are still discarded. Oversized,
duplicate or malformed identities are rejected without clipping or selecting an
owner. Existing reference markers remain external even when their previously
selected implementation is recorded. Reusing attached external provenance as a
proposed/create component is rejected; a new deployment needs a separate identity.

The root `deployment-ownership.json` reconciles actual managed addresses against
each component's reference/new-source/create disposition and observed provenance.
Independent checks reject managed addresses on preserved components, root/child
import/moved/removed instructions and forged ownership/migration records. The
Spec Kit points resource tasks to the concrete inventory. Changing external
identity invalidates prior context review without rewriting its original evidence.

This preserves metadata import, reference and existing-source/create boundaries;
it does not implement Terraform/Pulumi adoption or authorize state migration.
Those remain separate reviewed capabilities when actually required. URNs are
logical resource identities, not native physical IDs or proof of behavior/access.

Validation:

- `js-tests-current.log`:529 passed, zero failed/skipped; eight new regressions
  cover all four providers, identity bounds/secrets, preservation, context and
  negative managed-address/state-transition/inventory mutations.
- `build-final.log`: production build passed. Python backend source is unchanged
  from the earlier429-test tree; no new execution of that suite is claimed.
- `service-{aws,azure,gcp,ibm}/receipt.json`: actual service generation/admission
  and native cached schema/unit mock checks pass for both active units in every
  provider,17/19/16/20 mocks respectively,72 total. Each project also includes an
  observed-state reference and an explicit already-running service marker.
- `provider-parity.json`: actual supplied-image native resource/query/protection
  and ownership inventory, including limitations and the open partition defect.
- `browser-v2/receipt.json`: actual isolated5344/8944 browser and HTTP service
  checks,16 native unit mocks,122 generated-file hashes matched to the downloaded
  ZIP, retained external provenance/zero managed addresses, Design entry, mobile
  layout, reload and exact gpt-6.1-sol/high selection. No architect/engineering
  inference submissions or page errors. ZIP/screenshots stay on MEM0; mobile
  screenshot inspected. The primary package still identifies as alpha.3; this
  temporary preview is not a frozen new release.
- `generated-manifest.json` and `source-manifest.json`: exact generated/source
  bytes; `references.json`: reviewed primary identity/import/partition sources.

Browser-v1 clicked validation before the UI's real service connection was ready,
then timed out waiting for success. Its failure text/screenshot are retained. The
driver now waits for the actual connected indicator before clicking; v2 passes
without mocking transport, replaying the old request or changing product UI.
The test-only preview was closed after qualification; owner previews/jobs remain
untouched. Direct-service72 and browser16 are separate transport observations of
overlapping fixtures, not independent project acceptances or added quality points.

`partition-counterexample.json` is an unresolved release blocker found during
parity review: AWS China placement is accepted while a supplied-image adapter
still emits commercial-partition ARN templates. It can claim infrastructure
complete incorrectly. Fix partition-aware lowering or retain a precise unsupported
partition blocker without substituting the destination before freezing alpha.4.
Do not remove this case or promote current parity checks to general AWS support.

Reproduce public packages with `compile-lifecycle-probes.mjs`, the existing actual
service checker and the parameterized `composition-candidate-smoke.mjs` against a
fresh isolated app home. No cloud refresh/read/plan, import, migration, application
runtime or deployment occurred. Continue the partition repair and remaining
provider policy/release qualification, then all remaining increments and28/unfamiliar
local block, connection and whole-system evaluations.
