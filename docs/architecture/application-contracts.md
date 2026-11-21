# Shared application payload contracts

`workflow_payload.py` supplies an immutable version1 input/result contract for the
existing PostgreSQL/Procrastinate approval mechanism. It is independent of business
domain and target provider. A contract is trusted application configuration selected
by the compiler/bootstrap, never a request, token claim, model answer or database role.
Domain adapters still own semantic checks, identity verification and external mappings.

The closed data language supports objects with explicit fields/required fields,
bounded arrays, UTF-8 strings, portable exact integers, booleans and string enums.
Unknown keywords/fields, type coercion, boolean/integer aliases, non-string object
keys, excess structure and oversized bytes are rejected. It does not implement JSON
Schema, decimal arithmetic, arbitrary predicates or executable validation. Decimal
business values need an explicit string contract and domain semantic validation.

The declaration has exactly `version`, `id`, `source` and `result`; both boundaries
are objects. Each object has `type`, `properties` and `required`; additional fields
are forbidden. Strings specify `minBytes`/`maxBytes`, integers `minimum`/`maximum`,
arrays `items`/`maxItems`, and enums `values`. Overall payload/declaration limit is
64000 UTF-8 bytes, schema depth8/nodes256, object properties32 and array entries64.
These are explicit implementation boundaries, not inferred client requirements.

Construct `PayloadContract(declaration)` and pass the same contract to
`producer_store`, `WorkflowRuntime` and, for a reviewed normalized HTTPS destination,
`ApprovedHttpDestination`. The complete declaration belongs in the delivered
application configuration/source. Its SHA256 binds to the persisted destination
identity as `payloadContractSha256`; the approval fingerprint includes that identity.
Producer, worker and destination must agree. The destination adapter checks the
whole identity and typed data before obtaining credentials or making a TLS request.
There is no field stripping to make mismatched versions compatible.

Submit validates source data before inserting an operation or queue notification.
Worker result commit and reviewer edits validate result data before changing its
revision/history. Approval and dispatch recheck persisted data. Claims reject a
different application/destination identity before processing. Contract changes need
explicit reconciliation; a stable key cannot silently acquire a new source/policy.
No existing records, approvals or source requirements are rewritten. Live membership,
tenant isolation, privileged account-change approvals, leases, unknown external
outcomes and verified-idempotency replay rules remain enforced by the existing core.

Existing adapters without a payload declaration retain their established domain
validation and old destination shape. This is an opt-in reusable runtime capability,
not automatic inference of schemas from prose. Upgrading the code does not migrate
existing work or retrofit a declaration onto it. Use a new reviewed workflow namespace
or explicitly quiesce/reconcile older workers before enabling a changed contract;
old binaries do not acquire new enforcement merely by sharing a database.

The helper is emitted in the current invoice application packages on all four
targets. That carries reusable source, not a claim of generic application compiler
coverage or four-cloud runtime acceptance. Selection from the shared architecture
model, generic HTTP/identity/persistence composition, native bootstrap wiring and
full application/handoff qualification remain GE-006 work. Existing invoice policy
is not replaced or relabeled as a generic business implementation.

Evidence: `specs/029-general-purpose-engine/evidence/20261112-application-contracts/`.
Equipment reservations and editorial publishing run through real local PostgreSQL,
real producer/queue/worker, human approval and a synthetic TLS destination. The same
checks run from an exact emitted/unpacked application. TLS credentials/identity and
processing callbacks are explicit local fixtures, not cloud services or real domain
implementations. No new original-case acceptance, release5 or deployment is claimed.

## Unicode storage and schema admission

Fresh workflow schema2 stores source, result, result history and external receipt
objects as PostgreSQL `json`. Their canonical application serialization uses UTF8
without ASCII expansion, retains controls including U+0000, and preserves the
existing byte/type/structure/revision/approval boundaries. Destination metadata and
internal audit details remain `jsonb`; they do not carry arbitrary payload text.
This is a storage mechanism, not a new domain policy or text normalization rule.

PostgreSQL `jsonb` cannot store U+0000. Some JSON-to-text scalar functions also
cannot process it. Do not cast the payload columns to `jsonb` or use text scalar
extraction as a substitute for decoding and validating their JSON in the runtime.
This storage choice gives up JSONB payload indexing/operators; these workflows
query relational identity/state fields and bind decoded payloads in application
code. No performance or query-planning improvement is claimed.

Every store connection and worker startup checks schema version2, exact source
hash and pinned queue version before operating. Queue registration/heartbeat and
recovery cannot start against an unreviewed schema. Operator grants and maintenance
retain the same exact-version/hash checks. A mismatch fails without adopting,
rewriting or migrating an existing database. `initialize_database` remains fresh
CREATE-only; running it over an existing schema is an error.

