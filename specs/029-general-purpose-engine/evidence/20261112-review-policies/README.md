# Shared review/access/semantic policy capability

This GE-006 engine change implements the reusable seams found independently in
Azure museum-label and Google sample-routing transfers. It does not copy their
field names or native application files into the shared runtime. No original
client export, owner project/preview, model/effort or cloud resource was changed.
No new native-model inference or deployment was performed.

## Invariant, applicability and interfaces

`ReviewPolicy` is an immutable trusted-bootstrap interface for typed approval
workflows. It declares editable top-level result fields, ordinary staff read scope,
optional inspection TTL, and a module-level semantic validator with explicit source
dependencies. The validator may reject, never normalize or replace data. Shape,
exact integer/Unicode/byte limits still belong to PayloadContract; domain arithmetic,
initial processing/mapping, native identity and real destination contracts remain
application duties. This is not a business recipe or automatic architecture compiler.

The policy binds its declaration, exact payload, validator entrypoint/dependencies
and mechanism source into reviewPolicySha256 in persisted destination/approval
identity. Declared source changes fail closed. Dependency labels may name relative
package paths when filenames repeat, without putting private absolute paths in the
public identity. This is explicit source binding, not automatic dependency discovery,
Python purity/sandbox enforcement or image/kernel attestation.

Producer/worker/native factories and normalized TLS publisher accept the same
explicit policy. Source/result semantics are checked on worker commit, edit,
approval and dispatch, and before publisher credentials/network. Only declared
result fields can change. Optional owner scope covers detail/list/cursor/events/
history; live reviewer authority remains account-scoped. Stable-key reuse by a
different submitter conflicts. Account-change approval/inspection retains the
supervisor/owner requirement; token claims cannot grant SQL roles.

Shared HTTP retains source/result envelopes. An explicit policy adds current source
representation, POST inspect, bounded history and revision/hash-bound approval.
Authenticated inspection records a representation request, not proof of human
reading. Approval requires current actor/account/revision/hash/policy and DB-clock
TTL. An edit requires reinspection. Repeated approval of approved/sent/unknown work
cannot enqueue another send; inspection expiry does not erase uncertainty.

Inspection uses existing append-only events and its relational operation/account/
actor/timestamp fields, rather than a new table or migration. SQL schema bytes and
grants are unchanged. Omitting a policy preserves legacy envelopes/read/approval
behavior. Enabling/changing one needs a fresh namespace or reviewed reconciliation;
old workers cannot silently acquire or remove it. See
`docs/architecture/application-contracts.md` for API, packaging and rollback limits.

## Independent execution and transfer

Latest `regressions-v2.json`:138 tests, zero skips, actual private PostgreSQL17.11,
native Procrastinate queue workers, ASGI intake and real synthetic TLS recipient.
This includes16 new policy tests and existing payload/HTTP/native-factory/binding/
role/worker/uncertainty/recovery checks. The actual final source snapshot is pinned
by archive/image/command and source hashes. Earlier137-test pass and focused13/15
runs are retained, including setup failures and evaluator mistakes. No failing test,
assertion, prerequisite or old native check was removed to obtain acceptance.

Two evaluator-authored domains exercise different source/result contracts and
semantic callbacks: parcel mass/routing and audio caption billing. Neither is a
production dispatch key, original28 project, blinded holdout or native-model
comparison. Tests independently reject derived values in both directions, freeze
undeclared edit fields, retain NUL/non-BMP and empty values, test separate60000-byte
source/result budgets, detect callback transformations and dependency changes,
exercise four-way atomic idempotency/one job and cross-owner conflict, live role
removal, owner-scoped cursor/history/events, actor/hash/revision/TTL inspection,
changed policies, supervisor rules and unknown no-replay.

Actual workers deliver only after approval in both domains. Reviewer edits to empty
advance revision and require a new inspection. The receiver body and approved hash
are independently compared with exact expected normalized payload/source/result/
revision/destination values; tampered dispatch is rejected without a second effect.
No source field is silently added to the normalized external contract. Native
factory tests use real synthetic JWT crypto for AWS/Azure/Google/IBM, injected SQL
and synthetic key lookup; this is not four-cloud managed-service execution.

Counterexamples remove semantic validation, inspection enforcement or owner scope
only inside isolated source archives. Their expected test failures and unchanged
oracle hashes are recorded separately from positive results. Product sources and
frozen client packages are never edited by mutation tests. Review their receipts
rather than interpreting a failed counterexample suite as a product failure.

555 JavaScript tests,457 server tests and production build pass. Server tests
actually materialize all four provider SDK catalogs and run the copied pure policy
with no host repository or database/cloud SDK imports. Source/catalog manifests
match the production files; emitted invoice/shared inventories include the new
module. This does not establish complete generated applications, actual model
choice or clean cloud image/provider acceptance. Existing build chunk warning stays
visible. No frontend/CSS change or owner preview activation accompanies this patch.

## Reproduce and review

Use the explicitly owned engine Docker endpoint and pinned cached Azure SQL check
image63164e32. The controller uses the original bounded PostgreSQL validation
profile: no host ports/mounts, network none with container-local SCRAM loopback,
nonroot fixture, read-only source, fixed CPU/memory/PID/time/output limits. It
creates and removes its own database/container; existing host/owner databases are
not used. Scratch fixture password/config remain inside the disposable container.

Run from repository root, using fresh output directories on MEM0:

    .venv/bin/python specs/029-general-purpose-engine/evidence/20261112-review-policies/run-probe.py --regressions --output .local/external-artifacts/review-policy/NEW-full
    .venv/bin/python specs/029-general-purpose-engine/evidence/20261112-review-policies/run-probe.py --counterexample semantics --output .local/external-artifacts/review-policy/NEW-negative

Use inspection/owner for the other isolated mutations. Without either flag the
controller runs only the policy suite. The helper snapshots authoritative runtime
and evaluator source; the receiving test image supplies pinned test dependencies,
not the host virtualenv. No host package installation or network fallback is used.
Archives and verbose raw failures remain ignored on MEM0 under review-policy/v1.

Manual review card: inspect a newly materialized SDK's source/manifest; construct
one explicit policy in trusted application source; submit a typed operation,
inspect it as an enrolled reviewer, change only an allowed field, verify stale
approval fails, reinspect and approve; inspect the synthetic normalized recipient
and history. A generated app still needs its own UI/entrypoints/identity/resource/
clean-image/full-system checks. This source checkpoint is not a frozen alpha.5.

Rollback development source only with tests/workers stopped, preserving pinned
client artifacts. A running policy-bound database must retain its exact old code,
policy and destination bindings or undergo separately reviewed reconciliation;
never rewrite approvals/unknown rows or resume a different binary as a shortcut.
No SQL migration, managed backup restoration or old-image rollback is qualified.

Next: explicit operator-owned validator placement and original-worker cleanup/
evidence binding; complete IBM/native application and remaining receiving checks,
then qualify alpha.5. The full ten-increment programme,26 remaining originals and
unfamiliar systems remain. Counts stay2/28 original projects, four offered
increments, owner acceptance0 and measured quality unknown.
