export const INVOICE_OPERATIONS=`# Invoice workflow operations

This is a private staff application. The generated API and worker SQL identities
cannot create accounts, admit staff, erase audit history or perform operator repairs.
Keep the schema-owner credential separate. No command below authorizes deployment.

## Bootstrap and staff access

Run Terraform foundation with applications_enabled=false. Review the actual account,
regional availability, costs, private network access and provider identity settings.
Supply the real accounting endpoint, scope and native secret outside Terraform state.
Build, scan and publish the emitted API/worker and parser images when authorized;
pin their exact digests in the emitted repositories before enabling applications.

Create a private .local directory (mode 0700), and keep all operator input files mode
0600 and outside source control. Run the operator from the emitted application
directory, using a Python 3.13 environment installed with requirements.lock hashes.
The operator needs an approved connection path to the private native database.
Never expose PostgreSQL publicly to make bootstrap easier.

operator-connection.json has exactly these fields:
host, port (integer), dbname, user, passwordFile, caFile.
The password/token and reviewed native PEM CA are absolute separate file paths.
There is no inline password, insecure TLS option or arbitrary connection string.
AWS includes rds-global-ca.pem plus its pinned public-source receipt; verify native
CA availability for the selected database and update/rebuild before CA expiry.
IBM supplies its database-specific CA and separately provisioned SQL passwords.
Azure's operator must be authorized for native Entra mapping in postgres as well as
schema administration in the application database. Google native IAM SQL users must
exist before the separate schema/grant step. Short-lived tokens must remain valid
for the bounded operator action; the tool does not silently acquire extra privilege.

operator-deployment.json has exactly: provider, deploymentId (UUID), accountId (UUID),
namespace (invoice), bindings (api and worker), tenantId (Azure UUID, otherwise null).
Each binding has name and principal; Google additionally has created_by_package:true.
Use exact Terraform outputs/native identity subjects, never guessed display names.
AWS emits the complete nonsecret operator_deployment output. With an approved
foundation and private connection available, retain that output in the private file.

Preview (no database connection or write):

    python -I invoice_operator.py initialize --connection-file .local/operator-connection.json --deployment-file .local/operator-deployment.json

Add --execute only for the reviewed authorized destination. Initialization creates
owned native login mappings, the exact version-1 schema/queue and restricted grants.
It refuses to adopt an unrelated role or schema. Re-running the exact owned bootstrap
is supported; a changed schema requires a reviewed migration, not reinitialization.
IBM initialization additionally reads --input-file with apiPasswordFile and
workerPasswordFile pointing to private strong passwords; never rotate existing
owned passwords implicitly. Roll out credentials explicitly when rotating them.

Membership uses --input-file containing subject (verified native login subject),
roles (explicit array of user/reviewer/supervisor/owner), active (boolean):

    python -I invoice_operator.py membership --connection-file .local/operator-connection.json --deployment-file .local/operator-deployment.json --input-file .local/member.json --execute

Inviting/signing in at the native identity service does not automatically grant
application membership. Ordinary staff get user; three designated reviewers get
reviewer. Revocation uses active:false; role replacement is explicit. Native JWT
expiry and live SQL membership are different boundaries. Test both at the destination.

## Ninety-day retention

The invoice API and processing stages refuse payloads whose creation time is outside
the 90-day retention window, including data recovered from old backups. Private-store
lifecycles remove original objects separately; version/noncurrent deletion and native
provider deletion are asynchronous. Backups may retain expired data for the stated
backup window. This is not an exact physical-deletion deadline or legal-retention SLA.

AWS and Azure emit fixed operating jobs and schedules in OPERATING_JOBS.md. Other native
operator job adapters remain under qualification; do not assume those schedules
exist. The shared job entrypoint supports preview (without --execute), initialize,
maintain and monitor using the emitted owned metadata and separate operator identity.
It is never an API/model endpoint.

For the manual CLI maintenance path, pause uploads/API and workers, allow bounded
work to settle, then run:

    python -I invoice_operator.py purge-expired --connection-file .local/operator-connection.json --deployment-file .local/operator-deployment.json --execute --confirm-workloads-stopped

It removes at most 500 expired operations, their historical suggestions/audit and
owned queue notifications per transaction. Repeat while moreMayRemain is true.
Active queue jobs/live leases cause rollback; settle them before retrying. Other
accounts/namespaces, staff memberships and young records are preserved. Retain the
count-only maintenance receipt and alert on failure/overdue runs. The fixed
maintain job additionally bounds a whole execution to twenty 500-record batches,
reports remaining backlog nonzero and uses the same live-job/lease/ownership guards
for online expired-only cleanup. Concurrent young submissions are serialized by
transaction locks and preserved. Restore/reconciliation still require the isolated
paused boundary. See the provider-specific native job definitions for scheduling;
a script file alone does not establish that a schedule exists.

Deduplication is scoped to the retained operation lifetime. Do not promise unlimited
historical deduplication after the client-directed 90-day payload/audit deletion.
Destination operators must independently retain the idempotency identity as required
by their accounting contract. Do not clear an unknown outcome to resend it.

## Backup, restore and uncertain deliveries

Review native managed backup retention, encryption, restore region and current
provider procedures. Restore to an isolated new database/endpoint with API/workers
stopped. Do not point running workers at a restored snapshot: the accounting service
may have accepted deliveries after that snapshot's recovery point.

With private operator files explicitly pointing to the isolated restored database:

    python -I invoice_operator.py quarantine-restore --connection-file .local/restored-connection.json --deployment-file .local/operator-deployment.json --execute --confirm-workloads-stopped

Repeat while moreMayRemain is true. The tool fences restored approved/in-flight
deliveries as unknown, preserves approval hashes and clears stale queue notifications.
Interrupted extraction leases are fenced back to pending; the normal worker rebuilds
those notifications after expiry cleanup. This avoids retaining a restored doing
job forever or restarting an old external delivery. Attempt limits are preserved.
The stopped-workloads flag is an operator assertion, not proof that cloud workloads
were stopped. Purge expired restored records before reopening. Reapply reviewed native
runtime identity grants/membership as appropriate; verify current revocations and
object versions. Exercise read, denied access, fresh extraction and same-key behavior
on an isolated synthetic fixture before cutover. Keep old endpoints for rollback;
never dual-run workers on divergent databases. A local logical restore test does not
prove native PITR, object recovery, production RPO/RTO or destination availability.

For each uncertain delivery, independently query the existing accounting system by
operation ID and payload digest. If it confirms completion, store a private JSON
receipt with operation_id, payload_sha256, external_id and accountable operator:

    python -I invoice_operator.py reconcile-completed --connection-file .local/operator-connection.json --deployment-file .local/operator-deployment.json --input-file .local/verified-receipt.json --execute --confirm-workloads-stopped

The tool checks exact ownership/state/approval integrity and records the supplied
receipt without making an external request. It does not verify the human's accounting
lookup. A missing receipt is not permission to resend. Automatic same-key replay needs
the scoped, expiring destination-contract review described in the worker configuration.
Never rewrite an approved payload, endpoint, account or idempotency key for a retry.

## Monitoring and release checks

Alert on stale pending/approved work, dead/unknown outcomes, repeated parser/model
failures, storage/database growth and failed retention windows. Healthz means process
alive; it does not establish database/model/destination readiness. Keep payloads,
credentials and document text out of telemetry. Scale worker/parser capacity together
after throughput/quota tests. Before production, qualify native sign-in/token expiry,
workload IAM, private ingress, TLS, native storage versions, actual model quality,
external accounting idempotency and restore/cutover with authorized destination tests.
`;
