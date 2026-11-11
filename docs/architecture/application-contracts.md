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
