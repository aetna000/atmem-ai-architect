# AWS architecture examples

These are captured outputs from real prompts in AtMem AI Architect, with generated Terraform and recorded validation. They are examples to inspect, change and requalify—not a claim of general AWS coverage or production certification.

Start AtMem Architect with `npm run local`. Use **⋯ → Open project file** and select the example's `project.atmem-ai-architect.json`. Inspect its diagram, continue chatting, and regenerate the delivery pack after changes. Save your own copy to preserve the archived example. No credentials or cloud deployment are needed to load these projects.

| Example | Local exported-code checks | AWS account plan | Live deployment of selected export |
| --- | --- | --- | --- |
| [01 Private storage](01-private-storage/) | Passed | Not run | Not run; earlier storage revision passed and was cleaned up |
| [02 Document statistics](02-document-compute/) | Passed | Passed | Blocked by Lambda quota |
| [03 Asynchronous processing](03-async-documents/) | Passed | Passed | Blocked by Lambda quota |
| [04 Bedrock summarization](04-model-summary/) | Passed | Passed | Blocked by Lambda quota |
| [05 Cited answers](05-cited-rag/) | Passed | Passed | Blocked by Lambda quota |
| [06 Permission-aware answers](06-permission-rag/) | Passed | Passed | Blocked by Lambda quota |
| [07 External sources and web](07-enterprise-connectors/) | Passed after correction | Passed | Blocked by Lambda quota |

The six account plans were run against Sydney on 2026-11-07. The quota request remains `CASE_OPENED`; actual concurrency was 10 at the recorded check. Bedrock control-plane availability is not an inference test. SharePoint/Confluence examples use normalized local test servers; native APIs and real tenants remain unverified. Retrieval is bounded keyword retrieval, not managed vector search.

- [Runbook: prompts, reproduction, AWS gates, acceptance and cleanup](RUNBOOK.md)
- [Machine-readable results and SHA-256 manifest](manifest.json)
- [Recorded quota check](evidence/lambda-quota-status.json)
- [Fresh local reproduction of all seven archived exports](evidence/local-artifacts/results.json)
- [All seven file-menu imports and canvas renders](evidence/browser-import/results.json)
- Milestone before this work: [`96e369d`](https://github.com/aetna000/atmem-ai-architect/commit/96e369d), tag `milestone/aws-qualification-foundation-2026-11-07`.

Each example includes its exact prompts and model responses in `history/`, a loadable project, diagram, generated Terraform/runtime/tests, and results. The connector history includes failed attempts. Published text replaces local paths and the account identifier; hashes identify published bytes and original bytes separately. State, account-bound inputs, binary plans, runtime build directories and credentials are excluded. Model statements about testing are not evidence; use runner receipts.

## Stateful emulation before download

AtMem Architect now offers **Outputs → Emulate locally**. [All seven supported workflows passed the current generator's emulation run](evidence/emulation/2026-11-07T06-51-24.662677+00-00/results.json). Reports bind the generated files and worker code by hash. [The first failed run](evidence/emulation/2026-11-07T06-41-43.615468+00-00/results.json) and [the harness correction run](evidence/emulation/2026-11-07T06-42-43.242069+00-00/results.json) are retained.

These are stateful Moto API and host-executed handler checks, with scripted model/authentication envelopes. They do not apply Terraform, enforce real IAM, run managed inference or qualify native vendor connectors. See [emulation setup, coverage, compatibility fix and hosted-worker requirements](../../docs/AWS_EMULATION.md). Previous live-deployment statuses in the table above remain unchanged.
