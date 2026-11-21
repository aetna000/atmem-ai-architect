# AWS emulation in AtMem Architect

Open a project, select **Outputs → Emulate locally** (also available in Terraform). The sidecar generates the current Terraform/runtime files and runs supported synthetic acceptance checks in a separate process. Download the emulation report before downloading the delivery ZIP; it contains hashes for the exact generated files. The report is a separate download, not silently inserted into the unchanged ZIP manifest. Changes to generated files invalidate the displayed result.

## Install and reproduce

Install the normal server dependencies first, then the optional pinned worker packages:

```sh
.venv/bin/python -m pip install -r server/emulation-requirements.txt
npm run local
```

Restart a running sidecar after installing or updating the feature. No Docker daemon, AWS credentials, model subscription, cloud quota or cloud spending is needed. The Python Docker SDK is a transitive Moto dependency; this backend does not start containers. Set `ATMEM_ARCHITECT_EMULATION_ENABLED=0` to disable the server feature. An unavailable worker is reported as unavailable, never a pass.

```sh
npm run test:emulation
npm run test:emulation:browser
.venv/bin/python -m unittest server.tests.test_emulation -v
```

The scenario runner uses the seven archived prompt-produced projects and the **current product generator**; it does not repair exported Terraform. Reports go to `.local/emulation/<run>`. Browser evidence goes to `.local/emulation-browser/<run>`. Reports include per-file hashes, so these new results do not overwrite or qualify different older exports. Dependency notices are in `public/licenses/emulation-notices.txt`.

## Evidence boundaries

| Layer | Implemented in this backend | Still unverified |
| --- | --- | --- |
| Storage | Stateful S3 API, versioned writes/reads and prior-version recovery | IAM/resource-policy enforcement, actual AWS encryption/durability |
| Compute | Actual generated Python handler, exact synthetic counts, Unicode and invalid/oversized input | Lambda ARM64/runtime packaging, concurrency and real invocation authorization |
| Async | Moto S3 notifications and SQS redrive, harness-driven polling/invocation/ack, generated worker, DynamoDB conditional writes, duplicate/poison/replay checks | AWS event source mapping execution, timing, visibility/race behavior under load, real alarms |
| Models | Actual summary code, SDK request validation, scripted responses and denied/throttled failures | Managed inference, model availability, factual quality and live throttling |
| Retrieval | Actual emitted retrieval/admin code with stateful DynamoDB transactions, ACL and region filtering, updates/deletes, stale-write conflict and mid-generation revocation | Actual signed gateway requests, IAM policy decisions and production load |
| Browser | Claims-to-directory adapter with synthetic valid/wrong-client claims | JWT verification by API Gateway, OAuth/PKCE, Cognito MFA and CloudFront |
| Sources | Generated synchronization code writing to emulated DynamoDB, permission lease expiry, incomplete-permission refusal, interrupted-write recovery and deletion | Vendor HTTP APIs, actual tenants, native source permissions |
| Infrastructure | Generated configuration supplies runtime wiring and settings; missing notifications/partial-batch mapping fail the harness | Terraform apply is **not run**; use the separate schema/mock-plan checks, then actual account plans |

A pass means the supported local workflow checks passed. It is not a whole-resource emulation pass or production certification. Each report lists resource types as stateful API adapters, host-executed code or not emulated. Synthetic identities and model responses are fixtures. Moto's Dockerless Lambda invocation result is never used: that mode can report success without running code.

The original workflow and emulator failures are retained in the evidence archive. Defects must be classified by reproducing them at the service boundary. Never weaken required runtime behavior to satisfy an emulator.

## Qualified emulator compatibility fixes

Moto is pinned to **5.2.5**. `server/emulation_adapters.py` contains one scoped repair, `moto-s3-notification-version-id-v1`. Unpatched Moto omits `s3.object.versionId` from standard notifications even though the triggering key has its exact version. AWS includes the object version for versioned buckets. The adapter adds only that triggering key's version, preserves all other fields, and restores Moto after the context exits. It never looks up the latest version or modifies the application handler.

A regression test writes two versions before consuming notifications, checks both emitted version IDs and the URL-encoded key, and reads the first version after the second exists. Unsupported Moto versions are refused until requalified. This is a local compatibility patch; no upstream issue/PR has been submitted or claimed.

References: [AWS notification structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html), [Moto source](https://github.com/getmoto/moto/blob/5.2.5/moto/s3/notifications.py), [Moto Dockerless behavior](https://docs.getmoto.org/en/latest/docs/configuration/index.html). [LocalStack](https://docs.localstack.cloud/aws/getting-started/installation/) is a possible additional backend for containerized Lambda and broader infrastructure emulation; it is not installed or qualified here, and its current service/license requirements must be checked separately.

## Worker and future website deployment contract

The frontend uses only the relative authenticated endpoint `POST /api/emulation/run`, with `{project, environment}`. It does not choose executable files, endpoint URLs, worker paths or credentials. The server validates and compiles project data with its own generator. Responses are versioned (`version: 1`), with status, backend/version, design revision, environment, artifact/file hashes, checks, capabilities, compatibility patches, unverified boundaries and cleanup state. Statuses distinguish `passed`, `failed`, `blocked` and `unavailable`; HTTP 409 represents admission rejection and 504 timeout.

The local implementation is behind the existing loopback host/origin/session-token middleware. It permits one job at a time, uses an ephemeral working directory, strips inherited cloud/model credentials, profiles, proxies and endpoint overrides, supplies dummy credentials, and limits a worker to 90 seconds (generation has a separate 20-second limit). Supported designs are bounded to 40 components and input fixtures to 1 MB. Workers block socket connect/DNS to catch accidental service passthrough. Canceling the UI request stops waiting; an already-running worker completes or reaches its server deadline. Its result is not reused after project changes.

**This process adapter is not a public multi-tenant sandbox.** A website deployment should keep the same browser contract behind a same-origin API gateway, then substitute a queued worker adapter with:

- Real user authentication and workspace authorization on every job/report operation; the local shared session token is not hosted identity.
- Tenant-scoped queue admission, rate limits, quotas, cancellation and bounded concurrency.
- An ephemeral container/VM per job, non-root execution, read-only image, no host mounts/Docker socket, enforced network-deny policy, CPU/memory/process limits and a hard job deadline.
- Trusted immutable generator/worker images, artifact digest verification, capability probes and a reviewed emulator version/patch set.
- Encrypted, tenant-scoped evidence storage with retention/deletion controls; no real source documents, cloud credentials or model keys in emulation jobs.
- Separate authorization for real deployment. An emulator pass never grants cloud execution rights.

Python socket interception and dummy credentials are useful local safeguards, not substitutes for OS-level isolation. Public exposure, hosted authentication, distributed workers and hosted deployment are not implemented or claimed by this increment. The UI/API split and versioned result contract allow that change without making browser users install AWS tooling.
