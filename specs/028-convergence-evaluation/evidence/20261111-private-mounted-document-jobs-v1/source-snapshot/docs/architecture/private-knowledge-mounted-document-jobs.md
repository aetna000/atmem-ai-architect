# Private document jobs: bounded mounted transport

The owned parser now has a file-based mode for fresh per-file workloads. The
normal stdin/stdout CLI remains available for existing explicit local tools.
Native cloud launchers remain unfinished; this transport does not advertise a
new generator capability or qualify a complete private-assistant project.

## Contract

Run `python -I /app/enterprise_document_cli.py --job` as UID/GID 10001. Mount a
private read-only `/input` and a distinct private writable `/output`. Do not mount
application files, source credentials, model credentials, SQL credentials or a
cloud workload token. Select the exact independently reviewed parser image by
digest, not a floating tag. Each file requires a fresh workload and fresh mounts.

`/input/document` contains at most 10,000,000 bytes. `/input/request.json` contains
at most 2,048 bytes and exactly these fields:

```json
{
  "format": "enterprise-document-job-v1",
  "requestId": "<64 lowercase hex, random and unique per execution>",
  "sha256": "<SHA-256 of the exact document bytes>",
  "mediaType": "<canonical declared MIME type>"
}
```

The parser checks the complete request, actual byte digest and bounded regular
files. It refuses duplicate metadata keys, symlinks, FIFOs, reused input/output
directories, existing output files and malformed or partial parser responses.
Only the mounted output contains the extracted text. Successful output has the
same format/requestId, `status: "ok"`, and the complete `document` byte-bound
contract. Consumers must require successful process exit, then call
`enterprise_document_job.result` against the original bytes, MIME and requestId.
Neither an output file alone nor a matching requestId proves successful extraction.

Publication uses a private temporary regular file and an exclusive hard link to
`/output/result.json`, followed by fsync. It never replaces an existing result.
Both mounts must therefore have local POSIX file semantics; this implementation
does not claim direct compatibility with object-storage FUSE, Windows shares or
Kubernetes projected secret symlinks. A native transport may copy between scoped
storage and these private local mounts outside the untrusted parser.

The CLI prints only success or a bounded rejection code in mounted mode. This
prevents routine document content from entering logs; it does not constrain a
compromised native parser's ability to write stdout. The local qualification
launcher disables the Docker log driver as well as network access. Native cloud
launchers must independently contain log collection, network, identities,
resources and cross-file storage access; merely changing the CLI is insufficient.

## Current authority and cleanup

`CachedDecoder` passes its live company/job and native source check through
`DocumentExecutor.from_source` to an owned launcher. Launchers must check it
before releasing input, during waits and before consuming output, and stop their
owned workload after cancellation or revocation. The wrapper also checks before
and after extraction. The cache cannot publish a derivative after failed current
authority checks. Existing simple decoders retain before/after checks; they do not
thereby gain native per-file containment or cancellation during execution.

The test-only `LocalDocumentJobs` uses the owned qualification VM's Unix Docker
socket, exact image ID, no host mounts, fresh named volumes/container, network
none, disabled logs, read-only root and input, UID 10001, dropped capabilities,
no-new-privileges, bounded CPU/memory/PIDs/tmpfs/deadline and bounded result reads.
Its fixture volume initializer uses only root plus CHOWN, never parser execution.
Cleanup removes only this call's unpredictable owned names. Cleanup failure fails
the operation. It is not a Docker socket integration offered to production users.

## Provider research and remaining implementation

Primary documentation reviewed 2026-11-11 identifies candidate transport mechanisms,
not proven complete architectures:

- [AWS ECS environment files](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/use-environment-file.html)
  are read by the execution role. The
  [task role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
  is a distinct authority boundary. A parser must not inherit source/model/database
  or future-file access through a reusable task identity.
- [Azure Container Instances secure environment values](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-environment-variables)
  provide a platform injection option. This does not independently prove network,
  log, storage or managed-identity containment.
- [Google Batch container network blocking](https://docs.cloud.google.com/batch/docs/job-without-external-access)
  and [storage volumes](https://docs.cloud.google.com/batch/docs/create-run-job-storage)
  are candidates for a credentialless parser with a separate trusted transfer
  boundary. Mounted storage semantics and host/container IAM isolation still need
  verification. Cloud Run job secret access must not give one parser a reusable
  identity that can read other files' secrets.
- [IBM Code Engine trusted profiles](https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles)
  are optional and [secrets can be referenced by jobs](https://cloud.ibm.com/docs/codeengine?topic=codeengine-secret).
  Parser workloads must not receive the trusted worker's IAM authority or broad
  service bindings. These docs do not establish a safe per-file result channel.

Next implement and validate the concrete provider launchers and scoped transfer,
timeouts, cancellation, orphan recovery and IAM/Terraform composition. Retain
existing provider choices and deployment units. Then qualify the complete private
assistant and proceed to the remaining project families and final 28-project and
held-out evaluations. No cloud access or deployment is authorized by these local
checks.
