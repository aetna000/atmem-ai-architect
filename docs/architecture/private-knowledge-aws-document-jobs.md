# AWS per-file document execution

`enterprise_aws_jobs.py` currently emits an offline-validated task-definition
contract. It is **not an operational launcher**. The native controller, transfer
CLI, durable recovery integration, host provisioning/verification and generated
private export remain unfinished. It does not call AWS or enable a capability.

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

The future controller must also bind the actual destination/worker identity, use
conditional, owner-checked S3 byte operations, commit cleanup intent before remote
work, fence result consumption, handle lost RunTask/registration acknowledgements,
wait for task termination and recover task-definition/object cleanup after restart.
Provisioning must restrict host identity, IMDS, image pulls, storage, placement,
retention and recovery; never expose application/source/model credentials to the
parser host. Agent cleanup timing is not a strict deletion guarantee. Shared-kernel
EC2 containers are not a VM security boundary; the
[AWS IAM-role guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
explicitly discusses cross-task/instance credential risks. Host hardening and native
isolation checks remain acceptance requirements.

Eight offline tests validate the emitted request against the pinned official
botocore1.43.123 ECS service model. Separate enum recursion catches values the
SDK's ordinary parameter validator accepts. The original invalid logging enum is
preserved with the failed request source. This is structural and contract evidence,
not a launched task, native security verification or complete-project qualification.
