# Architecture work context, version 1

This model connects recorded intent, requirements, responsibilities, interfaces,
explicit delivery units, implementation mappings, assumptions, decisions and evidence
references. It preserves the existing diagram and project records. It does not infer
a physical deployment unit from every diagram block or turn a proposed requirement
into an accepted business constraint.

`src/architecture-work.mjs` supplies the shared projection. Its optional persistent
state is `project.extensions.architectureWork`, version 1. Existing project files
remain format 2.3 and migrate by projecting their existing sources; they acquire no
invented mappings or execution receipts. Future unsupported state versions and
malformed references fail explicitly without discarding the original input.

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

GE-003 is unfinished. Native sessions still start from an immutable project snapshot.
We must add versioned current-context updates for existing native work, an
artifact-bound proposal/reconciliation path, and independent actual-native checks
that prove the diagram, requirements, implementation files and evidence remain aligned.
Revising/importing mappings must retain history and reject stale/cross-project artifacts.
Existing compiler views must consume the reconciled model without losing scope. No
alpha.2 release or original-case improvement is claimed by this foundation.
