# Azure invoice operating jobs

Obtain authorization before destination writes, publication, apply or job start.
The emitted native jobs are fixed trusted operator tools, not API/model endpoints.
Azure job start accepts an execution template that can override image/command/env.
Treat start permission as access to the job's available managed identity. Never
grant job start/contributor/operator or listSecrets rights to the product, end users,
worker, parser or an untrusted automation identity. This package assigns none.

Foundation: applications_enabled=false, operations_enabled=false,
maintenance_enabled=false. Review regional availability, model/version, identity,
costs and existing operator_action_group_id. No existing action group or its routes
are adopted or modified. Verify its actual notification recipients and delivery.
Azure Monitor and resource-specific log tables are used; diagnostic routing includes
both console and system logs. Logs retain 30 days, separate from 90-day invoices.
Provider-managed state must remain private/encrypted; do not publish workspace keys.

After authorized build/scan/publication of the immutable runtime image to owned ACR,
set operations_enabled=true with applications_enabled/maintenance_enabled=false.
All three jobs are Manual. The pull identity has lifecycle None; only the separate
PostgreSQL Entra administrator identity has lifecycle Main. There is no password,
accounting secret, model, object access or HTTP ingress on these jobs. The exact
operator identity and login bind token acquisition to the managed database.

Start initialize as the trusted destination operator:

    az rest --method post --url "$(terraform output -raw operator_bootstrap_url)" --body '{}'

The shared core maps owned API/worker principals in postgres, then initializes
the application schema/grants/account in invoice. Check completed execution status,
exit code and initialized:true log receipt; start acceptance alone proves neither.
Admit verified staff subjects/roles using the separate membership CLI/runbook.
Do not infer reviewer privileges from Entra app access. Keep accounting secret
population separate from this SQL-only operator identity.

The nonsecret operator_start_urls output gives the exact remaining start endpoints;
call them with an empty JSON body as above. Do not override image/command/template.
Start maintain and monitor manually and check count-only receipts and both native
log tables. Query files are in monitoring/. Validate their ownership filters against
actual JobName/replica fields at the destination. Alerts are initially unvalidated
while fresh tables do not yet exist. Enabling maintenance_enabled makes ARM query
validation mandatory; a missing/incorrect table/query must block release, not be
silently skipped. Log ingestion/diagnostic activation can be delayed. Verify actual
queries and an action-group test notification before enabling scheduled release.

Release with operations_enabled=true, maintenance_enabled=true and
applications_enabled=true. Bootstrap stays Manual. Maintain runs 02:17 UTC daily;
monitor at minute 7 hourly. Completion/parallelism is one, native retry is zero and
replica timeout is 900 seconds. The shared process deadline and SQL statement/lock
bounds apply as well. Scheduling does not prove native IAM/SQL/network/alerts worked.

Daily expired-only SQL cleanup is bounded to twenty 500-record transactions and
refuses live execution jobs/leases. New/young operations survive; original-object
expiry is a separate asynchronous lifecycle. Monitoring is a read-only count-only
transaction. Two hours of missing monitor receipts and 48 hours of missing cleanup
receipts alert, along with failure/attention/backlog and platform warnings/errors.
These are explicit operating defaults, not promised availability or a client SLA.
No KQL engine or Azure Monitor ingestion/notification execution is proved by local
provider schemas/mocks. Retain actual destination acceptance before production.

Restore/quarantine/reconciliation still require an isolated paused destination.
Never use daily maintenance to reset or resend unknown accounting side effects.
