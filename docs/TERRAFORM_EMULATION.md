# Terraform apply emulation

Runs the real Terraform lifecycle of a project against a cloud API on loopback. The Terraform CLI, the provider plugin, the configuration and its dependency graph are the real ones; only the cloud endpoint is replaced. No cloud account, credentials or spend.

AWS is the first backend. Azure, Google Cloud and IBM use the same engine and report but have no backend yet and return `unavailable`. Specification: [032](../specs/032-terraform-emulator/spec.md).

## Use it

Both the packaged launcher and `npm run local` install the private Terraform binary and hash-locked emulator runtime automatically. Existing configured tool paths are preserved. First setup needs internet access; users do not run a separate Python setup command.

In the app, on the **Board**: **Emulate apply** opens the dock; the play button runs the lifecycle. Blocks follow the real run: creating, applied, SDK-verified, destroying, gone, then passed or failed. Each block shows how many of its resources are live. The same run appears under **Terraform → 2. Test Terraform**. Download the JSON report afterwards.

Diagram states come only from Terraform's own event stream and the read-back checks. A resource maps to a block by its `block_<id>` address or its `Component` tag; nothing is animated on a timer.

On any Terraform directory:

```sh
npm run setup:terraform:emulator            # once: isolated, hash-locked runtime
.local/terraform-emulator-runtime/bin/python -I server/terraform_emulator.py \
  --dir path/to/terraform --progress --report report.json
```

`--var-file inputs.json` supplies input variables. `--trace timeline.json` also records stage, resource and API-call timing. The exit code is 0 only for `passed`.

The local process-group lifecycle is qualified on macOS; Windows termination and cross-platform behavior remain unqualified. Requires Terraform 1.7+ (`ATMEM_ARCHITECT_TERRAFORM_BIN` or `PATH`) and Python 3.11+. No Docker daemon. With a provider mirror at `.local/provider-cache` (or `ATMEM_ARCHITECT_PROVIDER_CACHE`) the whole run is offline; without one, `terraform init` downloads the provider and cloud API calls still stay on loopback. Set `ATMEM_ARCHITECT_EMULATION_ENABLED=0` to disable the server feature.

## What a run does

| Stage | What it establishes |
| --- | --- |
| Application build | Generated `build-runtime.py` produces the archives the configuration references. |
| Provider initialization, Schema validation | Real provider, real schema. |
| Plan | A real plan against live emulator state. |
| Apply | Provider API requests execute in dependency order; each is logged. |
| Independent API read-back | A separate AWS SDK client re-reads resources and compares them with Terraform state. Types without a verifier are labelled `provider-refresh-only`. A verifier checks named fields, not every service property; each report lists the comparisons. Image settings, blocked messages/filter strengths and vector model/storage mappings have explicit comparisons. |
| Convergence plan | A second plan with full refresh must propose zero changes. |
| Destroy protection | `lifecycle.prevent_destroy` must block a destroy plan. It is then lifted in the private workspace only. |
| Destroy | Teardown through the same provider. |
| Leak check | Configured SDK service inventories and custom-engine inventories are checked; any discovered remainder fails. |

The source directory is never modified. Backend implementation files are also SHA-256 hashed under `backend.implementationDigests`. Every input file is hashed into the report (`fileDigests`, `artifactDigest`); the server refuses a worker report whose hashes differ from what it generated. Files the emulator adds to its private copy are listed under `workspaceAdditions`.

## Result statuses

`passed` — every stage passed. `failed` — Terraform, read-back, convergence or teardown failed for a reason not attributed to the emulator. `unsupported` — the emulator does not implement a required API operation; not a pass and not a configuration failure. `blocked` — unfinished generator work or a required input without a value. `unavailable` — runtime, Terraform or backend missing.

## Isolation

