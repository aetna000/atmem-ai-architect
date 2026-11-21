# Reusable application payload contract checkpoint

GE-006 remains in progress. Four runnable increments,1/28 complete original local
projects and zero owner acceptances are unchanged. No release5 or measured-quality
claim. Existing owner UI/AtFlow CSS, previews and native jobs were untouched.

## Implemented mechanism and applicability

`workflow_payload.py` defines an immutable bounded object input/result language,
independent of domain/provider. Its digest binds to the persisted destination and
human-approval fingerprint. The existing producer, PostgreSQL store, queue worker
and explicit normalized HTTPS destination share that binding. Input, worker result,
reviewer edit, approval/dispatch and destination validation reject unknown fields,
coercion, changed policies and oversized bytes without clipping or rewriting data.
Membership, account boundaries, role policy, leases and uncertain-effect rules stay
in their established shared mechanisms. Domain semantic validation remains separate.
See docs/architecture/application-contracts.md for the contract, interfaces and limits.

The source/fixture probe records a concrete old-code failure. On frozen94e98a8,
changing the destination configuration after queue insertion still allows a pending
operation to be claimed. On repaired code the same source input is rejected and
the persisted operation remains pending. before.json and after-v2.json identify
exact runtime/input hashes; probe-stale-contract.py is the independent driver.
after.json is an earlier intermediate receipt, superseded by after-v2.json.

## Observed evidence

- runtime-v3.log:13 checks, including equipment reservations and editorial publishing
  through real local PostgreSQL/Procrastinate producer/worker, live membership,
  human approval and a synthetic TLS destination with certificate verification.
  Source data stays out of the outbound action; stable ID/digest and exact result
  reach the destination once. A changed declaration is rejected before credentials.
- New checks cover UTF-8 boundaries, structural/type errors, immutable definitions,
  duplicate submissions, no insert/history change for invalid input/result, reviewer
  denial, cross-account reads, changed-contract processing/result/approval/dispatch
  rejection, same-contract reconstruction and corrupted persisted result rejection.
- durable-regressions-v3.log:89 existing shared-runtime checks pass, including real
  workers, membership/tenant fences, atomic enqueue/rollback, leases, unknown effects
  and stable-key replay. This is regression evidence, not89 new capabilities.
- emitted-manifest-v5.json records four application ZIPs on MEM0, independently
  unpacked/byte-checked; shared runtime bytes match across targets. This does not
  prove four cloud applications. Only the AWS dependency context is executed here.
- A fresh MEM0 Python environment installs the emitted AWS test lock with isolated
  pip, binary wheels and required hashes (locked-setup-v1.log). The exact unpacked
  package's own tests/run.py passes99 tests across12 suites, including13 new contract
  tests; no skips, package sources unchanged. Full runner receipt is
  emitted-package-runner-v2.receipt.json. No root source override is used in that run.
- 537 JavaScript/430 server tests and production build pass in final logs.
  source-manifest.json binds final changed source, dependency versions and test lock.

runtime-v1/v2 and emitted-runtime-v1/v2 are earlier contract/callback checkpoints;
v3 adds real loopback TLS. v4 executes the packaged test file itself. The first full
package attempt used the minimal durable-only environment and failed imports for
invoice dependencies. Its failed47-test receipt is retained, not promoted to a pass.
The fresh locked environment resolves setup; no source, test or gate was weakened.
Final v5 differs from v4 only by the acceptance test's explanatory docstring.

## Reproduction and limits

Use the task-owned loopback fixture validated by tests/runtime/durable_postgres_acceptance.py;
never point these tests at a client database. Run the13 source checks with
`.local/durable-runtime/bin/python -I tests/runtime/workflow_payload_acceptance.py -v`.
Run `node specs/029-general-purpose-engine/evidence/20261112-application-contracts/emit-packages.mjs v6` from the repository root for a fresh archive
revision. Install its emitted test-requirements.lock with required hashes in a fresh
MEM0 environment, then run the emitted tests/run.py with --fixture pointing to the
owned fixture and --out a new directory beneath that package's .local. Exact prior
commands are in commands.json; archive locations are in manifests. Preserve prior bytes.

No cloud identity/model, actual business processor/destination, managed database,
provider IAM/network or whole-system acceptance is established. Identity and domain
processing remain explicit fixtures; the local TLS service is the declared normalized
protocol. No schema migration, account operation or deployment was performed. New
typed workflows require a reviewed namespace/worker rollout; older binaries cannot
enforce new contracts. Existing invoice policy is not automatically replaced.

Next implement shared architecture-model selection, generic API/identity/persistence/
async composition and native bootstrap, then connected application/negative/transfer
qualification and frozen alpha.5. Keep all remaining increments and original28 plus
unfamiliar full-system local evaluation in scope.
