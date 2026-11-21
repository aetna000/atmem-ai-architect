# AtMem AI Architect local-first architecture

AtMem AI Architect is an AI-first, multi-cloud workbench. AWS, Azure and Google Cloud are the initial focus. IBM remains a small starter catalogue; other providers can be added through the same contract. General compute, database, networking and integration services remain available alongside AI components.

## Source integration

The unified React Flow 12 canvas consumes OpenArchFlow catalogue data, templates, Mermaid and SQL import, Dagre layout, and nested payload formatting. Exact copied paths, source hashes, and modification status are recorded in `merge-manifest.json`; repository commits are in `upstream-lock.json`. No upstream Next.js shell, Streamlit UI, vendor icon pack, SEO ratings, analytics or deployment process is executed.

The Python sidecar imports the AWS sample's composed `AWSArchitectAgent` and its retry/backoff and `RateLimiter` implementation for configured SDK model adapters. It deliberately does not call upstream `initialize()`: that starts MCP commands using unpinned `@latest` and selects an AWS-only prompt. AtMem AI Architect supplies its own provider-neutral prompt, explicit model selection, no automatic tools, and strict response validation. The original upstream prompt is retained as provenance source only and is never installed as the active prompt.

## Fast account access

Official local clients reuse their own authentication: Claude Code, Codex, GitHub Copilot SDK/CLI and Gemini CLI. AtMem AI Architect never reads, extracts or copies account tokens. The connections dialog supplies the official terminal sign-in command; users sign in using the official client, then use it from the workbench. CLI installation alone is not proof of account access. Native client history, telemetry, subscription limits and provider terms remain provider-specific.

Direct Claude, OpenAI and Gemini API keys are supported through the Strands adapters. A key may be supplied to the sidecar environment or entered in the local connection dialog. Entered keys are held only in the sidecar process memory; restarting clears them. They are not saved in browser storage or project exports. API credentials have separate billing and permissions from account subscriptions. Copilot has an account adapter; it is not presented as an interchangeable model API key.

Official CLI calls run in temporary working directories, with model tools disabled/restricted, explicit timeouts and cancellation. Claude and Codex use ephemeral sessions; Copilot disables configured instructions, hooks, skills and tools through the SDK. Gemini uses a scoped settings override and deny-tools policy. SDK requests cannot guarantee recall of already submitted remote work when cancelled; provider-side usage may continue. Chat is model work, not permission to execute the drawn infrastructure.

## Local trust boundary

`npm run local` starts Vite on `127.0.0.1:5174` and FastAPI on `127.0.0.1:8766`. Vite proxies `/api`. The sidecar checks Host and Origin, uses a random process-lifetime bearer token for POST operations, limits payload size, disables API docs and access logging, and does not expose cloud discovery or deployment endpoints. The browser holds the bearer token in memory. A single in-flight model request avoids concurrent native-client sessions.

This is a single-user local trust model, not multi-tenant SaaS. Do not expose it through a public tunnel. Self-hosting on a server requires real user authentication, per-user credentials, isolated execution, TLS, secret management and revised origin/host controls. Deployment of AtMem AI Architect and deployment of user-designed infrastructure are separate operations.

## Project and execution semantics

One canonical graph powers manual edits, validated architect proposals, the block diagram, front-panel indicators, wire probes and local fixture execution. Proposals contain a base revision and complete candidate graph; user acceptance creates an undoable revision. Stale proposals cannot be applied.

Imported upstream reference blocks do not silently become executable fixtures. The Inspector exposes an explicit fixture-behaviour selection. This assigns local synthetic behaviour; it does not create a cloud adapter. Structural errors prevent execution. Failed blocks skip downstream execution. Cancellation suppresses later block events. Editing the graph invalidates current simulation evidence.

## Pulumi-first interchange

Pulumi is the preferred infrastructure engine direction. The initial implementation exports a TypeScript Pulumi scaffold containing metadata ComponentResources and dependency ordering, with no provider-native cloud constructors. It also imports sanitised resource identifiers/type/name from Pulumi stack-export JSON; input/output properties and secret envelopes are discarded. Imported snapshot references are kept separate until the user chooses to create a proposed design from them.

Pulumi import can adopt existing resources and generate code. Refresh reconciles recorded state with observed cloud resources; it does not automatically rewrite application source or recover arbitrary diagram semantics. Current AtMem AI Architect does not invoke Pulumi import/refresh/preview/up, reconstruct a complete cloud topology, or offer live drift detection. Terraform remains a future optional adapter rather than a second parallel deployment engine.

References: https://www.pulumi.com/docs/iac/guides/migration/import/ and https://www.pulumi.com/docs/iac/concepts/state-and-backends/.

## Hosting state

This integration is localhost only, per the user's request. No new changes are pushed to Sites or atmem.ai. The earlier private demo remains a separate, older artifact. The future `/AtMem AI Architect` path is a destination requirement only; no existing AtMem website source, Firebase configuration, custom domain or production release is changed.
