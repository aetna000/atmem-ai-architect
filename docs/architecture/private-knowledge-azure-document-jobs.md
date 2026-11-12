# Azure private document execution

Status: partial implementation, 2026-11-11. Not enabled in the native worker.

The generator's Azure execution contract now describes one Batch job per opaque
64-character file identity. An elevated trusted preparation task stages the file;
a non-administrative container task parses it; a trusted release task collects the
bounded result and removes private Docker volumes. The future controller must
explicitly terminate a job after observing its parser, wait for release completion,
then delete it. An empty job must not use `onAllTasksComplete=terminatejob`, which
could complete the job before its parser is submitted.

The parser disables native shared Batch data mounts with an explicit
`containerHostBatchBindMounts: []` and sets `workingDirectory=containerImageDefault`.
Microsoft documents that omitting this array mounts the entire node root; an empty
array prevents those mounts and requires a node agent newer than 1.11.11. The
contract separately requests no container network, read-only root, no capabilities,
no new privileges, bounded CPU/memory/processes, no Docker log driver and two named
per-file volumes. Input is literally mounted read-only. Credentials, document
metadata, source URLs and application packages are not passed to the parser.

Batch chooses a native non-admin task UID; the design must not assume image UID
10001. The locally tested staging fixture sets input files 0444, input directory
0555 and the fresh private output directory 0777. Parser output is created 0600.
Only that file's parser and the trusted transfer stage receive these volumes. A
trusted root collector needs only DAC_READ_SEARCH to read the native UID's output;
the parser receives no such capability. This permission scheme still requires
owned-pool/node checks and the native host helper implementation.

Preparation/release commands are fixed isolated Python bootstrap commands. They
verify an exact SHA256-bound root-owned, non-group/world-writable helper file under
`/opt/atmem/document-host/<sha256>/enterprise_azure_host.py`. There is no helper
download, shell expansion, arbitrary command field or mutable package default.
The standalone helper is now implemented and locally tested. Its native pool
installation, protected ancestor provisioning and reaper service are still
pending. No export or readiness receipt claims it is installed on a Batch node.

## Reviewed primary sources

