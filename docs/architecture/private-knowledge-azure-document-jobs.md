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
The helper and protected ancestor provisioning are **not implemented yet**. No
export, readiness or installed-runtime receipt claims that this helper exists.

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

## Required next implementation

Implement temporary Blob storage with native managed identity, conditional reads
and create-only writes, bounded responses, no redirects and ARM-verified placement
and disabled retained history. Implement trusted host preparation/release and
independent label/deadline cleanup after interrupted preparation or node reboot.
Build the Batch controller, pool/agent/image/identity preflight and durable SQL
intent/recovery. Cleanup must verify release outcome, not infer erasure from an
accepted delete request. Preserve cleanup ownership across artifact revisions.

Generate dedicated private pool, native roles/network/storage/artifact/host
provisioning, and wire the approved native executor into the worker only after the
composition is tested. Complete the four-provider application/Spec Kit exports,
whole private cases, security/performance qualification and final 28/held-out
evaluation. No cloud operation, Azure agent test, complete export, security
acceptance or whole-project qualification has occurred here.
