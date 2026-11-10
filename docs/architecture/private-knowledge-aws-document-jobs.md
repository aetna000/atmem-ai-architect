# AWS per-file document execution

`enterprise_aws_jobs.py` now implements the task-definition contract and native
ECS controller. `enterprise_aws_objects.py` and `enterprise_aws_transfer.py` supply
conditional storage operations and trusted transfer stages. These are **not a
complete production composition**: host provisioning/verification, Terraform and
generated private export wiring remain unfinished. No cloud account was accessed
in qualification and no new capability/default worker is enabled.

The design uses Linux EC2/ECS for this parser workload. Fargate requires `awsvpc`
and does not support per-container `disableNetworking`; substituting it would lose
the parser's required network restriction. See the
[AWS task definition reference](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html).
This choice does not move unrelated application components from their accepted
hosting platform.

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
logging inherits the daemon default, so the future dedicated host must set and
verify a `none` default before advertising its policy fingerprint as an ECS
placement attribute. A matching attribute alone does not attest host settings.
The controller must reject missing/stale host evidence before sending documents.
See [AWS LogConfiguration](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_LogConfiguration.html).

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

Cleanup discovers both desired RUNNING and STOPPED tasks for the exact family,
checks ownership before stopping, polls for termination, deregisters/deletes owned
task definitions and attempts both object deletions even after another cleanup
failure. Accepted task-definition deletion is not a claim of immediate native
metadata erasure. Failed cleanup withholds success and retains retry debt; uncertain
acknowledgements retain the shared ledger's settlement probes after restart. See
`private-knowledge-document-recovery.md`. Native listing is eventually consistent;
local fixture evidence does not establish a maximum retention or termination SLA.

Provisioning must still restrict host identity, IMDS, image pulls, storage, placement,
retention and recovery; never expose application/source/model credentials to the
parser host. Agent cleanup timing is not a strict deletion guarantee. Shared-kernel
EC2 containers are not a VM security boundary; the
[AWS IAM-role guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
explicitly discusses cross-task/instance credential risks. Host hardening and native
isolation checks remain acceptance requirements.

The AWS image passes 95 enterprise policies and 25 AWS contract tests (including
the original eight task-definition checks), plus 88 SQL tests on each PostgreSQL
version. Additional recovery runs contain three actual SQL/process-death tests and
eight offline contract checks per version. They exercise the installed image,
ordinary roles and a real abrupt child-process exit; ECS/S3 and host policy remain
explicit fixtures. Emitted stages also process real DOCX and scanned PDF in
restricted Linux, with actual CHOWN and separate read-only/writable volumes.

Native request checks use the pinned official botocore1.43.123 model plus separate
enum recursion. The original invalid logging enum is preserved. None of these
results proves ECS scheduling, account IAM, host settings, native VM/task shutdown,
security acceptance or whole-project qualification. The rebuilt AWS image has not
been vulnerability-rescanned; existing security acceptance remains open.