- [Batch container isolation](https://learn.microsoft.com/en-us/azure/batch/batch-container-isolation-task), reviewed 2026-11-11; explicit empty mounts and agent requirement.
- [Preparation/release lifecycle](https://learn.microsoft.com/en-us/azure/batch/batch-job-prep-release), reviewed 2026-11-11; terminate/delete runs release tasks on applicable nodes. Reimaging and interrupted preparation require separate recovery.
- [Native job creation](https://learn.microsoft.com/en-us/rest/api/batchservice/jobs/create-job?view=rest-batchservice-2025-06-01); release completion is part of job completion; not evidence of successful byte erasure after a node is lost.
- [Official REST schema, API 2026-10-01](https://github.com/Azure/azure-rest-api-specs/blob/0b01059c3d95a84bc84ff16a4bb0fd10f66f3abd/specification/batch/data-plane/Batch/stable/2026-10-01/BatchService.json), pinned revision and SHA in `tests/fixtures/providers/azure-batch-2026-10-01-20261111.provenance.json`.

## Observed checks

Evidence: `specs/028-convergence-evaluation/evidence/20261111-private-azure-document-contract-v1`.

- Ten contract tests, including independent official schema traversal, native
  enum/unknown-field rejection, metadata separation, immutable artifacts, identity
  separation and rejected mount/network/cleanup substitution.
- Twenty-three local Docker checks. Actual emitted options ran real Word and
  scanned-PDF/OCR fixtures using UID 42424 rather than image UID 10001. Docker
  inspection confirmed network/root/capability/log/mount controls. Byte-bound
  consumer validation and expected content passed; created volumes were removed.
- The parser image is the existing qualified exact image
  `sha256:0e6089395cc36c96986ef500026af794dd07f2a8c97196e7c0df726fbe465c82`.
  Its receipt's source hashes were checked before reuse. No new runtime image or
  publication was implied. Local registry references and Batch UID are fixtures.
- An initial unsupported-MIME failure is preserved. The transfer contract now
  rejects unsupported canonical MIME before scheduling; octet-stream remains an
  allowed detection input under the shared parser contract.

## Temporary storage and transfer

The native temporary-Blob adapter and trusted transfer CLI are now implemented.
They are not installed in an emitted image or enabled in the worker yet.
`enterprise_azure_objects.py` selects one explicit managed identity client ID;
there is no default developer credential chain, SAS or storage account key.
ARM2025-06-01 observations bind the exact subscription/resource group/account/
container, same-region LRS/ZRS storage, private-only/HTTPS/TLS access, encryption,
disabled public/shared-key access, versioning, blob/container soft deletion,
restore/change feed and absent legal/immutability holds. Missing history flags
fail closed. Account policy changes are not transactionally locked by a preflight;
the generated dedicated account and role policy must restrict administrative
changes. Native cloud responses remain untested.

Blob2025-05-05 operations use fixed constructed HTTPS endpoints with redirects,
environment proxies and automatic content encodings disabled. Uploads use
`If-None-Match: *` and a native Content-MD5 transport checksum; this checksum is
not a security/content identity. The existing SHA256 request and consumer protocol
remains authoritative. Downloads use the acknowledged ETag as an opaque If-Match
token, enforce encrypted BlockBlob/no-version headers and bound actual length.
Delete includes snapshots only within the owned opaque per-file path; policy
preflight rejects retained history. A successful request alone is not proof of
cloud erasure or termination of every writer.

`enterprise_azure_transfer.py` validates a bounded metadata envelope, stages only
matching bytes into fresh separate directories, applies native-UID-compatible
permissions and validates both input and result before create-only upload. It
rejects aliases, symlinks, FIFOs, stale output and forged inner/outer byte bindings.
CLI failures contain a fixed message without document/provider-error contents.

Additional evidence:
`specs/028-convergence-evaluation/evidence/20261111-private-azure-document-transfer-v1`.
Fourteen scripted ARM/Blob checks, nine actual filesystem/transfer checks and ten
job-contract regressions pass. Twenty-six Linux checks execute the actual new
transfer CLI/adapter around Word and scanned-PDF/OCR parsing with UID42424 and
DAC_READ_SEARCH only in the trusted collector. The transfer sources are explicitly
injected into an existing qualified Azure core image; token/ARM/Blob responses
are offline fixtures. This is not an installed artifact, MSI or cloud test.
The earlier23-check parser receipt remains historical, bound to its original
qualifier hash; the new receipt binds the extended qualifier and current sources.
An initial metadata-ETag exception-type mismatch is retained and corrected at the
metadata boundary. No client export or runtime dependency lock was modified.

Additional primary references, reviewed2026-11-11:

- [Storage account observation, ARM2025-06-01](https://learn.microsoft.com/en-us/rest/api/storagerp/storage-accounts/get-properties?view=rest-storagerp-2025-06-01).
- [Blob service history properties, ARM2025-06-01](https://learn.microsoft.com/en-us/rest/api/storagerp/blob-services/get-service-properties?view=rest-storagerp-2025-06-01).
- [Container holds and access, ARM2025-06-01](https://learn.microsoft.com/en-us/rest/api/storagerp/blob-containers/get?view=rest-storagerp-2025-06-01).
- [Blob2025-05-05 version](https://learn.microsoft.com/en-us/rest/api/storageservices/version-2025-05-05), [Put Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/put-blob), [Get Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/get-blob), [Delete Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/delete-blob).

## Standalone host ownership and recovery

`enterprise_azure_host.py` now implements preparation, release and independent
expiry recovery using the standard library and Docker Engine API1.43 over a local
Unix socket. It does not download scripts or artifacts, parse documents, accept
shell commands or inherit Docker contexts/proxies. Preparation requires the
approved immutable images already present and observes a dedicated Linux Engine
with builtin seccomp, no live restore and no default log driver. Only the trusted
transfer stages use host networking, with an explicit transfer MI in metadata;
the parser remains network-disabled and receives no source/model/SQL credentials.
Native pool IAM/network restrictions remain required and unqualified.

The root entrypoint walks protected path ancestors without following symlinks,
checks ownership/modes/link counts/bounds, reads an exact protected policy and
verifies its installed source hash. It checks Batch account/pool/job bindings.
The file-state directory must be0700. A locked, fsynced, metadata-only intent is
committed before creating any native volume. Each volume has exact owner/request/
policy/side labels and a fresh nonce. Existing volumes or replayed job IDs are
not adopted. Root tombstones prevent replay; long-running metadata compaction
and capacity qualification are pending. A parser cannot mount these state files.

The worker/task compiler now emits parser labels that match this ownership model.
Cleanup validates every consumer and both volumes before deleting any resource.
A foreign consumer blocks cleanup and remains untouched. Lost create responses
are reconciled by known per-file volumes; timeout/still-running jobs can be
stopped only after matching artifact, user, mount, isolation and ownership checks.
Transfer polls use monotonic time; durable expiry uses the node wall clock and
is an operational fallback, not a strict retention SLA or offline-node erasure
claim. The helper does not erase cloud Blob bytes; the controller/SQL ledger must
settle remote writers before removing those objects.

The stable cleanup owner excludes artifact revisions but includes the native
destination and registry. Root-owned state retains each original policy/artifact
binding, allowing a current reaper to remove an old artifact's owned resources
without adopting a different destination. Release requires its original transfer
metadata/image/helper binding. Failed staging/upload never promotes publication;
successful publication is recorded before removing its file volumes. A process
that dies between upload acknowledgement and state recording remains uncertain
until controller recovery; the helper does not invent success.

### Cleanup acknowledgements for controller recovery

The host now publishes an exact metadata-only
`enterprise-azure-document-cleanup-v1` acknowledgement after all per-file native
containers/volumes have been removed. It contains only format, opaque request ID,
stable owner fingerprint and `cleaned: true`. It is not a parser-success receipt,
an architecture validation report, or proof about an offline node that has not
run cleanup. The controller must still verify the original task, source/company
guard and complete byte-bound result before accepting an answer.

The standalone root publisher uses the native VM IMDS endpoint with an explicit
transfer managed-identity client ID, bounded responses and a fixed Blob host/path.
It forwards no token to IMDS and no document bytes to either service. Blob writes
are create-only with transport checksum/encryption checks. After a lost write
acknowledgement, it reads and accepts only the exact existing receipt. Redirects,
duplicate headers/JSON fields, compression, oversized responses, expiring/wrong-
audience credentials, retained versions and mismatched owners fail closed.

Root state v2 separates physical cleanup from acknowledged receipt delivery.
Failed delivery leaves a durable pending flag; the reaper retries even before
ordinary expiry. Legacy v1 state is ownership-checked, rechecked against the
Engine, then upgraded and acknowledged. No missing receipt is invented. Ordinary
worker byte APIs reject receipt creation/deletion; they can fetch and strictly
validate a bounded encrypted/unversioned receipt, distinguishing missing from
permission/provider failures. This API separation is not cryptographic isolation
between trusted VM processes: Microsoft documents managed identity as a VM-level
security boundary. Only the approved transfer identity belongs on this dedicated
pool; native IAM/pool verification remains required.

Receipts stay until the generated metadata lifecycle expires them, preserving
idempotence during acknowledgement loss. That lifecycle and native IAM grants are
pending infrastructure deliverables. A receipt is not authorization to delete a
running Batch job blindly. The controller must stop/wait for native work, settle
uncertain creation and check the cleanup barrier before retiring source/result
objects and SQL debt.

### Native API and original-job observation

`enterprise_azure_batch_api.py` now implements fixed owned Batch endpoints and
explicit worker MI authentication. Its typed methods emit the pinned native
job/task shapes, observe only the owned pool/nodes/jobs/task/release status and
request termination/deletion without forcing node acknowledgement. It cannot
mutate pools/nodes, list arbitrary jobs, read task files or follow caller URLs.
ARM observation checks exact account/subscription/region/endpoint, provisioned
state, private-only access and AAD-only authentication. No HTTP202 response claims
termination or deletion completion. Full pool verification and controller
orchestration are not implemented by this transport.

Native job metadata now retains the original parser, helper and worker bindings,
allowing recovery even if task creation never completed. `recover_job` reads the
bounded original native metadata, reconstructs the exact historical job contract,
checks its full fingerprint/root commands and preserves the current stable
destination/registry boundary. It never executes native job text or grants
permission to launch an old artifact. Duplicate/malformed metadata and changed
destinations are rejected. Only documented name/value array order is normalized;
boolean/integer aliases cannot weaken control values.

Additional evidence:
`specs/028-convergence-evaluation/evidence/20261111-private-azure-cleanup-receipts-v1`.
75 component/regression tests pass:19 host/process death,9 producer/consumer wire,
6 original-job recovery,7 fixed Batch API,10 job schema,14 Blob,9 transfer and1
qualifier regression. A fresh21-check native Engine/build run passes with receipt
delivery represented by an explicit offline sink that checks real native volume
absence. Root IMDS/Blob wire requests are separately scripted; no cloud identity
or Batch account was contacted. Both native runs and their exact historical
source/context bindings are retained. No production runtime image, worker
admission, security or complete-project status is promoted.

Additional reviewed sources2026-11-11:

- [Native VM token protocol and VM-level security boundary](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token), API2018-02-01 with explicit client ID.
- [Batch authentication](https://learn.microsoft.com/en-au/azure/batch/batch-aad-auth), explicit `https://batch.core.windows.net/.default` scope.
- [Batch account observation](https://learn.microsoft.com/en-us/rest/api/batchmanagement/batch-account/get?view=rest-batchmanagement-2025-06-01), ARM2025-06-01.
- Pinned Batch2026-10-01 schema above: job/task create201, terminate/delete202; the optional `force` flag is not requested. Data-plane pool creation does not contain the identity field exposed by pool observation. The infrastructure compiler must use the management-plane pool/identity contract, rather than copying response properties into a data-plane create request.

Evidence:
`specs/028-convergence-evaluation/evidence/20261111-private-azure-document-host-v1`.
Seventeen host/true-process-death checks, one qualifier regression and the previous
ten job/fourteen Blob/nine transfer tests pass (51 tests). Twenty-one native
Engine/build checks pass, including six protected root CLI/filesystem checks in
Linux, installed transfer-source hashes, real Word/scanned-PDF OCR, byte-bound
upload, actual process death after native volume creation, stuck-parser expiry
and preserved unrelated consumers/volumes. Final native owner-label queries found
no remaining containers or volumes from this helper namespace.

The native test uses a qualification-only image containing the installed current
transfer modules, an offline HTTP wrapper and synthetic fixtures. It is not a
production artifact. ACR identities, Batch agent/UID, ARM/MI responses and the
daemon default-log observation are explicit fixtures. The Engine sandbox fields,
containers, volumes and process-death cleanup are real. Root filesystem checks use
actual UID0/protected Linux paths with an explicit no-Engine fixture; the Engine
integration uses a local-user state-directory fixture. These do not prove the
native pool image/agent, root service installation, cloud permissions, security
or whole-project behavior.

The first native run exposed a list-versus-inspect bug in the qualifier. Preserve
its failed receipt and original source, the precise repair regression and the
label-bound recovery of its leftover owned job. Successful intermediate runs are
retained with original qualifier/host/test bytes when their hashes changed. The
final receipt binds the current sources. Context ZIPs preserve exact build inputs
and hashes without changing upstream bytes.

Primary references, reviewed2026-11-11:

- [Docker Engine API1.43](https://docs.docker.com/reference/api/engine/version/v1.43/) for local container, image, volume and inspection operations; actual owned Engine29.5.2 exercised the compatibility API.
- [Batch runtime environment bindings](https://learn.microsoft.com/en-us/azure/batch/batch-compute-node-environment-variables); native paths are implementation details, so no Batch data path is constructed or remounted.

## Required next implementation

Build the Batch controller, pool/agent/image/identity preflight and durable SQL
intent/recovery. Add root-policy/helper installation and reaper service/timer to
the generated dedicated pool. Test release acknowledgement/outcome and native
deletion/uncertain creation; do not infer cloud erasure from an accepted delete.
Use a separately bound native pool definition/installation contract so its hash
does not create a circular dependency through the existing14-field host/job
configuration. Verify all ready nodes' startup outcome and agent version before
source upload; preserve original job bindings and cleanup receipts across
artifact/worker revisions. Never delete Blob data while any root writer remains
unsettled. Implement metadata lifecycle and replay-tombstone capacity management.

Generate dedicated private pool, native roles/network/storage/artifact/host
provisioning, and wire the approved native executor into the worker only after the
composition is tested. Complete the four-provider application/Spec Kit exports,
whole private cases, security/performance qualification and final 28/held-out
evaluation. No cloud operation, Azure agent test, complete export, security
acceptance or whole-project qualification has occurred here.

Final hardening also rejects unsupported HTTP methods before token acquisition,
closes the credential if session cleanup fails and sanitizes CLI cleanup failures.
The earlier successful run is retained with all four drifted source files restored
byte-for-byte against its recorded hashes in `initial-qualified-sources/`. The
`linux-transfer-hardened/receipt.json` binds the final current sources;26 checks pass.
