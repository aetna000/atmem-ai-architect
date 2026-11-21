# Plan — Terraform apply emulator

Dependency-ordered. Status reflects delivered files and observed test evidence, not intent.

| # | Deliverable | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Feasibility: real `terraform apply`/converge/destroy against loopback Moto with provider 6.72.0 | Done | decision-log.md |
| 2 | Provider-neutral lifecycle engine and report (`server/terraform_emulator.py`) | Done | `server/tests/test_terraform_emulator.py` |
| 3 | AWS backend: endpoint redirection, fail-closed egress, request log, gap classification | Done | RequestLog tests; corpus run |
| 4 | Independent SDK read-back verifiers (including added lifecycle engines) | Done | per-resource `checks` in reports |
| 5 | Destroy-protection proof and service-inventory leak check | Done | example 01 report; counterexample test |
| 6 | Version-scoped Moto adapters, including the rpc-v2-cbor protocol bridge | Done (6) | `AdapterTests`; docs/TERRAFORM_EMULATION.md |
| 6a | AtMem-built engines: CloudFront, Step Functions validation/versions, Cognito resource servers | Done | `server/tests/test_terraform_emulator_engines.py`; edge, edge-policies, workflow, auth fixtures |
| 6b | Board dock and live diagram animation from Terraform's event stream | Done; real browser lifecycle passed | `tests/terraform-apply-emulation.test.mjs` |
| 7 | Isolated hash-locked runtime and setup script | Done | clean install verified |
| 8 | Server job API and Terraform view panel with live stages | Done; real browser lifecycle passed | route tests; `tests/terraform-apply-emulation.test.mjs`; production build |
| 9 | AWS fixture corpus (22 service fixtures) and measured coverage file | Done | `docs/terraform-emulator-aws-coverage.json` |
| 10 | Seven archived AWS example projects through the current generator | Done: 7/7 passed | `.local/terraform-emulation/2026-11-16T22-54-55.576371+00-00/results.json` |
| 11 | Repair remaining recorded lifecycle gaps: Serverless, Bedrock guardrails and knowledge bases, App Runner; RDS parameter-group read-back | Done; original AI composite and individual fixtures pass | continuation engine tests; original AI composite now 6/6; all 22 fixtures have passing receipts |
| 11a | OpenSearch domain lifecycle with the real provider waits | Done; both full lifecycle runs passed | provider 6.72.0 waits ten minutes in create and delete; deadline corrected without bypassing waiters |
| 11b | Real browser recording and reproducible, revision-bound coverage | Done | live Board run; per-fixture implementation, artifact and report digests |
| 12 | Azure backend | Not started | — |
| 13 | Google Cloud backend | Not started | — |
| 14 | IBM Cloud backend | Not started | — |
| 15 | Hosted execution (tenant auth, container isolation, network policy) | Not started | requirements in 022 |

## Next backends — same engine, same report

A backend supplies: availability, start/stop, provider environment, synthetic inputs, seed fixtures, SDK verifiers and inventory probes. Candidates need qualification before any claim:

- **Azure:** `azurerm`/`azapi` call Azure Resource Manager over HTTPS with Entra ID tokens. Azurite covers the storage data plane only. A backend needs an ARM-compatible control-plane emulator and a way to satisfy the provider's authentication and metadata discovery. Highest effort.
- **Google Cloud:** the `google` provider accepts per-service `*_custom_endpoint` settings. fake-gcs-server covers Cloud Storage; other services need emulators or an API-discovery-driven stateful server.
- **IBM Cloud:** the provider supports private/custom endpoint files. No maintained multi-service emulator is known; requires research.

Until then these families return `unavailable`. Their existing schema and mock-plan checks are unchanged.

## Rollback

The feature is additive: one route module, one worker, one UI panel. Remove the `terraform_emulation_routes` include in `server/app.py` and the `TerraformApplyPanel` line in `src/TerraformView.jsx`, or set `ATMEM_ARCHITECT_EMULATION_ENABLED=0`. Existing emulation and validation code paths are untouched.
