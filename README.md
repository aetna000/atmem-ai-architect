# AtMem AI Architect

AtMem AI Architect helps turn a client's intent into architecture and implementation. The current local candidate adds **Build**: a persistent native engineering session that retains ordered updates, works with reviewed skills and local tools, captures immutable packages and records local checks. **Design** preserves the existing diagram, review and estimate workflow. The engine programme targets AWS, Azure, Google Cloud, IBM and unfamiliar combinations; complete original-project acceptance remains under independent assessment. Nothing is deployed.

For the native candidate, read [Local engineering Build](docs/LOCAL_ENGINEERING.md). The candidate is not a hosted service or a claim that all 28 projects pass.


The architect's know-how lives in [`agent-skills/`](agent-skills): a discovery skill (what to ask, in what order, in plain language, and what to assume when unsure) and workflow skills (knowledge assistant, document processing, prediction, agentic automation). The connected model uses them alongside a small reviewed specialist registry for architecture, security, FinOps, DevOps and all four clouds.

## Installation and training

- [Install, start and troubleshoot AtMem AI Architect](docs/INSTALLATION.md).
- [Hands-on training: your first AI architecture](docs/TRAINING.md).
- [Four-cloud emulation and mentor loop](docs/CLOUD_EMULATION.md): central testing, supported corrections, fresh retests and explicit coverage.
- [Local AWS emulation before download](docs/AWS_EMULATION.md): stateful Moto services and generated runtime checks, with explicit unverified boundaries.
- [Loadable AWS examples and qualification runbook](examples/aws/README.md): seven prompt histories, diagrams, generated code and recorded results. Six compute scenarios have real account plans but remain blocked from live deployment by Lambda quota.

## Start

Prerequisites: Node 22.12+ and Python 3.11+. Current local verification uses Node 26 and Python 3.14.

```sh
npm ci --ignore-scripts
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
npm run setup:memory
npm run local
```

On Windows use `.venv\\Scripts\\python.exe` for installation. The launcher selects the virtualenv executable for the operating system. Windows execution has not been browser-tested.

Open **http://127.0.0.1:5174**. The sidecar binds to **127.0.0.1:8766**. `npm run dev` runs the zero-key frontend alone; model access needs the sidecar.

## Choose an architect

In **Connections**, choose Local patterns, an official account client, or a model API key. Local patterns work without keys. Install/sign in to the desired official client once:

```sh
claude auth login
codex login
copilot login
gemini
```

Use only commands for providers you want. AtMem AI Architect uses their supported native authentication; it does not extract tokens or implement a generic subscription OAuth proxy. Installation and subscription do not guarantee a particular model is available. Choose `default` for a native client's default model or enter an accessible model ID.

