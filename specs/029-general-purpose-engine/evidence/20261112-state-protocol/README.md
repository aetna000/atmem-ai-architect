# Native local state protocol checkpoint

GE-005 remains in progress; this is not alpha.4 or another original project
qualification. Three runnable increments,1/28 full local originals, zero owner
acceptances and unknown overall quality remain the programme counts.

Explicit root state packages now include a byte-bound `state-contract-check.py`
and concrete STATE.md/Spec Kit instructions. It creates only a fresh synthetic
loopback HTTP/SQLite fixture and two isolated native Terraform workspaces. It
never reads project backend inputs, inherits cloud credentials, invokes apply or
migrates state. No production state service is supplied by this fixture.

Two actual unpacked outputs ran the exact emitted helper: Azure application with
HTTP state choice and Google application with GCS state choice. Each passed18
checks. These are two executions of the same HTTP/local-store contract, not two
different state-platform qualifications. Both retain selectedBackendVerified=false,
generated acceptance=not_verified and unchanged root gates.

`emitted-{http,gcs}-v2/report.json` records actual Terraform1.17.1 binary and helper
SHA256, native commands and expected exit codes. Each run demonstrates:

- Two native backend initializations and native reading of synthetic lineage,
  serial, outputs and resource inventory.
- A live native plan holding a lock while a second native writer receives the
  expected lock-conflict exit1. The first plan completes and unlocks with exit0.
- Invalid credentials, foreign-owner unlock, incorrect lock ID and foreign state
  replacement are denied. Fixture recovery refuses an active writer.
- Plan-only native clients do not write state. Local SQLite versions survive
  reopening; checksum-verified fixture recovery restores exact original bytes,
  and the native client observes identical restored lineage/payload.
- A corrupted synthetic backup is rejected without replacing good state. An
  uncertain abandoned fixture lock survives reopening and still requires the
  matching owner and lock ID.

The SQLite version/recovery checks are local fixture-controller operations, not
Terraform migration, backup authenticity, process-crash or remote-platform recovery
proof. HTTP is loopback-only with ephemeral fixture credentials; TLS, cloud auth,
S3/Azure/GCS native storage behavior, external service durability, tenancy and real
project backend custody remain unverified.

Evidence:

- `emitted-*-v2/receipt.json`: full generated artifact digests, source identity and
  unchanged custody declarations. All raw work/databases/native logs are on MEM0;
  public reports omit credentials, raw lock-owner/host details and private metadata.
- `unchanged-project-native-files.json`: all8 Terraform/test/lock files in each
  case are identical to the prior18-root qualification. The helper does not alter
  the selected backend or deployment implementation.
- `js-tests-final.log`:521 passed, zero failures/skips. The added regression binds
  emitted Python to source and rejects modified/missing helper code or a forged
  selected-backend verification claim.
- `build-final.log`: production build passed. Python backend source remains the
  previously qualified429-test tree; no new backend-suite execution is claimed.
- `source-manifest.json`: exact generator/helper/evaluator bytes and original
  emitted source hash. `references.json` binds the reviewed native HTTP protocol.

Earlier source/v1 executions are retained privately or as historical public v1
receipts and are not added to final counts. Final v2 adds explicit expected native
exit codes so the deliberate second-writer denial cannot be mistaken for an
unexpected failure or a successful plan. No failing check was removed.

Reproduce on a generated state package with
`python3 -I state-contract-check.py --terraform /absolute/path/to/terraform
--work-dir /absolute/path/to/fresh-fixture` or run the independent unpacking driver
`scripts/engine-evaluation/check-state-protocol.py` with a public synthetic project
and fresh MEM0 work/evidence directories. No caller-supplied endpoint is accepted.
Native credentials and CLI environment are replaced with isolated fixture values.

Next: remaining lifecycle/reference/import and provider operating-policy parity,
then browser/export and frozen runnable alpha.4. The other increments and all28
original/unfamiliar local block/connection/system evaluations remain required.
Owner UI, running projects and cloud accounts were untouched.
