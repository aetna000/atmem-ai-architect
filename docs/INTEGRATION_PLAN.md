# AtMem AI Architect integration plan

## Current local milestone

- A single provider-neutral graph powers the unified canvas, architect proposals, inspector, front-panel indicators, wire probes, local fixture runs and export.
- OpenArchFlow modules supply full AWS/Azure/generic/cloud-native/integration catalogues, templates, parsers, layout and payload formatting. Google Cloud and IBM are original starter catalogues, not upstream parity claims.
- AWS architect sample modules supply the composed Strands agent, retry/backoff and rate limiter for explicit SDK providers. The active prompt is neutral; AWS-only automatic MCP initialization is not called.
- Official Claude/Codex/Copilot/Gemini account-client adapters and Claude/OpenAI/Gemini API-key configuration run through a local sidecar. Availability/sign-in/model access remain provider-specific.
- AtMem tokens and identity are used in a read-only local snapshot. AI blocks are prioritised, with broader infrastructure available.
- Pulumi is preferred: metadata scaffold export and sanitised stack-snapshot import are implemented. No resource provisioning or full round-trip claims.
- Original licence texts, source revision/file hashes, notices and dependency inventories are retained.

## Next bounded milestones

1. Finish provider account onboarding and per-provider integration tests, improve streamed job feedback, and test desktop/Windows/Linux packaging. Preserve a zero-key frontend path.
2. Formalise shared schema generation across TypeScript and Python; extend canonical graph migrations, diff-based proposals and revision history.
3. Add AI-specific component schemas and actual staging adapters for selected AWS, Azure and Google Cloud use cases. Keep runtime data contracts separate from architecture relationships.
4. Integrate Pulumi Automation API behind reviewed plans: supported resource constructors, project/stack/state-backend selection, import discovery, explicit refresh and source-change proposals. Do not automatically equate state refresh with rewriting source or diagram intent.
5. Add scoped read-only inventory, first-party documentation tools and evidence-backed pricing. Review per-server licences and tool permissions before optional MCP integration.
6. Add resource-aware staging deployment, actual endpoint evaluation, revision-bound promotion, approvals, rollback/recovery and cost bounds. Production changes require explicit user action.
7. For hosted or commercial multi-user distribution, implement backend identity, workspace ownership, per-user credentials, isolation, quotas, security/release review and distribution-target licensing.

Future atmem.ai/AtMem AI Architect integration remains deferred. Do not push or publish this local milestone without a new request.
