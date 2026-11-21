# Google private-document job adapter

The native controller, object adapter and two trusted transfer commands are
implemented and locally tested. This is an unfinished provider composition, not
a registered private-assistant capability or an account-qualified deployment.
The other three provider launchers and the complete 28-project evaluation remain
required. No existing application, company sign-in or document source is replaced.

## Ownership and execution

`enterprise_google_jobs.GoogleBatchDocuments` implements the guarded execution
port consumed by `DocumentExecutor.from_source`. Calling it without a live source/
company/job guard is rejected. Its configuration is owner-supplied deployment
data, never a browser/model-selected endpoint. It requires a destination project,
region, private temporary bucket, separate worker/transfer-VM service accounts,
private network/subnet and exact regional parser/transfer image digests. A shared
worker/VM identity, floating or cross-project images, malformed names and a subnet
outside the selected region are rejected.

Each request uses an unpredictable fresh identity. The controller writes one
native GCS object with a create-only precondition, retains its exact generation,
then creates one Batch task without retries. The three foreground runnables are:

1. The trusted download CLI uses the VM identity to read that generation and
   verify the input digest. It prepares a private local POSIX input/output tree,
   using root plus CHOWN only to hand files to UID/GID 10001, then exits.
2. The immutable parser runs as UID/GID 10001 with read-only root/input, a bounded
   tmpfs and writable per-file output. Its native Batch network-blocking field is
   set. No source/model/SQL credentials, worker identity, secret variables, image
   streaming, background listener, FUSE or implicit extra mounts are requested.
3. Only after parser success, the trusted upload CLI rechecks the complete
   byte/MIME/request result contract and uploads a create-only result. It reads the
   local work tree read-only and cannot overwrite an earlier result object.

The controller requires the exact job to report success before fetching and
validating its output. Guards surround upload, job submission, waiting and result
consumption. Failed, timed-out, revoked or malformed work does not yield text.
Finally it deletes only its unpredictable job and two object names; it waits for
the returned deletion operation and withholds success if cleanup fails. A lost
creation acknowledgement still takes this cleanup path. An initial failed guard
makes no remote call.

The task has no external VM IP, selects the same region, explicitly chooses the
transfer VM identity and blocks project SSH keys. Docker log collection is disabled
for every runnable. The official Batch value `DESTINATION_UNSPECIFIED` disables
preserved job logs; `NONE` is not a valid destination enum. Image streaming is not
enabled because the documented streaming path ignores container isolation options.

## Contract evidence

The public [Batch discovery document](https://batch.googleapis.com/$discovery/rest?version=v1)
is pinned in `tests/fixtures/providers/google-batch-v1-discovery-20261111.json`,
revision `20261103`, SHA-256
`5d1d75cf13459b7099d00250db786c13edea9cabb6852b32c521cbd16afdc2f6`.
Its adjacent provenance file records URL and review date. A generic independent
schema walker checks emitted field names, types, enums and read-only fields.
The [native job reference](https://docs.cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs)
documents runnable order, explicit mounts and network blocking. This is contract
evidence, not evidence that those controls have run in a real destination account.

Sixteen focused tests exercise configuration/schema/isolation fields, exact native
HTTP shapes, redirects/error bodies/limits, immutable object reads, source changes,
live revocation, lost acknowledgements, wrong results, deadlines and cleanup errors.
The clean Google dependency image runs all 95 enterprise policies and 88 actual
SQL/crypto/queue/operator checks on each owned PostgreSQL 17 and 18 fixture.

`qualify-enterprise-google-jobs.py` independently executes the emitted three-stage
sequence for actual DOCX and scanned PDF files. The real transfer CLI and file
ownership changes run in separate restricted Linux containers; the real isolated
parser and consumer validate the uploaded bytes. Native Google HTTP is an explicit
fixture; the local transfer containers also have network disabled. This does not
exercise the Batch agent, VM identity, private Google networking or actual GCS.

## Remaining work before integration and qualification

- Wire reviewed runtime configuration and complete parser artifact provenance into
  the generated private worker; preserve provider/project/region ownership. No
  production default worker command or public capability is enabled by this module.
- The parser-substrate Terraform and exact runtime-output consumption are now
  locally qualified; see `private-knowledge-google-infrastructure.md`. Complete
  application/operator hosting and destination validation of encryption, retention,
  routing/DNS, IAM and artifact provenance. The controller is bound to the selected
  runtime provider/project/region/worker identity; its configuration is immutable.
- Durable metadata-only orphan tracking, fenced cleanup retries and a separate
  worker reconciliation loop are now locally tested, including abrupt process
  death; see `private-knowledge-document-recovery.md`. Complete operator monitoring,
  old-target draining and strict retention/backup verification. The 24-hour
  uncertain-creation settlement probes are not a hard raw/result retention SLA.
- Verify native account semantics when authorized: Batch metadata isolation,
  container flags, transfer identity scope, job/VM termination, startup duration,
  cancellation, quotas and residency. A deletion operation receipt does not by
  itself demonstrate VM reclamation or continuous permission revocation.
- Measure cold execution against the existing cache lease and question deadlines;
  the controller currently bounds its wait to 140 seconds, task run to 160 seconds
  and cleanup polling to another 30 seconds. These are enforced engineering limits,
  not a measured production latency promise or accepted business SLO.
- Complete the remaining cloud launchers, security remediation/review, private
  project exports and full medium/hard/final-28/held-out qualification. Existing
  source freshness, current-context checks, audit and key/recovery obligations stay
  in scope.
