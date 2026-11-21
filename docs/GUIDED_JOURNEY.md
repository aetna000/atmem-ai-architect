# Guided architecture journey

The main consultation moves from sketch/document to cloud choice, country/residency, named service architecture, risk review, cost estimate and delivery draft. Later views and delivery export actions remain hidden until the relevant working-draft checkpoint. The current next step is passed to the model on every turn. Navigation alone does not mark a stage complete.

The always-visible journey strip above the workspace highlights the current stage, explains its purpose and exposes the primary next action even when chat is closed. **Continue to cloud options** works from the board as well as Requirements. Reached stages in the strip are clickable, so users can return to Cloud options without resetting checkpoints or the diagram. The selected provider is shown when revisiting Options, alongside a **Continue with [provider] →** action. Each cloud comparison has a **Choose [provider] & continue →** action that sends the explicit selection into the consultation; country/residency is the next interview step. Service previews remain separate from provider selection.

Project-scoped compact change fingerprints invalidate downstream checkpoints when confirmed scope, service selection, placement, connections or costs change. Requirements, comments, cloud previews and undo/redo keep their existing behavior. A preview is a complete candidate graph but does not modify the active board until applied; previewing a cloud does not record an accepted cloud choice.

Service mapping checks the selected provider against a bounded local name catalogue, region/global-placement fields and labelled connections. This detects generic or unmapped blocks. It does not query cloud inventories, validate regional service/model availability, verify IAM or networking, or prove integrations work. These remain explicit review/engineering tasks. The native Terraform exporter still covers S3 foundations only; no cloud deployment tool exists.

## Validation

Unit scenarios cover all four providers, hidden initial stages, generic-node rejection, scope changes and reopening architecture review after a regional change. Browser scenarios cover the staged flow, country question, pending service preview, named provider nodes, comments, AtMem, estimates and delivery export. Their model and quote responses are fixtures over real app routes and AtMem storage.

An opt-in real Codex account check also completed two synthetic turns: a six-block concept sketch followed by a concrete Azure proposal using Blob Storage, AI Search, Container Apps, Azure OpenAI, Microsoft Entra ID and Key Vault, with twelve connections. The model asked where documents and their permissions currently live. Its service graph passed the local mapping check. This verifies native model output and schema handling, not cloud execution or compatibility. The script is `scripts/live-guided-check.py` and does not run in CI.

## Reference architecture sources

The service-level approach is consistent with these provider references, checked during implementation. The application does not claim it fetched these pages during a user turn:

- [AWS RAG implementation guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/basic-reasoning-agents.html) describes document storage, retrieval and orchestration alongside model invocation.
- [Azure retrieval-augmented generation](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview) describes retrieval and grounding with Azure AI Search.
- [Google Cloud Run AI use cases](https://docs.cloud.google.com/run/docs/ai/use-cases) includes RAG hosting with Vertex AI and Vector Search.
- [IBM retrieval-augmented generation setup](https://cloud.ibm.com/docs/watsonx-code-assistant?topic=watsonx-code-assistant-rag-overview) documents its product-specific retrieval integration; its plan and integration constraints must not be generalized to every IBM workload.
