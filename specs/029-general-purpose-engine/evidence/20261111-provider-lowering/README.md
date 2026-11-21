# GE-005 checkpoint: exact provider-aware memory lowering

This implements a reusable quantity invariant for explicit supplied-image container
units, not another workload recipe. `containerMemoryBytes` retains an exact safe
integer byte quantity. Existing `memoryMb` keeps MiB semantics; conflicting fields
block instead of selecting one. Provider policies map exact sizes to compatible
CPU allocations, expressed as engineering proposals rather than performance/cost
claims. Existing systems and the four selected providers remain unchanged.

Supported AWS Fargate sizes follow the reviewed primary table, with explicit
Linux platform1.4.0, including the244GiB/32vCPU boundary. Azure uses the documented
Consumption-only combinations up to4GiB until a workload-profile contract exists.
Cloud Run selects generation1 below512MiB and generation2 otherwise, with reviewed
CPU/memory combinations through32GiB. IBM uses documented decimal sizes through
48GB. Decimal GB and binary GiB are deliberately distinct: an explicit IBM GiB
quantity does not silently become a smaller decimal GB. Unsupported exact sizes
retain required scope and block approval. The existing finite CloudWatch retention
contract is also honored for AWS; other runtime/application settings remain explicit
implementation work. No concurrent-request setting is disguised as an autoscaling
threshold. API schemas/import/save and prompts retain the exact bytes. The new field
is refused on other implementation contracts rather than silently ignored.

## Independent checks and current evidence

- 484 JavaScript tests pass without skips (`js-tests-current.log`);428 server tests
 pass without skips (`server-tests-v2.log`); production build passes
 (`build-current.log`, existing chunk-size warning).
- `native-v3-summary.json`: eight actual cached native init/backend-disabled schema
 checks and40 mock-provider runs, including separately authored exact memory/CPU
 assertions, ordinary and upper-bound cases for every provider. No generated
 implementation/configuration was patched. `generated-v3-manifest.json` preserves
 exact generated-file and separate oracle hashes; `current-output-equivalence.json`
 proves the current compiler regenerates those checked bytes exactly.
- Four actual public server generation/validation invocations execute58 module mock
 runs (`service-*-v1`), including both workflow and image units. Those earlier
 receipts predate README explanation and explicit AWS platform pin; they bind their
 own emitted file digests. The later eight native-v3 packages/current equivalence
 are the current exact artifact evidence. Do not combine repeated runs into a new
 whole-system acceptance claim.
- Independent configuration inspection derives applicability and canonical addresses
 from the project, not claimed metadata. Mutants change memory, public ingress or
 runtime identity and try to disable inspection via row metadata; all are rejected.
 Unsupported size/conflicting quantities retain root/child scope gates and input
 text/ownership. Separate API tests reject strings, floats, booleans, unsafe
 integers and applying the new field to a different implementation contract.
- Primary sources are reviewed and snapshotted with SHA-256 in
 `reviewed-source-manifest.json`; full content and generated working packages live
 on MEM0. Versioned provider docs and dated platform snapshots are distinct.

The first conflict regression found duplicate gap IDs suppressing the specific
conflict explanation; one explicit conflict gap now preserves both requirements.
A native-v2 probe expansion failed before native execution because a helper's
file-loop variable shadowed the case directory name. Its partial ignored MEM0
directory remains unchanged. Corrected helper writes distinct paths in native-v3,
whose generated digests/native results pass. V1 native results remain historical.

## Remaining GE-005 work and programme boundary

GE-005 stays in_progress; this is not alpha.4. Next implement/reconcile explicit
provider regions and placement inputs, native environment/network/identity checks,
reference/import/create preservation and lifecycle/state-custody policy. An explicit
container region can still be ignored by the old region input path; this is a
known counterexample to fix before release4, not region acceptance. Azure larger
Consumption profiles need an actual profile/environment contract. Configurable
CPU requirements, workload/image architecture, concurrency semantics, non-AWS
retention and other unresolved behavior need explicit implementation/contracts.
Do not silently map function settings onto different container semantics.

Then qualify parity/negative checks, browser/export behavior and a separately
frozen runnable alpha.4. Preserve alpha.3 on5285 and all earlier previews. Runtime
images, connections/full application journeys and model conversation behavior were
not executed by these configuration checks. No account, region availability, cloud
plan, state migration or deployment was verified/authorized.

Three runnable increments remain offered, original complete local qualification
1/28, owner acceptance0 and95% quality unproven. The remaining seven increments,
all original28 and unfamiliar complete local systems remain required. Previous
goal turn was progress: alpha.3 source/build/service/browser qualification, local
release and branch backup changed authoritative state. This turn adds source
capability and independent checks; the full goal remains active.
