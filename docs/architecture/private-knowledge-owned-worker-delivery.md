# Owned worker configuration and application source delivery

`enterprise_worker.py` now supplies a dedicated worker entrypoint. It reads an
exact bounded `enterprise-document-executor-v1` envelope, checks provider/parser
revision, constructs only the implemented native adapter and binds the destination
and existing worker identity before source/encryption/SQL work. The full runtime
then attaches its durable document ledger and recovery loop. AWS/Google loading is
implemented; Azure/IBM native execution remains unfinished and never falls back.

Deployment metadata uses `ENTERPRISE_DEPLOYMENT_JSON` or an absolute
`ENTERPRISE_DEPLOYMENT_FILE` mount. Worker configuration uses
`ENTERPRISE_DOCUMENT_EXECUTOR_JSON` or `ENTERPRISE_DOCUMENT_EXECUTOR_FILE`. Exactly
one source is accepted, with32-KiB UTF-8 bounds, duplicate/nonfinite JSON rejection
and the existing strict schemas. No parser executable, plug-in import or arbitrary
endpoint comes from these values. Metadata is compiler/operator input, not a chat
request. The API never reads the executor configuration or constructs inference.

The source inventory in `enterprise-application-manifest.json` now drives both
clean-image qualification and `enterpriseApplicationFiles`. Each provider gets its
own reviewed dependency lock and the identical API/worker/operator implementation.
AWS also receives its public RDS CA. Explicit Docker context whitelists exclude
unreviewed extra files. Separate parser/PDF/OCR source, Java, hashes and recipes are
supplied outside the credentialed application context. This increment byte-checks
those recipes; it does not rerun their unchanged native parser qualification.

The full hosting compiler must provide a private writable ephemeral `/tmp` for
native environment-to-file secret materialization when using a read-only root.
Qualification uses a64-MiB tmpfs; this is not proof of a destination mount. File-only
platform injection can avoid materialization, but cannot replace the required
secret references or share temporary space with untrusted parser workloads.

AWS and Google parser Terraform compilers now include these application sources and
emit `document_executor_configuration` bound to the actual job configuration and
parser revision. This is a connected source/bootstrap deliverable, not full
API/worker/SQL/model/source hosting or a completed Spec Kit/export capability.

## Observed evidence

`specs/028-convergence-evaluation/evidence/20261111-private-owned-worker-delivery-v1`
contains four clean dependency-image qualifications, each106 policy checks and88
SQL checks on each PostgreSQL17/18. The13 native factory checks per version include
actual queue execution, citations and cleanup from serialized AWS/Google envelopes.
Source/model/cloud job responses remain fixtures; SQL, crypto and queue behavior
are real local checks. Eleven startup contracts cover schema/bounds, destination,
identity, CLI privacy, API separation and cleanup on exit. All368 JavaScript checks
pass. Normal/hostile AWS/Google packages pass42 native provider-mock plans; four
installed-image consumers load their actual generated envelopes with no network.

Actual emitted application directories for all four providers build to the same
qualified Linux/amd64 platform manifests. The original failed qualifier compared
OCI index identities, which can include new per-build provenance. Native Docker
platform selection showed identical runnable manifest digests, configuration and
layer identities. The repaired verifier requires that exact runnable manifest and
records both different build/index identities; it does not drop attestations or
weaken the source check. The exact earlier qualifier was restored by hash and is
retained with its failed receipt. See
[Docker attestation storage](https://docs.docker.com/build/metadata/attestations/).
Build provenance, runtime platform manifest, parser revision and publication digest
must remain distinct. Publisher/source-policy trust is not established by equality
of runnable code alone; current security acceptance remains open.

Reproduce using the existing owned Docker/SQL fixtures and fresh local output:

- `scripts/qualify-enterprise-runtime.py --provider <provider> --docker-host <owned-socket> --out <core-evidence>`
- `tests/runtime/enterprise_worker_acceptance.py` and `tests/runtime/enterprise_native_postgres.py`, selecting each owned PostgreSQL fixture.
- The AWS/Google infrastructure qualifiers and independent consumers documented in their existing architecture notes.
- `scripts/qualify-enterprise-worker-output.py <native-output> --core-receipt <core-receipt> --docker-host <owned-socket> --out <worker-evidence>`
- `scripts/qualify-enterprise-application-package.py <emitted-output> --core-receipt <core-receipt> --docker-host <owned-socket> --out <package-evidence>`
- `npm test`

## Remaining scope

Finish native Azure/IBM per-file execution and configured worker loading. Complete
four-provider application/worker/database/model/source networking, secret/enrollment
and operator/artifact/monitoring/recovery/Spec Kit composition. Derive published
parser configuration from actual reviewed build/publication receipts; the current
revision envelope is a trusted operator binding, not publisher attestation or a
claim that a registry image exists. Preserve complete source/company requirements.

Then run unchanged full private client briefs and qualify security, operational and
performance behavior. Remaining medium/hard families, final28 and held-out projects
are still required. No capability or complete project is promoted by source
emission, mocks, installed dependency checks or this partial delivery increment.
No cloud deployment, account access, registry publication or remote push occurred.
