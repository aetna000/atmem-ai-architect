# Emulate, learn, correct and retest

Open **Emulate & improve** from the architecture journey, or run the same checks from Outputs or Terraform. The report belongs to the current project, environment and generated artifact. Navigation preserves it; changes and Undo invalidate it. Downloaded reports identify the exact generated file hashes and worker version.

When an architect model is connected, each fresh result automatically starts one mentoring turn per selected provider/model. Switching to another ready architect can resume guidance on the same report. The architect explains actual evidence, proposes the smallest supported correction, or asks a focused question. **Draw as we talk** controls whether proposals apply immediately; otherwise the user reviews them. Corrections remain visible, logged and undoable. Automatic retesting stops after two applied corrections; a manual run starts a new bounded session. Both automatic mentoring and retesting can be switched off. Report text is untrusted input, not authority to change scope, requirements or credentials.

An empty checks list means **no runtime tests ran**, including when a generator gap blocks execution. It never means the architecture is sound. A deterministic evidence summary accompanies the mentor; unsupported reassurance about an empty run is removed. Existing components, service choices and permission boundaries cannot be deleted or silently redirected to clear a gate.

## Qualified local backends

| Provider | Current local implementation | Evidence boundary |
|---|---|---|
| AWS | Moto 5.2.5 stateful S3/SQS/DynamoDB, emitted Python handlers, explicit fixture model/identity adapters | Seven existing application scenarios; IAM, sign-in, actual Bedrock quality and cloud runtime still require real checks |
| Azure | Azurite 3.37.0, emitted Blob client, native AzureRM storage/container/custom-role Terraform | Private object CRUD; Entra permissions, versioning/retention and control-plane deployment unverified |
| Google Cloud | fake-gcs-server 1.56.1, emitted GCS client, native Google bucket/IAM Terraform | CRUD, stale-generation rejection and prior-generation recovery; IAM, signed URLs and control-plane deployment unverified |
| IBM | Moto S3 protocol model, emitted S3-compatible COS client, native IBM bucket/IAM Terraform | Object protocol and version recovery only; **not an IBM Cloud service/control-plane emulator** |

The Azure/GCP/IBM storage foundation requires an explicit existing caller and object CRUD permission edge. Destinations and identity identifiers are required Terraform inputs. The new storage exports pin AzureRM 4.81.0, Google 7.46.2 and IBM 1.89.0 and include the qualified provider lockfile and client SDK requirements. Existing identity policies need review. Azure uses a container-scoped custom data role; Google uses bucket-scoped `roles/storage.objectUser`; IBM uses a bucket-scoped Writer grant. An authenticated public endpoint is not a private network endpoint. Production exports remain blocked pending operational/remote-state review.

## Install and reproduce

```sh
.venv/bin/python -m pip install -r server/emulation-requirements.txt
npm run setup:emulation:clouds
npm run test:emulation
npm run test:emulation:clouds
npm run test:emulation:browser
```

The optional setup installs lockfile-pinned Azurite without npm lifecycle scripts, checksum-verifies the official fake-gcs-server release, and installs pinned client SDK dependencies. The current process adapter supports macOS/Linux arm64/amd64; other platforms need qualification. Docker is not required. Terraform 1.7+ must be installed for native schema/mock plans; the qualification script uses `.venv/bin/terraform`.

Azurite: <https://github.com/Azure/Azurite>. GCS API emulator: <https://github.com/fsouza/fake-gcs-server>. Provider Terraform schema/mock plans are separate checks, not emulator results. The worker uses temporary storage, synthetic identities, worker-owned loopback ports, disabled Azurite telemetry and bounded subprocess lifetime. External SDK connections are rejected. Timed-out workers and their child servers are killed together. No inherited cloud credential/profile or proxy enters the worker.

## AI applications are the target

The [forty-case AI qualification specification](../specs/024-ai-workload-qualification/spec.md) covers IoT, observability, RAG, chatbots, version control, predictive maintenance, customer support, call-center/CRM, cloud operations and cybersecurity on all four clouds. Each case has explicit behavioral acceptance requirements. A scenario's presence in the registry is not evidence that its native implementation exists. Unsupported application components remain in the design and in the implementation backlog; they do not become a storage-only example.

[Archived real prompts, loadable diagrams, outputs and results](../examples/cloud-qualification/README.md) separate static graph checks, native schema/mock plans, runtime emulation and model mentoring. The real-model script is opt-in and uses the selected account client; it is not an automatic CI task:

```sh
npm run test:mentor:live -- aws,azure,gcp,ibm
npm run test:mentor:live -- aws --ai
```

## Hosted deployment boundary

The UI talks to a provider-neutral job endpoint and server-owned generation/worker adapters. Current execution is single-user and local. A hosted version still needs tenant authentication, authorized job ownership, queues, isolated ephemeral containers, OS-level network restrictions, resource limits, per-tenant secret handling, cancellation and audit retention. The local Python socket guard is not a public multi-tenant sandbox. See [AWS emulation](AWS_EMULATION.md) for the existing hosted adapter contract and detailed AWS test coverage.

## Validation receipt — 2026-11-07

185 JavaScript tests, 102 server tests, the voice/main/delivery browser suites, eight emulation-browser assertions, and the production build passed. All seven existing AWS emulation scenarios passed. The three new storage contracts passed real provider init/validate/mock plans and local APIs; exact Terraform downloaded from the real storage model/UI runs also passed native provider checks.

The forty AI workload cases have archived real-model diagrams and bounded static graph assessments. One case in that broader matrix (AWS RAG) has a local runtime pass; thirty-nine still have application implementation gaps. Later model repeats include Claude session-limit failures and an Azure/Codex timeout followed by a successful retry. The archive retains these alongside the successful mentoring repeats. Neither the matrix nor the build establishes full production readiness.
