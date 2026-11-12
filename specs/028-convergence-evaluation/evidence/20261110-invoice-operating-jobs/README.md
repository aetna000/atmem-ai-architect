# Invoice operating jobs checkpoint

The shared fixed job entrypoint now implements initialize, bounded maintain and
read-only count-only monitor commands. Deployment/provider/scope validation precedes
connections. Private native secret injections become temporary owned 0600 files,
removed on exit; application/model/parser/action authority is rejected. Preview
never reads secret files or calls SQL/SDKs. A 15-minute process deadline and bounded
SQL waits constrain execution. Failures emit a generic code without driver values.

Actual local SQL verifies online expired-only maintenance: live doing queue jobs
and leases refuse deletion, competing new submissions wait for the operator lock
and survive, bounded batches report real backlog, and monitoring detects overdue
records without exposing payloads. Restore/reconciliation remain explicitly paused
and isolated. Native connection/deployment configuration was separated from the
HTTP/JWT adapter so jobs do not load staff authentication or HTTP components.

AWS emits three private fixed Fargate definitions, scoped RDS master-password-field
injection, separate execution authority and no task IAM role. Bootstrap is manual;
Scheduler can launch only maintenance/monitor. Schedules are disabled until the
post-bootstrap release flag; application release requires operations and maintenance
enabled. Daily cleanup/hourly monitoring have failed-invocation/dead-task queue
routing, missing-success alarms and an existing regional SNS route, whose owner must
verify policy/KMS/subscriptions. The package never adopts that existing SNS policy.
An exact nonsecret RunTask request and phased operating runbook are exported.

9 native mock plans and schema validation pass. The actual Linux image executes
three native-plan previews and real internally injected fixture SQL checks on PG17
and PG18: initialization/retry, monitoring, expired cleanup, preserving young work
and both runtime audit-deletion denials. This is NOT AWS authentication or native
scheduler/alert evidence. Exact API image startup/denial and five restricted queue
checks pass. 82 API/operator, 9 maintenance PG18, 307 JS and 208 server checks and
build pass. The build retains the known chunk-size warning.

The exact image inventory retains 47 high findings, zero critical and no reported
fixes in cached vulnerability metadata. This is not clean security or production
acceptance. Sources, receipts, native artifacts, review observations and raw logs are
preserved; manifest.json binds every evidence file. Private fixture files are absent.

Next: native operating wrappers for Azure/GCP/IBM, then whole state/Spec Kit/registry
integration and four complete medium invoice conversations. No complete medium case
is counted yet. Remaining families, full 28-case and held-out acceptance are pending.
No cloud operation, publication or deployment occurred.
