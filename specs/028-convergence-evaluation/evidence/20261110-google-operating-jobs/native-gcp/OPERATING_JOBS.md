# Google invoice operating jobs

Obtain authorization before account writes, apply, publication or RunJob. Fixed
operator jobs are not API/model tools. The existing project, verified staff and
notification channel are referenced, never replaced. Verify the existing channel's
actual on-call recipients and delivery. Review organization log placement/retention
and effective inherited IAM; this package does not rewrite existing logging sinks.
Operator receipts contain counts/status, not invoices, subjects or amounts.

Foundation: applications_enabled=false, operations_enabled=false,
maintenance_enabled=false. Publish reviewed immutable runtime/parser images into
the owned regional repository only when authorized. With runtime_image supplied,
set operations_enabled=true and keep maintenance/applications false. The three
fixed jobs exist; daily/hourly schedules remain paused.

As the separately authorized destination operator, preview the emitted command:

    python3 scripts/run-operator.py initialize

Then add --execute for the authorized destination. The helper reads nonsecret
Terraform outputs and invokes gcloud with exact project/region/name and --wait,
without shell interpolation, overrides or exposing OAuth tokens. Use maintain or
monitor for the other fixed jobs. Install/authenticate the reviewed Google Cloud
CLI beforehand. The exact operator_start_urls REST outputs are also available.
Do not use public invokers or application roles to launch privileged SQL work. RunJob acceptance is asynchronous: retain the actual
completed execution/exit status and initialized:true receipt before continuing.

The ops service account intentionally has separate cloudsqlsuperuser SQL authority.
API/worker IAM SQL users must already exist. Bootstrap verifies native IAM markers,
owned identities, exact schema/grants and scope, never creates a substitute native
IAM user or adopts unrelated roles. Managed Cloud SQL role mutation, native IAM and
effective privileges require destination checks; local PostgreSQL is not Cloud SQL.
Admit verified staff SQL memberships separately; IAP access alone is insufficient.
Populate the accounting secret outside Terraform/source and outside operator jobs.

Each job has one task, parallelism one, no native retry and a 960-second task limit.
Its operator waits up to 30 seconds on the pinned proxy's own loopback startup
endpoint, uses a 900-second work deadline and always calls the loopback shutdown
endpoint. Initial SQL connection transport failures retry at most three times with
fresh credentials; authentication/permission/schema errors do not. No insecure
remote connection, public SQL IP or configurable proxy URL is introduced. The
maintained proxy uses private IP/upstream TLS and a fixed instance. A failed shutdown
cannot emit an ok heartbeat; native task timeout remains the final failure bound.

Next enable maintenance_enabled=true while applications_enabled=false. Cleanup
runs 02:17 UTC daily, monitor at minute 7 hourly. The scheduler uses its own invoker
identity scoped to maintain/monitor only, OAuth, bounded retries and no bootstrap
or override/SQL authority. Its service agent has the required native role.
Manually run monitor and verify a real success metric AFTER policy installation/
modification: Google's absence policy does not arm from a never-written metric.
The two-hour monitor absence rule plus failures and hourly SQL retention-overdue
checks cover operating progress. No invalid 48-hour absence condition is emitted.
Native platform ERROR logs and count-only failed/attention/backlog receipts alert;
inspect execution history as well. Test failed scheduling/execution, first-sample,
missing runs and channel delivery before final applications_enabled=true release.

Daily cleanup is bounded to twenty 500-record transactions and refuses live jobs/
leases; younger/concurrent work is preserved. Original-object expiry is separate
and asynchronous. Restore/quarantine/reconciliation remain isolated and paused.
Local schemas/mocks and fixture SQL do not prove Cloud SQL IAM/TLS, scheduling,
metric/log ingestion, notification delivery or managed restore. Retain those actual
destination acceptance receipts; no production readiness is inferred from a URL.
