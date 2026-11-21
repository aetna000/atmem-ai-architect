# Typed workflow HTTP checkpoint

GE-006 remains in progress. Four runnable increments/1-of28 complete original local
cases/zero owner acceptances are unchanged. No release5 or measured quality claim.
Owner UI/AtFlow CSS, previews and active jobs were untouched; no cloud deployment,
account action or database schema migration.

## Capability and limits

`workflow_http.py` adds a domain/provider-independent API for typed source intake,
operation listing/detail and revision-bound review/approval. Trusted bootstrap owns
account, origin, operation kind, payload/destination contracts and verifier. The API
cannot select these from request fields. Current membership comes from PostgreSQL,
including the established supervisor rule for account changes. It rechecks identity
and membership after streaming before inserting work. Unknown/duplicate envelope
fields, duplicate authority headers, invalid types and excess bytes fail explicitly.
The body read has an actual5-second deadline; admitted mutations are bounded per
process.202 proves durable enqueue, never processing or delivery completion.

This exposes the existing generic durable mechanism instead of repurposing invoice
upload/extraction/evidence/retention semantics. See docs/architecture/workflow-http.md
for endpoints, interfaces and limits. Native identity, provider/database bootstrap,
architecture-model selection, domain processors and whole-system/handoff qualification
remain implementation work. No missing-work gate was removed.

## Observed evidence

- runtime-v2.log:16 checks pass. Equipment reservations and editorial publishing
  each cross ASGI HTTP intake/read/approve, a real PostgreSQL/Procrastinate worker,
  human approval and a synthetic destination served over real loopback TLS.
  The ordinary user is denied approval; before approval no destination call exists;
  after approval one fixed-key/payload effect is recorded. Same-input HTTP replay
  returns the same operation without another destination call.
- 20 same-key HTTP submissions through an8-thread pool produce one operation and one real queue
  record. Changed source conflicts; caller tenant/role/kind/destination/contract
  overrides, duplicate JSON fields and foreign operation IDs are denied.
- Reviewer edits need the exact current revision and valid typed result; stale
  approval and revoked membership do not enqueue dispatch. A separate native-header
  fixture requires its configured signed-header transport with no Bearer fallback.
  Account-change approvals still deny ordinary reviewers and admit supervisors.
- Streaming tests revoke membership during input and verify zero queued work;
  the actual5-second read deadline stops a stalled stream with408 and zero rows.
- emit-packages.mjs emits/unpacks/byte-verifies four real application ZIPs. Shared
  runtime bytes are identical; no four-cloud runtime/IAM/network claim follows.
- The exact unpacked AWS-context application's own tests/run.py passes115 tests
  across13 suites, no skips, with all package sources unchanged. It includes the16
  new HTTP checks and the prior99 package checks. emitted-package-receipt.json
  records every suite/source hash. Bulk ZIPs/logs stay on MEM0.
- 537 JavaScript/430 server tests and production build pass. Final changed source
  and the test lock are bound in source-manifest.json. The prior fresh hash-locked
  AWS test environment is reused after confirming the emitted lock is identical;
  no new or relaxed dependency is introduced. Commands are in commands.json.

runtime-v1 is the earlier12-check checkpoint before deadline/revocation/native-header/
supervisor coverage. Both are successful historical receipts. Tests use synthetic
subject verifiers and business processors; ASGI intake is not real network ingress
or a browser. The real local TLS service implements the declared normalized action
protocol, not a vendor/business system. These are component/connection and regression
checks, not a complete original project, managed database or deployed-system proof.

## Next action

Connect shared architecture-model intent to provider-owned application/identity/
database/async bootstrap and explicit domain policies. Qualify connected application
failures and unfamiliar compositions, concrete handoff and runnable alpha.5 before
counting another release. Preserve all remaining increments and original28/unfamiliar
complete local systems; no cloud deployment is required or authorized.
