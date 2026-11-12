# AWS private parser infrastructure

The compiler in `src/enterprise-aws-infrastructure.mjs` now emits a new private
parser execution substrate. It composes the fixed host-verification module rather
than adopting an existing cluster or duplicating its command implementation. This
is not yet a complete private-assistant export or an advertised capability.

It creates a dedicated VPC, two private subnets and route tables, seven interface
endpoints and one S3 gateway endpoint, temporary no-history S3 storage, two immutable
ECR repositories, separate host/transfer/image-pull IAM roles, a fixed SSM command
and additive policies on the exact existing worker role. Actual immutable images
and a reviewed Amazon-owned ECS-optimized AL2023 x86_64 AMI enable a static task
revision and bounded standing EC2 pool. The worker role's full ARN, including its
path, must equal the native lookup; other policies and existing systems are kept.

Foundation switches default off for hosts and images. No synthetic published image,
AMI approval or ready runtime is emitted. Recommended AMI metadata is discovery;
the operator must review and pin the real ID. Native output stays null until both
switches are enabled. Foundation endpoints have standing charges even with hosts
off. Two m6i.large hosts and 40-GiB encrypted disposable root volumes are engineering
proposals requiring cost/load review, not accepted prices or throughput guarantees.

There is no NAT, internet gateway, public IP or SSH ingress. Host HTTPS reaches
interface endpoints and the regional S3 prefix list; the gateway policy restricts
objects to this temporary store and ECR's regional layer bucket. The isolated parser
has no network or credentials. Host/pull identities cannot access source/model/SQL
secrets through these policies. Existing inherited worker/account permissions still
need destination inspection. No cloud account or IAM simulator was used here.

Host cloud-init writes exact root-owned probe/bootstrap programs and systemd units.
ECS is masked while preparation changes the owned configuration; Docker restarts,
the guard verifies/installs metadata isolation, and ECS starts asynchronously behind
the guard dependency. A failed preparation/guard must not register a usable host.
The actual AMI, agent version, boot sequencing and rule reachability remain native
destination checks. Native systemd syntax/dependency verification used explicit
platform-service stubs; it did not install units or exercise an Amazon AMI.

Task definitions are owned by Terraform. The runtime checks the exact active task
revision and uses only trusted transfer environment overrides per file. IAM allows
RunTask only for that revision/cluster, PassRole only for transfer/pull identities,
and lifecycle inspection/stop only in the dedicated cluster. Native unscopable
read/transport actions retain documented wildcards. Task role trust is bound to the
same account and regional ECS service. Public authorization metadata independently
checks action, resource type and supported condition-key shapes; this is not proof
of account policy evaluation or functional sufficiency of every permission.

Upgrade by building/reviewing a new immutable artifact and draining old work before
host replacement. Fixed desired capacity is not automatic scaling. Automatic host
refresh/drain, native fault recovery and physical-erasure deadlines are not proven.
The ordinary durable reconciler and asynchronous age-one-day lifecycle fallback
remain distinct; versioning is not suspended or silently adopted on existing data.

## Observed qualification

Evidence: `specs/028-convergence-evaluation/evidence/20261111-private-aws-infrastructure-v1`.
Normal and hostile-identifier packages each pass ten credential-free plans with
AWS provider6.72.0. Independent verification consumes the actual positive plan:
45 resources, 43 IAM action occurrences, exact runtime configuration/task/SSM
command, source bytes and host-policy arguments. The installed AWS image consumes
both packages without network access. Five independent IAM regressions, native
systemd verification and all364 JavaScript tests pass.

Retained failures caught invalid disabled-task indexing, test validation dependency
handling, double-escaped cloud-init newlines, trust-policy expression escaping,
unknown mock network IDs and provider tri-state boolean representation. Fixes are
in the compiler/harness; client exports were not patched. Synthetic native mock
IDs and digests are fixtures, not published resources or account-plan evidence.

Reproduce with fresh `.local` directories using:

- `node scripts/qualify-enterprise-aws-infrastructure.mjs <out> [--literal-probe]`
- `.local/durable-runtime/bin/python -I scripts/verify-aws-document-infrastructure.py <out>`
- `.local/durable-runtime/bin/python -I scripts/qualify-enterprise-aws-bootstrap-units.py <out> --out <unit-evidence>`
- `.local/durable-runtime/bin/python -I scripts/qualify-enterprise-aws-pool-runtime.py <out> --out <image-evidence> --core-receipt <exact-AWS-core-receipt> --docker-host <owned-Unix-socket>`
- `.local/durable-runtime/bin/python -I tests/runtime/enterprise_aws_infrastructure_verifier_contract.py`
- `npm test`

## Reviewed primary evidence

[AWS ECS endpoints](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/vpc-endpoints.html)
require ECS, agent and telemetry private connectivity for EC2. Modern
[SSM transport guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/troubleshooting-ssm-agent.html)
uses ssmmessages; ec2messages is unsupported in newer regions, so it is not emitted.
The actual modern agent and regional endpoints still need destination verification.

[Official service authorization metadata](https://servicereference.us-east-1.amazonaws.com/v1/ecs/ecs.json)
and matching IAM/ECR/S3/SSM/message catalogs are pinned with URLs, dates and SHA256
in `tests/fixtures/providers`. The
[provider6.72.0 task implementation](https://github.com/hashicorp/terraform-provider-aws/blob/v6.72.0/internal/service/ecs/task_definition.go)
omits false autoprovision when expanding task-local Docker volumes; a reviewed
upstream source hash is retained. We learned the narrow behavior without copying
its implementation into the generated application.

## Remaining work

Compose full native API/worker/SQL/model/source, artifact build/configuration,
operator/monitoring/recovery and Spec Kit delivery. Validate that application hosting
can reach its sources, model, SQL and this isolated parser control/data boundary.
Complete Azure/IBM isolated launchers, preserve Google bindings, run full private
client briefs across all four providers, then remaining medium/hard families and
the final28/held-out matrix. Current image security acceptance remains open. No
whole-case, full export, account plan or deployment acceptance is claimed here.
