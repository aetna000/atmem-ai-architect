# Fixed AWS invoice operating jobs

These are generated definitions and commands, not evidence of a deployed service.
Obtain destination authorization before apply, publication or RunTask. Keep an
existing reviewed same-account regional SNS topic in operator_alert_topic_arn.
Its owner must authorize CloudWatch publishing and verify an actual subscribed
on-call route. If encrypted, the topic must use a compatible customer-managed KMS
key whose policy admits CloudWatch; the default alias/aws/sns key is not sufficient. This package does not adopt or modify the existing topic/policy.

1. Foundation: applications_enabled=false, operations_enabled=false,
   maintenance_enabled=false. Review/apply only when authorized; publish the
   scanned immutable runtime and parser images to the emitted ECR repositories.
2. Bootstrap definitions: operations_enabled=true, applications_enabled=false,
   maintenance_enabled=false, runtime_image set to the owned immutable digest.
   This creates fixed tasks and disabled schedules; it does not execute SQL.
3. From the authorized foundation state, write the nonsecret bootstrap request:

       terraform output -json operator_bootstrap_request > .local/bootstrap.json
       aws ecs run-task --cli-input-json file://.local/bootstrap.json

   Use the same reviewed AWS account/region. Retain the returned task ARN, wait
   for STOPPED and check operator exitCode=0 plus an initialized:true receipt in
   the initialize log stream. A successful RunTask response alone only admits
   scheduling; it does not prove SQL initialization. Failed start/nonzero exit
   events reach the private operator-failures queue. No task role, accounting
   credential, model or object authority is conferred on the operator container.
   The execution role resolves only the managed RDS admin password field, image
   and logs. The connection verifies the regional RDS CA/hostname. SQL transactions
   and an advisory lock protect owned retries; existing passwords are preserved.
4. Invite verified Cognito users and admit explicit application roles through
   invoice_operator.py membership as described in OPERATIONS.md. No invitation
   or sign-in silently grants reviewer/owner authority. Populate the accounting
   secret outside Terraform/source. Retain native membership/denial checks.
5. Release: applications_enabled=true, operations_enabled=true,
   maintenance_enabled=true. The review gate refuses application release without
   the operating definitions/schedules enabled. This flag does not prove step 3
   or 4 ran: retain their actual destination receipts before approving release.

Daily maintenance runs at 02:17 UTC. It removes at most twenty batches of 500
expired SQL operations, with separate transactions and exact account/namespace
ownership. Live execution jobs/leases refuse deletion. Table locks serialize
concurrent submissions, preserving new/young operations. Remaining backlog returns
nonzero; retry after inspecting count-only logs. Object lifecycle expiry remains
independent and asynchronous. No scheduler IAM role can launch the bootstrap task.

Hourly monitoring uses a read-only SQL transaction and emits scoped state counts.
Pending/approved work unchanged for two hours, expired execution leases, dead or
unknown outcomes and records overdue for cleanup by two days need attention.
These are operational starting thresholds, not a promised throughput/latency SLA.
Both jobs have a 15-minute process deadline; SQL waits/statements are bounded.

Scheduler invocation failures go to the encrypted seven-day failure queue with
bounded retries. Task failed-to-start/nonzero operator exits also reach that queue;
this matters because RunTask acceptance is not application success. Queue alarms
and missing-success-receipt alarms publish to the reviewed existing SNS topic.
Daily/hourly heartbeat alarms breach after two missing periods. Bootstrap failures
alarm as well; no bootstrap is scheduled. Operator logs retain seven days and do
not include document data, subjects, amounts or SQL/password exception text.

Test alert delivery, stopped-task routing, missed schedules, private SQL/TLS,
native secret rotation and effective IAM in an authorized destination. Cloud
availability, notification delivery and managed restore remain unverified by local
schema/mocks. Keep restore/quarantine/reconciliation isolated and explicitly paused;
daily cleanup does not authorize replaying uncertain external accounting effects.