- Redirection uses the provider's `AWS_ENDPOINT_URL` contract, so all provider services are covered without editing the configuration.
- Terraform starts with no inherited credentials, profiles, config files or proxies, and a synthetic account `123456789012`.
- Plain-HTTP requests to other host names (the provider's account-prefixed S3 Control calls) are proxied to the emulator. HTTPS to any real endpoint is sent to a closed port and cannot connect.
- The emulator binds `127.0.0.1` on an ephemeral port and lives only for the run. The server kills the whole worker process group at its time limit.

This is local process isolation, not a hostile multi-tenant sandbox. Hosting needs the tenant authentication, container isolation and network policy listed in [AWS emulation](AWS_EMULATION.md).

## Inputs

Only destination inputs with an explicit rule are synthesized: `aws_account_id`, `aws_region`, `review_approved` (an explicit rehearsal value, not a deployment approval), `principal_*_arn` (the referenced IAM role is created in the emulator first) and `*_alert_topic_arns`. Literal values in the module's own `tests/*.tftest.hcl` `variables` block (the generator's qualification inputs) fill other required variables and are labelled `module-test`. Anything still missing blocks the run and is named in `missingInputs`.

## Open-source base, AtMem-built engines

Moto 5.2.5 is the open-source base. Where it lacks an API the provider needs, AtMem builds that engine (`server/terraform_emulator_engines.py`). An engine is stateful, speaks the service's wire protocol and error codes, and answers before Moto. Every report lists the engines (`backend.engines`) and how many calls each component answered (`apiCalls.byEngine`).

| Engine | Implements | Behavior |
| --- | --- | --- |
| `atmem-cloudfront` | Distributions with tags; cache, origin request and response headers policies; the AWS managed policy catalog | CloudFront's stored-configuration defaults, ETag optimistic locking, `NoSuch*`, `*AlreadyExists`, `*InUse`, `DistributionNotDisabled`, `IllegalUpdate/Delete`, marker pagination. A distribution cannot reference a policy or origin that does not exist. |
| `atmem-stepfunctions-validation` | `ValidateStateMachineDefinition`, `ListStateMachineVersions` | Structural Amazon States Language validation with located diagnostics: StartAt, state types, transitions, terminal states, Choice, Wait, nested Parallel/Map. Expressions and resource ARNs are not evaluated. |
| `atmem-cognito-resource-servers` | `DeleteResourceServer` | Removes that resource server from the base emulator's user pool; AWS not-found errors otherwise. |
| `atmem-apprunner` | Image-service create, describe, update, delete, listing, operations and tags | Region-scoped identities and lifecycle; duplicate and missing-resource errors. Code repositories, custom autoscaling and encryption configurations are explicitly unsupported. Images are never executed. |
| `atmem-opensearch-serverless-lifecycle` | Collection creation and encryption-policy deletion | Matches exact or wildcard encryption policies, retains AWS-owned-key semantics, deduplicates client tokens and removes policies from shared state. Other operations use Moto. No indexing or encryption enforcement. |
| `atmem-bedrock-guardrail` | DRAFT content-policy guardrail lifecycle and tags | Retains requested categories and strengths, validates basic inputs and deduplicates client tokens. Other policy families are unsupported. No inference or moderation. |
| `atmem-bedrock-knowledge-base` | Vector knowledge-base registration with OpenSearch Serverless, updates and tags | Requires a collection in the same region; preserves field mapping, index name and embedding configuration. Does not establish index existence, IAM grants, model availability, ingestion or retrieval. |

Managed policy IDs and settings come from the CloudFront Developer Guide (read 2026-11-17). Where that guide states no value for a required CORS member of a managed response headers policy, the simple-request set is used.

Distributions report `Deployed` immediately; edge propagation, certificates, DNS and request serving are not emulated.

## Emulator compatibility repairs

Each repair is version-scoped to Moto 5.2.5, listed in every report under `backend.adapters`, and changes emulator behavior only — never the configuration. No upstream issue or PR has been submitted or claimed.