For API access, enter a Claude/OpenAI/Gemini key in the local dialog (sidecar memory only), or supply `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `GEMINI_API_KEY` to the sidecar environment. Do not put keys in project data or source control. API billing is separate from account subscriptions. Bedrock is an optional explicit `ATMEM_ARCHITECT_ENABLE_BEDROCK=1` + AWS SDK configuration path.

## Try it

1. **Describe your idea in chat.** The connected architect draws a first sketch and asks one useful question at a time. Answer in your own words. No default blocks are inserted by the local UI.
2. **Work on the diagram together.** Add blocks and right-click comments; with **Draw as we talk** enabled, semantic edits are sent to the architect after a short pause. Routine moves do not trigger a consultation. Requirements are a short read-only working summary derived from the current design, with **Discuss** and **Clarify with AtMem AI Architect** continuing in chat. Your answers update the working requirements. Opening **Options** asks for a provisional comparison of the current approach, AWS, Azure, Google Cloud and IBM; scores are architectural judgements, not price quotes.
3. **Review.** Findings grouped by security, reliability, availability, scalability, performance, maintainability and cost, each with its rule and an action. Accept a risk with a reason and an owner. **Test run** runs designs that have sample-data fixtures (predictive-maintenance and analytics templates).
4. **Estimate.** The architect asks about the largest missing usage or scope assumption in chat. Supported storage list prices are retrieved for the explicit provider/region; the summary shows costs and gaps. Optional worksheet inputs and sources are available in a collapsed inspector. Start with a ROM using stated low/high factors. Refine with detailed cloud charge lines (input/output tokens, compute, requests, storage and transfer), each with quantity, unit, currency, service, region, date and price source. Detailed lines replace the coarse ROM line for that component. Mixed currencies are never summed; stale prices and uncosted components are flagged. Enter one-off consulting/build person-days, rates and scope separately; no prices or effort are invented.
5. **Delivery draft.** Inspect the diagram-derived resource schedule and engineering gaps. **Download delivery pack** exports the specification, diagram, architecture/deployment document, decisions, estimate JSON, resource schedule, handoff checklist, editable project and Terraform sketch from one snapshot. Change the project and regenerate. A manifest identifies each snapshot, design revision and generation time. Nothing is provisioned.

Use **Undo / Redo** for board changes (Cmd/Ctrl+Z and Cmd/Ctrl+Shift+Z). A new board edit clears redo; discovery records and estimates stay intact. **Start over** in the top bar offers to save a project file, or cancel, before clearing the board, chat, requirements, decisions and estimates. The model connection stays. Project boundaries start a separate undo history.

## Voice input

The microphone works as **live dictation**, like a voice input box: speak, watch
words appear, review/edit them, then press **Send**. The architect works on the
design and responds in text. There is no spoken playback or automatic submission.
Press **Stop dictation** to finish the transcript; pressing **Send** during recording
also finishes the latest words before posting once. Typing cancels recording and
preserves your edits. Microphone permission is still required by your browser.

Transcription runs on your computer through the local helper and an optional
OpenAI Whisper installation, rather than the browser vendor's online speech
service. Audio is handled in memory and not saved; only text you submit follows
the selected architect's existing chat/memory path. Prepare local voice once:

```sh
# macOS, if Whisper is not already installed:
brew install openai-whisper
python3 scripts/setup-voice.py
```

The setup script reuses Whisper's existing Python installation and downloads the
checksum-verified official `tiny.en` model (about 72 MiB). It does not use an
OpenAI API key or paid speech service. The helper warms the model after connecting.
An operator can select an existing local checkpoint with
`ATMEM_ARCHITECT_WHISPER_MODEL`. No model is silently downloaded while recording.
A recording is bounded to 60 seconds; stop and start another to continue.

Words update progressively, normally on roughly one-second capture intervals plus
local decoding time. This is not a guarantee of ChatGPT's recognition quality or
latency. Errors remain visible below the composer. See [voice verification](docs/VOICE.md).
`npm run test:voice` uses an isolated frontend and synthetic audio/model transports;
the real local engine was checked separately with generated speech over HTTP.

## AtMem

Open **⋯ → AtMem dashboard** for About you, This project, Skills and Activity. This is AtMem AI Architect's scoped dashboard over the real AtMem 2.3.10 SDK, not the separate upstream operator dashboard. AtMem uses its own `.memory-venv` because its crypto dependencies differ from the model SDK environment. New installations store app-owned memory under `~/.atmem-ai-architect/memory` (or `ATMEM_ARCHITECT_HOME/memory`); the existing `~/.atmem` store is untouched.

Only explicit reusable preferences, accepted project decisions, explicitly authored must-have requirements and budget limits qualify for personal/project memory. Drafts, block positions, canvas comments and routine turns are excluded. You can explicitly say **Remember about me: …**, inspect current/earlier values, preview forgetting, and turn memory off per project. Durable pending updates retry after an outage; content entered while opted out is not replayed. An unavailable memory runtime leaves the architect working from the current project.

The specialist registry is hash checked, has per-skill enable/disable controls, and stores reviewed guidance in a separate AtMem knowledge scope. Pinned upstream skills and their licences are preserved as reference-only assets. The app's bounded broker exposes memory lookup, project read, skill lookup and supported storage price lookup. It has no deployment or shell tool. Per-turn expandable receipts show the context AtMem AI Architect supplied; they cannot attest to a native client's hidden internal prompt.

Current automated storage pricing covers AWS S3 Standard and Azure Blob Hot LRS in an exact supported region/tier. Google Cloud Catalog lookup needs `GOOGLE_CLOUD_BILLING_API_KEY`; IBM needs an exact sourced quote. Missing rates remain explicit gaps. These are storage lines, not a complete infrastructure estimate, and rates are never borrowed across providers.

## Project files

**⋯ → Save project file** writes `<name>.atmem-ai-architect.json` (format `atmem.ai-architect.project` 2.2.0): design, discovery, requirements, assumptions, open questions, decisions with history, and options. **Open project file** restores it exactly, upgrades older workbench files, refuses newer major versions, and keeps unknown fields. Files containing anything that looks like a credential are refused on save and open. Schema: [`specs/002-project-model/contracts/project-file.schema.json`](specs/002-project-model/contracts/project-file.schema.json).

## Specifications

Product direction lives in Spec Kit: the [constitution](.specify/memory/constitution.md) and numbered features in [`specs/`](specs/README.md) (discovery, project model, review, estimate, deployment document, AtMem memory, deployment plan, agent runtime). Use `/speckit-specify`, `/speckit-plan`, `/speckit-tasks` and `/speckit-implement` for new features.

## Checks

```sh
npm test
npm run test:server
npm run test:browser  # isolated real AtMem journey + delivery scenarios; model and quote fixtures
npm run test:terraform # optional: Terraform 1.7+, provider schema and mock-plan checks only
npm run build
npm run notices
```

`python scripts/live-account-check.py PROVIDER MODEL` is an opt-in live smoke check using the running sidecar; it incurs provider usage. Do not run it automatically in CI.

## Scope and deployment

Local fixture runs are deterministic examples, not cloud tests. Architect model requests are real only when explicitly selected and sent. Cloud inventory discovery, executable MCP integrations, full service pricing coverage, provider-native Pulumi resources, real staging tests and deployment remain unimplemented. Pulumi output is a metadata scaffold. Terraform JSON exports the explicitly supported AWS application contracts and Azure/GCP/IBM storage foundations. Unsupported resources, references and connections stay unfinished; a review gate blocks planning until reviewed and completed. It is not a complete deployable AI application. Imported stack metadata is not a live refresh or a complete round trip.

The browser stores projects locally; there is no workspace account service or cross-device sync. This is a single-user localhost application. See [self-hosting](docs/SELF_HOSTING.md) before deploying the workbench yourself. The browser application and the infrastructure drawn on its canvas have separate deployment lifecycles.

## Provenance and commercialisation

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [the merge manifest](docs/merge-manifest.json), [source audit](docs/SOURCE_AUDIT.md), [local architecture](docs/LOCAL_ARCHITECTURE.md), and [Claude Opus 5.5's design review](docs/CLAUDE_5_5_DESIGN_REVIEW.md). Imported upstream licences are preserved; no vendor branding assets are bundled. Original product code has no public open-source licence grant. The product is not commercially cleared by this preliminary engineering inventory.

Options and Design choices are read-only conversational outputs. The architect receives the active view, authors structured requirement proposals from the chat and graph, and refreshes cloud comparisons as answers arrive. Confirmed requirements are preserved; diagram revisions are retained separately from actual choices.

Requirements have stable REQ numbers, retained across document revisions and project saves. Early proposals are collected under **Suggestions still to discuss**. Each requirement includes its rationale and basis when available, with **Explain why we need this** continuing the interview. The local fallback proposes only access and data-location considerations for relevant diagram components; it no longer creates a requirement for every block.

Use **Comment or request a change**, or select requirement text and right-click **Comment on selected text**. **Suggest a revision** saves the feedback and asks AtMem AI Architect for new wording. The current document remains unchanged while you inspect current/proposed text and choose **Apply this revision** or **Keep current wording**. **Save for later** leaves feedback pending. Applied and dismissed suggestions are kept in Feedback history. Comments and proposals survive save/open; stale suggestions cannot overwrite a newer requirement. Document reviews do not apply board, estimate or cloud-choice updates.

## Guided progression

A new project shows the design workspace. The journey strip above the board stays visible with chat open or closed: **Sketch & document → Cloud options → Country & region → Cloud architecture**. It highlights the current stage and gives the next action. Sketch and requirements evolve together; **Continue to cloud options** acknowledges a working scope from either the board or document. The architect compares actual service combinations across AWS, Azure, Google Cloud and IBM. **Preview service architecture** draws an alternative as a pending preview; it does not select a cloud or overwrite the current board.

Click any reached stage in the journey strip to revisit it. Use **Choose AWS & continue →** (or the equivalent Azure, Google Cloud or IBM action) to select a provider and return to the guided conversation. Revisiting Cloud options shows the selected provider and **Continue with [provider] →**; you can choose another provider there. After the cloud choice, AtMem AI Architect asks about country/residency and refines the board into named services, placement and labelled interactions. Review appears after the user continues with that service design. Estimate follows the risk discussion; Delivery draft follows the cost discussion. These checkpoints acknowledge working drafts, including open risks and cost gaps; they are not claims of verified cloud compatibility or permission to deploy. Revising scope or service architecture reopens the relevant earlier step. Progress is stored in the project file.

See [guided journey implementation and validation](docs/GUIDED_JOURNEY.md). `python -m scripts.live-guided-check codex` is an opt-in real account check using synthetic data; it incurs model usage and never deploys resources.

## Download formats

The architecture **Download** action and **Download delivery pack** both generate a ZIP from a single project snapshot. It includes `specification.pdf` (with the diagram, numbered requirements and recorded rationale), `diagram.pdf`, `diagram.svg`, `diagram.png`, the editable project JSON, Markdown documents, resource inventory, estimates and `terraform/`. Diagrams are rendered from all saved board components and connections, independent of zoom or the current tab. SVG remains vector; PNG and the diagram embedded in PDFs are raster exports. Large PNGs are bounded to 8192 pixels per side and 24 megapixels. The PDF exporter uses a bundled Noto Sans font and makes no third-party network requests.

Terraform remains a partial draft: native AWS S3 foundations are generated; other services, providers and application integrations are listed as unfinished. Downloading does not deploy anything.

## Terraform view and checks

At the cloud architecture stage, **Terraform** opens **Resources & code**, showing implemented foundations, missing resources/integrations and the generated files. **Continue to Test Terraform → Run Terraform checks** sends the project to the authenticated local service. The server regenerates its own Terraform from the project (it never executes caller-supplied Terraform files), initializes the official provider with the backend disabled, then runs `terraform validate -json`. Temporary files are removed afterwards, and cloud credentials and Terraform CLI overrides are excluded from the subprocess environment. Provider installation needs network access.

Install Terraform on PATH or in `.venv/bin/`, or set `ATMEM_ARCHITECT_TERRAFORM_BIN` for `npm run local`. Missing tools, provider download failures and validation failures are shown explicitly. Results are cleared when the draft changes. Coverage gaps remain visible even when schema validation passes. A real cloud plan and apply are not connected; a successful schema check cannot establish account permissions, regional availability, successful deployment or application behavior.

## Coding-agent Spec Kit

The ZIP contains an implementation specification separate from the Requirements document. `START_HERE.md` and `AGENTS.md` tell the receiving coding agent how to read the bundle and start work. `spec-kit/implementation-spec.md` and `.pdf` combine the implementation plan, component/interface contracts, detailed tasks and validation plan. The separate `tasks.json` carries stable task IDs, dependencies, source component/edge/requirement links, implementation steps, deliverables and acceptance criteria. `context.json` preserves decisions, assumptions, proposed versus user-recorded requirements, notes and feedback; `questions.md` exposes missing decisions. `progress.json` starts every task as todo and provides fields for evidence, tests, changed files and blockers. `decision-log.md` records implementation decisions.

The kit derives one component task per resource, contract and integration tasks per connection, and acceptance tasks per requirement, plus repository/CI setup, Terraform validation, security/recovery, costs, end-to-end tests and release handover. Build dependencies remain acyclic even when the diagram has feedback loops. Existing systems receive integration/reference tasks rather than recreation tasks. Unknown runtime, API schema, account access and acceptance targets remain clarification work. This is a generated, project-specific implementation plan; it does not claim that code is already written or that deployment is authorized.

The recipient should begin with: “Read START_HERE.md and AGENTS.md, review the Spec Kit, identify the next actionable task and the highest-impact missing decision, then implement approved scope while recording progress and evidence.”

## Product theme

The header reads **AtMem AI Architect**. The UI uses the existing shared AtMem tokens for neutral surfaces and teal actions (`#1F777C` in light mode, `#5FD0D6` in dark mode), matching atmem.ai. Canvas interactions and stored project identifiers are preserved.

