# Canonical Unicode workflow persistence and schema admission

## Generic capability and applicability

Fresh workflow schema2 stores bounded source/result/history/receipt objects as
PostgreSQL JSON, serialized using the already validated canonical UTF8 bytes.
This retains all accepted Unicode, including escaped U+0000, without normalizing,
clipping or narrowing domain intent. It also avoids ASCII serialization expansion
rejecting large valid non-BMP results at the history SQL bound. Payload contracts,
roles, tenants, task IDs, revisions, approval hashes, leases and uncertainty rules
are unchanged. Internal audit/destination metadata remain JSONB.

Every store connection and worker startup admits exact schema version/source hash/
queue version before use. Worker startup checks before opening/registering the
queue, heartbeat/recovery or callbacks. Operator grants and maintenance retain the
same version/hash guard. Fresh CREATE-only initialization does not adopt a schema.
Failed admission closes its connection. No migration or existing data rewrite runs.

The mechanism has no cloud/domain dispatch. Providers share the same modules and
explicit workload adapters. Do not use JSONB casts, text scalar extraction or JSONB
indexes on these payload columns; some PostgreSQL JSON processing also cannot
represent NUL. This choice does not claim database query/performance improvements.
Domain semantics and native authentication remain separate.

## Evidence

- `source-v1.json`: primary PostgreSQL17.11 source pinned to commit
  083ac033419f690758508e08c1736089384bbee8, review date/digest/applicability/limits.
- `before-v1.json`: actual old shared runtime fails both archive-transcription and
  sensor-annotation inputs after accepting their typed Unicode payload. JSONB
  raises an unsupported Unicode escape error. A stale schema marker is also
  admitted by the old store. The large emoji case is a regression boundary.
- `after-v2.json`: the identical original three-case oracle now passes, plus a
  separate actual worker-admission test;4 tests/no skips. Source, processing result,
  edit/revision, history, approval fingerprint, receipt and idempotency use real
  private PostgreSQL17/Procrastinate inserts with separate restricted API/worker
  logins. Controls, combining marks and non-BMP Unicode survive. A60000-byte emoji
  result persists, while oversize data is rejected without revision change.
- `counterfactual-v1.json` binds the unchanged original test bytes and exact
  before/after source archives; the worker guard is an additional test, not an
  altered old-case assertion. All archives remain on MEM0.
- `materialization-v1.json`: actual fresh native SDK materialization into four
  provider contexts, full manifest checks and exact shared runtime/schema bytes.
  This is not four-provider application execution.
- `regressions-v1.json`:81 existing checks pass/no skips across10 modules, actual
  workers, HTTP, TLS, restricted SQL, memberships, approval, recovery, grants, native
  role mapping fixtures and credential rotation. Native service mappings are
  synthetic. `regressions-v2.json` adds the two regular Unicode cases:83 pass/no skips.
-554 JavaScript and452 server tests plus production build pass; existing bundle
  size warning remains. Embedded runtime/test source catalogs are regenerated.

## Reproduction and fixture boundaries

`run-probe.py --output NEW_DIRECTORY` snapshots actual shared source and invokes
the unchanged operator-pinned AMD64 SDK/PostgreSQL check image. `--regressions`
runs the existing suites without changing their source/assertions. All output is
bounded; failure, skip, zero-test and timeout remain distinct. Only new directories
are accepted. No inference is submitted.

The controller creates a new private PostgreSQL instance inside its network-none
container and removes it afterward. The regression helper enables only container
loopback TCP/SCRAM for the suites' existing nonce-guarded fixture interface and
subprocesses; no host port/network/socket/source mount is added. Its protected
fixture config/password live only in container tmp. The named denied-role target
qualification_admin is created NOLOGIN for the existing role-escalation assertion.
Actual administrative access remains the disposable fixture owner.

Earlier regression attempts failed at test setup: changed Unix-socket port, missing
loopback SCRAM admission and absent qualification_admin. Their full results remain
on MEM0 and are not passes. No application safeguard or test was removed. The
corrected setup executes the unchanged existing tests. Deliberate uncertain-action
job errors in successful suites are expected tested outcomes, not delivery success.

## Release and compatibility boundary

This is a GE-006 engine checkpoint. Existing schema1 clients keep their old pinned
runtime/package; they are not rewritten. Upgrading to schema2 requires explicit
review/authorization, quiesced workloads, verified preservation of source/results/
history/receipts/approvals, destination binding and a suitable migration/rollback
plan. No migration is supplied or performed. Binary rollback across schema versions
is not a valid rollback process. See docs/architecture/application-contracts.md.

Existing owner previews and UI/CSS are untouched. Azure label export remains
unchanged and its seven generated shared-module adaptations still need broader
review. Inspection receipts and child-identity policies are not copied from that
client into the engine by this patch. Complete those reviews, missing independent
failure/receiving checks and Google/IBM native transfers before alpha.5. Four
offered increments/1-of28/owner0/unknown quality remain; no whole-system promotion.