| Adapter | Observed defect | Scope |
| --- | --- | --- |
| `moto-rpc-v2-cbor-bridge-v1` | The provider calls CloudWatch in the smithy rpc-v2-cbor protocol; Moto server mode routes only the JSON and query forms, so alarms could never be created. | Re-encodes the same operation and members between CBOR and JSON using the pinned botocore model. No value is added, removed or defaulted. |
| `moto-s3-create-bucket-tags-v1` | Tags sent inside `CreateBucketConfiguration` are dropped; false drift on every tagged bucket. | Stores exactly the tags of the successful CreateBucket request. |
| `moto-s3-policy-condition-v1` | Conditional bucket-policy statements are applied unconditionally, so deny-insecure-transport blocks every object upload. | Conditional statements are stored and returned unchanged but not enforced. |
| `moto-sqs-redrive-allow-policy-v1` | `RedriveAllowPolicy` cannot be read back; `RedrivePolicy` is re-serialized; setting any attribute clears the queue `Policy`. | Returns stored values as supplied; keeps `Policy` when a request does not name it. |
| `moto-rds-parameter-source-v1` | Modified DB parameters omit `Source`, so the provider skips them and repeatedly proposes changes. | Marks explicitly modified values as user-sourced; retains values and apply methods. Engine validation and reboot semantics remain unverified. |
| `moto-lambda-mapping-alias-arn-v1` | An alias-qualified event source mapping is reported as targeting a numbered version. | Keeps the exact alias ARN supplied at creation. |

An unimplemented, routeless or crashing emulator operation is answered once with a non-retryable `EmulatorNotImplemented` / `EmulatorInternalError` in the service's wire protocol, so a gap fails in seconds instead of exhausting SDK retries. A command deadline alone is not evidence of an unsupported API. Unfinished creation is named and reported `blocked`, with `timedOut: true`; teardown still runs. The pinned AWS provider 6.72.0 deliberately waits ten minutes during both OpenSearch domain creation and deletion ([provider source](https://github.com/hashicorp/terraform-provider-aws/blob/v6.72.0/internal/service/opensearch/wait.go)). Corpus qualification therefore permits 900 seconds per command, without bypassing that provider behavior.

## Evidence boundaries

| Established on the emulator | Still unverified |
| --- | --- |
| Dependency order, argument validity and API request shapes of the real provider | Real AWS acceptance of those requests in your account and region |
| Stored configuration read back through an independent SDK client | IAM and resource-policy enforcement; encryption and durability |
| Zero-change second plan | Drift caused by real service defaults Moto does not model |
| Destroy protection and complete teardown | Deletion windows, retention and eventual consistency |
| Lambda/ECS/API resources registered | Code execution, invocation, networking and performance |

Leak checks cover the configured inventory probes and custom-engine inventories, not an exhaustive AWS account inventory. Quotas, limits, timing, service availability and pricing are not emulated. A pass is not an account plan or a deployment. Handler behavior is covered separately by [local AWS emulation](AWS_EMULATION.md); schema and mock-plan checks remain separate checks.

## Measured AWS coverage

`npm run qualify:terraform:emulator -- --write` runs every fixture under `tests/terraform-emulator/aws` and regenerates [terraform-emulator-aws-coverage.json](terraform-emulator-aws-coverage.json). A resource type is `qualified` only when it applied, converged and was destroyed in a fully passing fixture. Types absent from that file are unmeasured.

Coverage results are generated from completed fixture reports. Consult each fixture outcome and its implementation digest; a passing type does not establish support for every configuration of that service.

## Reproduce

```sh
npm run setup:terraform:emulator
npm run test:terraform:emulator        # seven archived AWS example projects, current generator
npm run qualify:terraform:emulator     # fixture corpus
.venv/bin/python -m unittest server.tests.test_terraform_emulator -v
node --test tests/terraform-apply-emulation.test.mjs
```

The real Board demo can be recorded with `ATMEM_EMULATOR_DEMO_URL=http://127.0.0.1:<ui-port> node scripts/record-terraform-emulator.mjs <output-directory>`. Configure the backend to allow that UI port; the script preserves actual polling responses, the downloaded report, screenshots and the raw recording.

Reports go to `.local/terraform-emulation/<run>`. Existing receipts can be summarized without rerunning Terraform using `--reports-from <corpus-report-directory> --write`; per-fixture digests retain the measured revisions. Historical failures remain in their original run directories.
