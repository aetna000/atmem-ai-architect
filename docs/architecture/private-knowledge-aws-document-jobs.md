# AWS per-file document execution

`enterprise_aws_jobs.py` now implements the task-definition contract and native
ECS controller. `enterprise_aws_objects.py` and `enterprise_aws_transfer.py` supply
conditional storage operations and trusted transfer stages. These are **not a
complete production composition**: private host-pool Terraform is now locally
qualified in `private-knowledge-aws-infrastructure.md`; full native application,
operator/artifact and generated private export wiring remain unfinished. No cloud account was accessed
in qualification and no new capability/default worker is enabled.

The design uses Linux EC2/ECS for this parser workload. Fargate requires `awsvpc`
and does not support per-container `disableNetworking`; substituting it would lose
the parser's required network restriction. See the
[AWS task definition reference](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html).
This choice does not move unrelated application components from their accepted
hosting platform.

The v2 configuration pins an immutable, operator-owned task-definition ARN and
revision. `enterprise-aws-task-template.json` is the shared static shape. The worker
has no registration, deregistration, definition discovery or definition deletion
operation. Before allocating intent or uploading bytes, DescribeTaskDefinition
must match the exact active revision, image digests, roles, commands, mounts,
network, capabilities and placement policy. Unknown nonempty configuration fails
closed; only inert native defaults are normalized, without changing the response.
The required native DescribeTaskDefinition IAM resource wildcard is a read-only
limitation, not authority to run another definition. See the
[ECS authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ecs.html).

Per-file request metadata and the acknowledged input ETag enter only bounded
DOCUMENT_JOB environment overrides on download/upload. The parser receives no
override, request environment, shell command, image, role or credentials. The task
definition contains no per-file metadata. This replaces the unreleased v1
per-file registration prototype; it is not a production migration or adoption.
The complete Terraform owner and worker permission composition remains unfinished.

The definition orders trusted download, isolated parsing and trusted upload. The
first two containers are nonessential and their dependents require successful
exit; the final uploader is essential. Marking an early stage essential would
stop the task when that stage exits. This follows the
[native dependency contract](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ContainerDependency.html).
Two separate task-scoped Docker volumes carry input and output. The parser gets
read-only input, writable output, read-only root, UID10001, dropped capabilities,
no-new-privileges, bounded temporary storage and disabled networking. The transfer
task role is distinct from the question worker and image-pull execution role.

The native API does not accept Docker's `none` logging driver. Omitted container
logging inherits the daemon default, so the dedicated host must set and verify a
`none` default. `EcsHostPolicy` now implements native ECS/SSM inspection rather than
accepting a scheduling label as proof. The fixed command document has no caller
parameters and its actual content, version and native SHA256 hash are bound before
submission. A fresh command invocation checks each connected selected host. The
probe checks daemon settings, running agent configuration, default bridge, builtin
seccomp and first-position IPv4/IPv6 metadata-blocking rules and forwarding hooks.
Docker inspection explicitly uses the local Unix socket, ignoring a saved remote
Docker context. It prints only a bound policy/cluster/boot observation.

The controller requires a short-lived typed host proof and further constrains
RunTask to those exact EC2 instance IDs. It verifies the final container-instance
identity before consuming output. Newly joined hosts cannot enter this launch
through the broader policy label. Missing, expired, unstructured or mismatched
proofs reject work before upload. This is point-in-time inspection of a trusted
host, not cryptographic kernel attestation or a guarantee against later root drift.
See [AWS LogConfiguration](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_LogConfiguration.html).

`enterprise-aws-host-infrastructure.mjs` emits the fixed SSM document and one
additive policy on the existing worker. It references an explicit existing parser
cluster and does not provision/adopt a host pool. The existing worker role is
looked up by name and its full returned ARN must match the supplied ARN, including
the path, before any policy is attached. A basename alone is not ownership proof.
SendCommand is limited to this
document and instances tagged with the exact policy fingerprint. No document
mutation, caller-selected shell command or Parameter Store read is granted.
GetCommandInvocation's native wildcard resource limitation remains explicit.
The native policy/model contract is documented in the
[SSM IAM guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/security_iam_id-based-policy-examples.html).

The controller binds the selected destination/worker configuration, requires the
owned host verifier before uploading, commits SQL cleanup intent before mutation,
uses a unique RunTask client token and fences every result with the live source
and execution lease. Exact cluster, task family, startedBy and task identity must
match; all three containers must exit successfully before text is consumed.