Existing schema1 deployments require a separately reviewed and authorized migration,
with old/new workers quiesced, retained source/results/history/receipts and approvals
verified, destination bindings preserved and rollback assessed before switching.
No migration is supplied, performed or implied by this change. Keep old artifacts,
their schema and pinned runtime together until that process is approved. Rolling
back a binary across schema versions is not a valid rollback procedure.

The primary PostgreSQL17.11 source revision and actual old/new SQL, domain-transfer,
boundary and worker-admission checks are retained in
`specs/029-general-purpose-engine/evidence/20261112-unicode-persistence/`.

## Explicit review, access and source/result policies

`workflow_review.ReviewPolicy` is an opt-in trusted bootstrap interface for typed
approval workflows. It adds owner-scoped ordinary staff reads (or explicit account
scope), a declared set of editable top-level result fields, optional bounded
inspection lifetime, and a module-level semantic validator. It contains no cloud
or business-domain dispatch. Payload shapes and byte units remain in
`PayloadContract`; business arithmetic, routing and source/result relationships
remain in application source supplied by its owner.

Construct `ReviewPolicy(payload, id='owned-review-v1', editable_fields=[...],
read_scope='owner', inspection_ttl_seconds=300, validator=validate_result,
validation_sources=[...])`. The trusted module-level function takes detached
`source` and `result` dictionaries, returns `None` to accept, or raises to reject.
It must not change either dictionary, coerce values, return replacements, perform
network/credential access, or select executable code from incoming data. The
mechanism detects changed input dictionaries and non-None returns; it is not a
Python sandbox or proof of purity/resource limits. Source/result retain separate
64000-byte budgets. Arbitrary callbacks, decimal semantics and missing business
rules are not inferred from prose by this interface.

Declare the function's source file and all trusted source dependencies explicitly.
A list of paths uses basenames; for packages with duplicate filenames, use an
explicit mapping such as `{'a/limits.py': first_path, 'b/limits.py': second_path,
'checks.py': validator_path}`. Labels are portable relative names, never executable
module selectors; absolute paths, traversal and ambiguous labels are rejected.
Each must be a bounded regular file with an unambiguous portable source label; callback
closures and executable strings are rejected. The policy identity binds payload
hash, version/id, editable fields, read scope, inspection TTL, function entrypoint,
declared source hashes and the shared policy mechanism's own source hash. Runtime
use rejects changed declared files. This is source binding, not automatic discovery
of all Python dependencies or runtime attestation. Validate complete applications
independently; keep API/worker/publisher files and dependencies identical in the
receiving build.

Supply the same `review_policy` to `producer_store`, `WorkflowRuntime`,
`create_native_api`, `create_native_worker`, and `ApprovedHttpDestination` where
used. `bind_review_policy(destination, payload, review)` exposes the exact bound
identity for custom trusted publishers. Missing/mismatched policies fail before
processing or delivery. `reviewPolicySha256` is part of persisted destination
identity and every approval fingerprint, alongside any existing payload/application
bindings. Source-derived semantics are checked before worker result commit,
reviewer edit, approval and dispatch; the normalized publisher rechecks before
obtaining destination credentials or opening a connection. Editable-field checks
freeze all other result fields, including both directions of numeric changes.

The shared HTTP interface retains `{source: ...}` submission and
`{revision, result: ...}` review envelopes. With an explicit policy it exposes
source with the result, adds authenticated reviewer `POST .../inspect` with `{}`,
and requires `{revision, payloadSha256}` approval. History is available through
`GET .../history` with a bounded `afterRevision` cursor. Inspection records an
explicit authenticated request for the exact representation; it does not prove a
human read it. Approval checks the live reviewer, account, revision, content hash,
current policy and database-clock lifetime. Changing a result requires a fresh
inspection. Account-change inspection/approval still requires supervisor/owner.
Already-approved/sent/unknown work cannot acquire another dispatch merely through
repeated approval; an expired inspection is not a reason to replay an unknown
external action.

Owner scope covers get/list/cursors/events/result history. Live reviewers can read
within their account; revocation/removal of their role takes effect on the next
operation. Cross-owner stable-key reuse conflicts. Caller token roles/groups,
account IDs and query overrides do not configure these policies. The ordinary
staff owner boundary is independent of provider-specific cryptographic identity.

Inspection receipts use the existing append-only event ledger, with operation,
account, actor, revision, hash and database timestamp. No new table/schema/grant or
migration is introduced. Existing workflows that omit `review_policy` retain
previous HTTP envelopes, account reads and approval behavior. Enabling or changing
a policy alters its integration identity: use a new reviewed namespace or quiesce
and explicitly reconcile older work. Never rewrite old approvals/unknown outcomes
or silently remove policy enforcement to run an old worker. Old source bundles and
native check history remain unchanged; binary rollback with a different policy is
not compatible operation recovery.
