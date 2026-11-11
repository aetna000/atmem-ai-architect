# Architecture work context, version 2

This model connects recorded intent, requirements, responsibilities, interfaces,
explicit delivery units, implementation mappings, assumptions, decisions and evidence
references. It preserves the existing diagram and project records. It does not infer
a physical deployment unit from every diagram block or turn a proposed requirement
into an accepted business constraint.

`src/architecture-work.mjs` supplies the shared projection. Its optional persistent
state is `project.extensions.architectureWork`, version 2. Existing project files
remain format 2.3 and migrate by projecting their existing sources; they acquire no
invented mappings or execution receipts. Future unsupported state versions and
malformed references fail explicitly without discarding the original input.
Version1 state migrates losslessly by retaining its records, intent and review
history and adding an empty artifact-mapping history. Producer proposals retain
their independent version1 format. Older readers must retain version2 files rather
than discard their new fields.

## References and changes

Source references use `project:identity`, `intent:project`, `selection:provider`,
`requirement:ID`, `block:ID`, `interface:ID`, `assumption:ID`, `question:ID`,
`decision:ID`, and explicit `work:ID` declarations. Recorded native client intent
uses opaque session IDs and backend event sequence numbers. Original text, order,
pending/uncertain delivery and later acceptance are retained; partial replay cannot
rewrite text or downgrade an accepted request. Internal automatic repair instructions
and model replies are excluded from client intent. Recorded native intent also enters
Design consultation context through its existing bounded continuation transport.

Block context depends on its linked requirements, assumptions, questions and accepted
decisions. An unscoped accepted decision conservatively depends on all requirements;
explicitly scoped declarations can be narrower. Interface context includes both
endpoints. Work declarations explicitly name their dependencies. Unclassified native
client updates conservatively affect all mappings until semantic reconciliation.
Project identity and target provider remain part of the context. Late callbacks from a different project are ignored; asynchronous proposal imports apply against the latest matching project, and a context review rejects sources changed since display. Moving a block or
changing its connection-handle position does not alter its meaning.
Structured brief/use-case/fact/workflow changes and substantive diagram annotations
are intent changes too; notes are not deployment units. Additional interface contract
fields participate in comparison. Exact saved context is read without the legacy
compiler's adapter/default normalization so a new contract cannot silently disappear
while an artifact is being linked.

Context review captures the exact transitive source values and reference sets. Full
JSON values are compared, rather than relying on a weak UI hash. Shared snapshots are
stored once and reused across bindings. Older review bindings and snapshots remain
available after a later review. Missing/deleted targets stay visible; missing sources
cannot be reviewed as current. Cycles are bounded dependency relationships, not a
circular proof of successful implementation.

The view distinguishes `unreviewed`, `current`, `changed` and `missing` context. Existing
accepted decisions and reported test outcomes are retained verbatim. A change adds a
need for review; it does not silently rewrite the client's history or erase a failed
check. The UI puts affected records first and shows source details. The legacy delivery
pack exports the same projection as `architecture-work.json` alongside the project file.

## Proposals and evidence

A proposal is a JSON object with `version: 1` and a `records` array. Each record names
an ID, kind, title, description, dependencies and JSON data. Record kinds include
responsibility, delivery unit, interface, implementation, requirement, assumption,
decision and evidence. Import always makes these records agent-proposed and unreviewed,
even if their data claims a passing test. It cannot overwrite an existing mapping,
change diagram ownership/provider or replace client requirements. Implementation
paths must be relative project files, without traversal or host paths.

New engineering workspaces receive the pinned public schema at
`atmem-tools/architecture-work.schema.json`. It documents the optional
`architecture-work-proposal.json` producer format. Legacy workspaces retain their
original pinned inputs; the schema is not retroactively inserted into them.

A context review is **not** an acceptance, authenticated artifact receipt or successful
execution. Arbitrary evidence data remains a claim/reference. Actual immutable file
hashes, registered validator reports, independent assessors and account/deployment
boundaries remain authoritative. Manual project edits are not cryptographic proof.

Storage limits reject oversize input without clipping: work IDs use at most 200 Unicode
code points, references 240; metadata text uses explicit code-point bounds. State has
at most 1,000 records/intents/current bindings/past bindings, 4,000 shared snapshots and
1.5 MB of UTF-8 JSON. Proposals add at most 200 records at once. The complete project
file's existing 2 MB limit is now checked in UTF-8 on both export and import. These
are application storage bounds, not invented customer quotas. Existing credential
checks still apply to all source/history/proposal data.

## Validation and unfinished work

Unit coverage exercises transitive/scoped changes, provider/ownership changes,
missing/deleted references, cyclic relationships, history/deduplication, legacy
round-trips, lossless native intent replay, finite JSON, path escapes, credential
refusal, UTF-8 limits and Unicode producer/consumer schema agreement. Actual browser
checks exercise a library workflow, requirement editing, stale evidence, unrelated
mapping retention, import, save/reload, UI/export agreement, native event persistence
and desktop/mobile layout with explicit fixture backend/model responses. A river
telemetry fixture provides a different domain. These are not blinded holdouts.