S3 operations specify the expected bucket owner. Before reading/writing/deleting,
they check native bucket placement and reject enabled or suspended versioning.
Writes require a missing key, explicit AES256 encryption and SHA256 checksum.
Downloads use the acknowledged ETag as a conditional token; the complete byte
digest/MIME/request binding is independently checked. ETag is not assumed to be a
content digest. Oversize, partial, encrypted-policy-mismatched or versioned
responses are rejected and streams are closed. The transfer CLI writes no document
content or traceback into logs.

Cleanup lists tasks using the exact startedBy identity in the selected cluster,
then verifies full cluster, task ARN and the owned task-definition family before
stopping or adopting anything. The native
[ListTasks contract](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ListTasks.html)
requires startedBy to be the only filter: do not add a family or desired-status
filter. Default desired RUNNING includes pending tasks. The foreground task ARN
is included even after it stops. Definitions are operator-owned and never deleted
by the worker. Both object deletions are attempted even after another failure.

An upgraded definition revision preserves the same cleanup target, so older owned
runs can be stopped after restart; foreground execution requires the exact current
pin. Changing the family, destination or bucket changes the recovery target and
requires draining the old target first. Failed cleanup withholds success and keeps
retry debt. Unknown stopped/stopping tasks may be absent from native listing;
uncertain acknowledgements retain settlement probes, and task-volume cleanup still
needs destination verification. See `private-knowledge-document-recovery.md`.
No maximum retention, termination or physical deletion SLA is established here.

`enterprise_aws_host_bootstrap.py` prepares only a new dedicated host: it refuses
foreign cluster/attribute ownership, preserves unrelated ECS/daemon configuration,
atomically writes private root-owned files and enforces local daemon/bridge/seccomp
settings before inserting first-position IPv4/IPv6 metadata blocks. It never
flushes unrelated rules. Twelve local contracts use real filesystem operations and
explicit daemon/firewall fixtures. Cloud-init/systemd wiring now comes from the private AWS compiler, with local
native unit verification; actual AMI/host qualification remains unfinished.

The probe compares firewall options semantically, preserving exact destination,
interface, action and first-rule constraints. A real owned Linux check uses only
new temporary unlinked chains in both families, verifies normal native option
ordering and rejects an earlier ACCEPT, then removes those new chains. It does
not modify existing forwarding or Docker chains, or prove metadata reachability.

The emitted substrate now restricts host identity, IMDS, image pulls, storage and
placement; native qualification must still verify those boundaries, retention and
recovery; never expose application/source/model credentials to the
parser host. Agent cleanup timing is not a strict deletion guarantee. Shared-kernel
EC2 containers are not a VM security boundary; the
[AWS IAM-role guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
explicitly discusses cross-task/instance credential risks. Host hardening and native
isolation checks remain acceptance requirements.

After repair of the owned test VM filesystem, the final AWS image passes
95 enterprise policies and 30 AWS contract tests (including
the original eight task-definition checks), plus 88 SQL tests on each PostgreSQL
version, and 16 host-verifier tests. Additional recovery runs contain three actual SQL/process-death tests and
eight offline contract checks per version. They exercise the installed image,
ordinary roles and a real abrupt child-process exit; ECS/S3 and host policy remain
explicit fixtures. Emitted stages also process real DOCX and scanned PDF in
restricted Linux, with actual CHOWN and separate read-only/writable volumes.

Two exact compiler packages run seven native Terraform mock plans each. Independent
consumption verifies the actual positive output and resolved command against the
runtime, including identical embedded Python and policy arguments; installed-image
checks also consume those native document bytes. Hostile source identifiers remain
literal evidence. The original forwarding-hook gap is preserved with its failing
regression and old probe source.

Native request checks use the pinned official botocore1.43.123 ECS/SSM models plus separate
enum recursion. The original invalid logging enum is preserved. None of these
results proves ECS scheduling, account IAM, host settings, native VM/task shutdown,
security acceptance or whole-project qualification. The rebuilt AWS image has not
been vulnerability-rescanned; existing security acceptance remains open.

Current static-task evidence: `specs/028-convergence-evaluation/evidence/20261111-private-aws-static-task-v1`. Earlier host/execution receipts are historical snapshots, not current-source acceptance.
