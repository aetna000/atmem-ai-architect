# AWS invoice workflow infrastructure

New private VPC/subnets, regional NAT, IAM-authenticated Multi-AZ PostgreSQL 17,
private versioned invoice bucket, invited/MFA Cognito users, separate API/worker
roles, a role-free isolated parser task, ECR repositories and regional TLS ingress.
The public Route53 zone and external accounting system remain existing references.

Run foundation first with applications_enabled=false. Build/scan/publish the exact
emitted runtime/parser images only after authorization. Bootstrap SQL logins/grants,
schema and staff memberships with the separate administrator secret; populate the
accounting secret outside Terraform state/source. Then review a plan enabling the
application release. Native platform secret injection becomes a private temporary
file; credential rotation requires an explicit workload rollout. Never put secret
values in tfvars, source, build context or command arguments.

Parser ingress is private HTTPS restricted to the worker security group. TLS ends
at its internal regional ALB; the target HTTP hop is inside restricted private
security groups. The parser has no task IAM role, data/model grant, secret injection
or outbound security-group rule. A short trusted root init container prepares only
the ephemeral temporary volume; processing containers retain nonroot image users.
No Docker daemon is installed in the worker. Verify actual platform isolation and
effective inherited IAM in an authorized staging environment before production.

The storage lifecycle expires current originals after 90 days and noncurrent
versions after one additional day; physical provider deletion is asynchronous.
Application payload access expires independently of physical cleanup. The emitted
OPERATIONS.md and invoice_operator.py implement scoped audit cleanup, restored
delivery quarantine and explicit completion reconciliation; schedule and monitor
the separate operator maintenance window before release. Seven-day encrypted database backups may
contain older data; review the stated backup/retention policy before deployment.
No static/mock check establishes an exact deletion deadline or cloud restore.

The single NAT, ALBs, managed database and continuously running tasks have fixed
cost drivers. Review actual regional rates, service/model availability and quotas;
no invented quote, price cap, throughput/latency SLA or deployment claim is made.
Infrastructure emission remains under qualification until the complete project,
operations, native account inputs and original full business brief are checked.