GE-003 is unfinished. Native sessions retain their immutable initial snapshot.
Each new client start/update can now attach a separate immutable current-context
revision from the authorized saved project. See the revision contract below. We still need an
artifact-bound proposal/reconciliation path, and independent actual-native checks
that prove the diagram, requirements, implementation files and evidence remain aligned.
Revising/importing mappings must retain history and reject stale/cross-project artifacts.
Existing compiler views must consume the reconciled model without losing scope. No
alpha.2 release or original-case improvement is claimed by this foundation.

## Native context revisions

The session service stores exact UTF-8 project file bytes and SHA-256 outside the
model-writable workspace. Each changed saved snapshot appends a revision; unchanged
consecutive bytes reuse a revision, and reverting to earlier bytes appends a new
revision. Request UUIDs bind immutable revisions before native submission. This
records attachment, not acknowledgement, acceptance, execution or completed design
reconciliation. Lost acknowledgements leave the existing request/context association
intact; recovery never resubmits either. Automatic repairs retain the prior thread
context rather than inventing a new client design update.

Build saves before every client submission. The save response hashes the exact
written bytes; start/steer check that digest against the server-resolved saved file
inside the session's submission lock. An intervening save fails before inference.
Legacy API clients without the optional digest attach the current saved file without
that optimistic concurrency guard. Browser input cannot supply snapshot content,
native handles, workspace paths or revision identities.

The Codex adapter sends the exact client text as its first input and a separately
labelled evidence envelope as its second input. The envelope preserves the complete
project JSON as an encoded string, revision identity and digest. It is evidence to
reconcile, never authority overriding client intent or worker policy. Existing native
request IDs, model/effort and start/steer recovery semantics remain. The original
project-context.json and all pinned inputs stay untouched, including legacy sessions.
The browser/session data contract does not depend on a CLI or local host path.

Bounds explicitly reject without trimming or pruning: 2 MB per UTF-8 snapshot,
1,000 revisions and 20 MB stored context per session. Duplicate JSON keys, nonfinite
numbers, invalid Unicode, mismatched project identity, stale digests, symlink/special
saved files and stored digest corruption fail closed. These are implementation
storage bounds, not customer quotas. Native model context capacity is a separate
limit; a rejected inference is not a reason to truncate design evidence.

The protocol surface follows [official App Server documentation](https://developers.openai.com/codex/app-server/),
checked against the installed adapter's request contract. Component doubles and
browser fixtures do not establish actual native transfer; the separate river-depth
evaluation script exercises that boundary without patching generated files.

## Artifact-bound proposals

The project-bound `/api/engineering/reconciliation` service accepts only a captured
artifact ID. It requires the current completed delivery run, verifies archive and
proposal bytes against the immutable manifest, validates the public proposal schema,
and binds declared implementation/test files to actual relative files and SHA-256
values. Missing files, supplied inputs, directory/path escapes, malformed/duplicate
JSON, invalid identities, credentials and unresolved intent delivery reject atomically.
A missing proposal is explicit; no mappings are invented. The latest accepted client
start/update supplies the immutable context; automatic repairs retain that context.
A recovered lost start acknowledgement restores its exact durable client text once,
with automatic repair prompts still excluded from client intent.

The server stores an immutable digest-bound reconciliation receipt outside the
native workspace. The browser verifies its exact encoded bytes and context digest,
then applies the proposed records to the latest matching project. This transport
integrity check is not a detached signature or runtime acceptance. All current
semantic sources, except mapping IDs being explicitly revised, must agree with the
saved context after exact client-history synchronization. This is conservative
whole-context comparison; scoped individual context reviews remain separate.

Mapping references must resolve. An implementation must name real captured files.
Existing client requirements, decisions, graph/provider/ownership and imported,
user-authored or accepted mapping records cannot be overwritten. A later artifact
can explicitly revise only its own session's unchanged, agent-proposed records.
Previous receipt record values, file hashes and source snapshots remain retained;
missing records are not deleted. Receipt reapplication is idempotent. A new artifact
supersedes earlier artifacts in that session; requirement/brief/interface/ownership
changes remain visible without rewriting historical evidence claims.

Build and Design block review show the same artifact mapping projection. The delivery
pack exports it as architecture-artifact-mappings.json and the Spec Kit as
artifact-mappings.json. Generation-quality reports reference those same mappings
without clearing compiler gaps or claiming tests ran. Coverage means only an explicit
file-reference link; global change dependencies such as an unscoped ADR do not prove
that one implementation covers every requirement. Unmapped requirements and blocks
remain visible. Native packages are separately downloadable; metadata references do
not embed their source in a compiler-generated ZIP.

Version2 stores at most1,000 immutable artifact mapping receipts under the existing
1.5MB work-state bound and 2MB complete-project bound. Each receipt retains at most200
records and2,000 file references; source snapshots are deduplicated. Limits refuse
without clipping or pruning history. Reopened/exported metadata is not authenticated
proof: reverify receipts with the owning session service and execute the exact
packages. The current single-owner service does not qualify hosted authorization,
leases or distributed transaction behavior.

Component/browser fixtures and the actual-native orchard round trip qualify this
reconciliation path. Two real turns preserve mapping identities/history across a
requirement edit, with20 independent checks per artifact and an old-artifact failure
under the new contract. Exact native/context/receipt history and full Build restore
are audited. Runnable alpha.2 preparation is tracked separately. Broad provider composition,
full connected systems and the remaining27 originals remain later programme work.
