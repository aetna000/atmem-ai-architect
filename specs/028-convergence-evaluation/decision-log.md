# Evaluation and implementation decisions

## Preserve a frozen baseline; repair the generator concurrently

The first complete run uses an immutable source copy, corpus digest and per-case
transcripts/exports. Current source changes cannot alter that run's behavior. Failed,
missing and timed-out cases remain failures. Compiler-only regeneration retains the
exact evaluated project and original export, records source hashes and creates a new
artifact directory; it is never counted as a new successful conversation.

## Qualify vertical slices before claiming provider parity

Interleave the single-unit and connected-system work in plan 027 per provider/capability.
A qualified unit is the prerequisite for its connected slice; unfinished units on other
providers remain visible. This allows testing a useful whole application early without
marking GEN-007/GEN-008 globally done. The first repaired slice is bounded, human-reviewed,
flat-schema AI processing with authenticated web access on AWS. Azure/GCP/IBM connected
AI application generation remains work to implement and qualify.

## Treat model output and provider data policy as runtime boundaries

The structured operation rejects invalid, duplicate, incomplete and out-of-contract
output. It executes no model actions. User enablement/subject is checked before inference
and before return. Model-service retention and text logging are read and enforced before
input leaves the handler; unknown settings block inference. No account-wide setting is
changed automatically. Real model quality, cloud identity and account policy tests remain
separate from fixture-based tests and provider mock plans.

## Own malformed proposals internally

One schema/revision repair is allowed before returning a failed operation. The original
request stays unchanged; a rejected proposal is never applied. Observed repair counts
are host-owned receipts, not model claims. Complex connected requests receive a bounded
240-second native-response allowance; simple requests retain 150 seconds. The regulated
case exposed a missing retrieval/identity classifier term; its failed 150-second run is
preserved and the corrected rule is covered by the actual frozen scenario text.

## Preserve consultation records

Long read-only records are split by Unicode code points into bounded continuation items.
There is no silent 1000-character truncation. Exceeding the API record bound produces an
explicit error until a retrieval-based larger-context path is implemented.

## Compact model wire protocol and evidence-driven finalization

The model emits revision-bound, whitelisted field edits and explicit additions/removals.
The host atomically validates the whole candidate and returns the existing full proposal
API. Unchanged graph/brief content is not copied through model output. No arbitrary JSON
paths, executable configuration or accepted-record rewrites are admitted by this patch
language. Original request state is unchanged on failure.

An exact recorded enterprise request exposed repeated evidence lookups. Project and
selected skills are already supplied; the model now receives useful memory, engineering
knowledge and pricing lookup tools. Approved retrieved contents appear once in canonical
context, with receipt pointers/IDs, query caching and observed provenance. If a lookup
adds no evidence, the next model round must finish using what is known. The final wire
schema forbids further tool requests. Missing facts remain explicit; users are not asked
to repair a tool budget or to narrow a complete brief.

Existing-reference contradictions now fail before resource generation, rather than
allowing a reference binding to create replacement storage or another deployment.

## Azure connected application repair, 2026-11-10

Added an explicit composed `azure-structured-app` capability with emitted Python 3.13
application/browser source, hash-locked runtime and test dependencies, a pinned official
container base, native App Service/model resources, managed identity, scoped permissions,
and single-tenant Entra API/browser registrations. It requires an existing access group
and reviewed ACR rather than recreating either. Each composed block owns its internal
resources explicitly; unrelated blocks and untyped integrations remain implementation gaps.

Local source tests exercise real JWT signatures, wrong identity/audience/scope/roles,
ASGI requests, input/output boundaries and scripted account-policy/model faults. The
runtime fails before sending input when the approved account data-handling capability
cannot be verified. It never writes that account-wide policy. Role claims authorize
until expiry; continuous revocation and destination MFA are not silently promised.

The live Azure ticket-triage case converged in two exchanges with zero technical
questions, zero compiler gaps and an independently consistent original handoff.
Its exact exported source, dependency versions, provider schemas and mock plans passed
local qualification. The current product emulation runs 15 emitted source tests with
external sockets denied. Container image startup/scan, live Entra/managed identity,
actual model quality and authorized cloud plans remain unverified. Production retains
the state/operations gate. This is one repaired case, not complete provider parity.

An invalid extra benchmark case selector was ignored by the old CLI while the valid
case ran. Original evidence is retained and counts exactly one case. Unknown and
duplicate selectors now fail before snapshotting or model invocation.

## Google application adapter and complete-brief acceptance, 2026-11-10

Added a separately implemented Google Cloud Run/IAP/regional Gemini composition.
Its keyless runtime, project-scoped prediction/policy-read role, image-pulling
platform identity, signed-header authorization and browser origin boundary are
explicit. Google-managed service identities use the pinned official Google-beta
provider; other resources use the pinned Google provider. The app never writes
project-wide model privacy controls. An expiring scoped owner review covers
abuse-monitoring terms that have no invented verification API; runtime separately
reads cache and model logging/sharing configuration. Review evidence is attested,
not independent provider proof. Existing project/group/registry are preserved.

Shared HTTP input/output/concurrency/origin handling was extracted and Azure's
15 emitted source regressions and provider checks rerun. Google has nine local
cryptographic/ASGI/scripted-transport checks, four browser checks, provider schema
and three plan-time mock tests. The live Google ticket-triage case converged in two
exchanges with no technical questions or compiler gaps; its unchanged original
handoff passed independent static and emitted-source/provider qualification.
Container images, real IAP/metadata/model behavior and cloud plans are not verified.

The acceptance audit found that reactive-facts runs may end before receiving
every corpus business constraint. They remain useful engineering regressions and
are never labeled semantically qualified. Added an explicitly versioned stronger
protocol that submits all remaining facts as one client update before export.
The corpus and acceptance criteria remain unchanged; preserve old results and
avoid direct exchange/time comparisons across protocols. Final matrix acceptance
must include every business fact and independent semantic/runtime checks.
