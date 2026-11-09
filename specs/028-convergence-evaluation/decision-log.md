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