## Review outputs before downloading

Choose **Outputs** in the journey strip once a diagram exists. The directory opens on the Spec Kit implementation specification and groups files into Spec Kit, Specification & handoff, Design and Terraform. Markdown is shown as a readable document, JSON/Terraform as code, SVG/PNG as images and PDFs in an embedded viewer. **Download reviewed ZIP** downloads the exact generated snapshot displayed in that directory. Edits to the project regenerate the output bundle; while generation is pending or fails, the reviewed-download action is disabled. No review checkbox implies validation or deployment approval.

## Rename and compatibility

The product and source repository are now AtMem AI Architect (`aetna000/atmem-ai-architect`). New project downloads use `.atmem-ai-architect.json` and `atmem.ai-architect.project`; existing `.atforma.json` files still open. Legacy browser-storage keys and memory subject IDs are retained as compatibility identifiers so existing projects, connections and memory histories are not lost. New settings use `ATMEM_ARCHITECT_*`; the former `ATFORMA_*` environment variables remain accepted. Existing installations keep their `~/.atforma` data directory; new installations use `~/.atmem-ai-architect`, or the configured home directory. These compatibility names are not product branding.

The atmem.ai website presents the architecture platform and its agent-memory foundation. The current architect application still runs locally; website integration does not imply a hosted multi-user workspace or automatic cloud deployment.


## Engineering handoff readiness

Outputs now includes a **Review handoff gaps** action and `spec-kit/readiness.md` / `.json`. The same assessment reaches the architect so it can address priority decisions before export. The report separates design decisions, partial generated foundations, unattached local validation, account planning, staging evidence and production approval. It never infers deployment from a generated file.

Service resolution respects an explicit service field before descriptive labels. Ambiguous labels do not generate resources, and generic OpenSearch leaves domain versus Serverless unresolved. All accepted design ADRs remain in the implementation context; country and deployment region are independent decisions. Shared application blocks, placement conflicts, requirement traceability, cost gaps and current reviewed App Runner eligibility constraints remain visible.

Component tasks include service-specific engineering guidance. The task graph runs local implementation and schema/mock checks before authorized account planning, cost reconciliation and separately approved staging deployment. Live integrations, acceptance and recovery tests follow staging; production release remains separately approved. Existing systems receive integration contracts, not recreation instructions.

Run `npm run test:handoff` for a repeatable multi-provider export/reorder matrix, or `node scripts/handoff-check.mjs /path/to/project.atmem-ai-architect.json` to include a real project. Results and generated text artifacts are written to a temporary review directory. These are deterministic generator checks, not live model or cloud tests. Native generation covers the bounded AWS application contracts described in the AWS runbook and typed storage foundations on Azure/GCP/IBM. Broader application generation remains incomplete; consult the evidence matrix rather than inferring readiness from service names.
