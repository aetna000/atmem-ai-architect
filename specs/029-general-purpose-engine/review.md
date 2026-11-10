# General-purpose engine review — 2026-11-11

Status: initial cross-layer source review and local composition diagnostics complete;
two-turn uncoached conversation diagnostic complete; broader conversation and full runtime/generalisation audit remain pending.
This review does not qualify a release. Source baseline: 67e0e59 plus the separately
identified unqualified Azure checkpoint. No cloud operations were performed.

## Owner direction and conclusion

Build an engine capable of delivering the 28 evaluation projects and unfamiliar
combinations. Do not build 28 bespoke deliverables. Generality and engineering depth
are separate requirements; neither may be traded away for a benchmark score.

The repository has valuable reusable safety and evidence foundations. It does not
yet demonstrate general-purpose composition or independently controlled architectural
convergence. Execution has become concentrated on deep application-specific runtime
work before the shared planner/composer and everyday conversation experience are
proven. Preserve that work, extract reusable mechanisms, and review before expansion.

## Findings by layer

| Layer | Existing value | Gap / evidence | Required direction |
|---|---|---|---|
| User intake and abstraction | `server/abstraction.py` gives ownership, topology-first and question-impact guidance | `server/prompts.py:7` narrows the product to the AI stack; line 21 requires two sentences then a question, while later policies permit optional questions and direct technical work. Broad software/DevOps intent and competing conversation rules need reconciliation. | One coherent policy; host-owned decision state, useful progress and optional material questions. Test plain unfamiliar briefs without benchmark coaching. |
| Reasoning and repair | Revision-safe patches, strict response validation, bounded evidence tools | `server/architect.py:31-64` repairs response/schema failures; `server/agent_runtime.py:60` bounds evidence lookup. These are not semantic architecture search, independent evaluation or convergence control. `docs/architecture/progressive-convergence.md` explicitly records that optimizer as unimplemented. | Separate propose, constraint/interface evaluation, targeted repair and stop/ask decisions. Preserve scope and report actual evidence. |
| Project representation | Explicit ownership, typed nodes/edges, reviewed contracts | `server/contracts.py:80,106` enumerate fixed application/integration recipes; domain values remain maintenance/churn. Shared configuration includes provider-specific assumptions. A closed verified registry is useful, but is not a composition model. | Versioned capabilities with requires/provides, interface and ownership invariants, compatible adapters, change impact and evidence requirements. Keep strict boundaries. |
| Composition and Terraform | Concrete provider implementations and explicit unsupported-work gates | `src/terraform.mjs:32-39` dispatches whole projects by recipe; `src/resources.mjs:61` similarly delegates invoice projects. `src/invoice-plan.mjs` accepts one invoice unit, treats additional proposed components as missing. Local counterexample confirms supported standalone containers become unsupported when added alongside invoice workflow on all four providers. | Plan all delivery units and shared dependencies, then compose provider lowerings with resource/address/output conflict checks. Do not merely remove the missing-work gate. |
| Application runtime | Real identity, durable work, isolation, recovery and private-byte mechanisms with local evidence | Invoice/private-document mechanisms are useful engineering, but substantial behavior is packaged inside particular application families. Their existence does not demonstrate arbitrary workflows or new combinations. Pending Azure node/pool work is unqualified; remote writes can outlive local cleanup, requiring a reusable write-settlement contract. | Extract independently testable identity, approval, job, object lifecycle, retrieval and integration blocks. Preserve domain-specific policies as adapters and regression fixtures. |
| Handoff | Artifact hashes, traceability, concrete implementation maps and generated tests | `src/spec-kit.mjs` enriches known invoice paths with concrete tasks/contracts; other unsupported work still receives implementation tasks instead of a finished implementation. Exact bytes/static completeness are necessary but do not establish behavior. | Generate every handoff from the same composed work model; reconcile requirements, code, Terraform, interfaces, runbooks and independent checks. |
| Knowledge and skills | Versioned registry, provenance, reviewed guidance and private/shared separation | `server/skills.py` includes stale S3-only capability summaries; actual selected specialist instructions and capability catalogue must be reconciled. Retrieval/evidence selection is not proof of architectural judgment or transfer. | Applicability, version/freshness and contradiction checks; teach why blocks fit/fail. Test retrieved practices against unfamiliar constraints, not record counts. No model-weight training has occurred. |
| Evaluation | Real runtime driver, immutable transcripts/exports, independent static assessor | `scripts/evaluate-convergence.py:78` adds ownership/question coaching; technical replies also redirect the model. Frozen seven families are visible development tests. `scripts/assess-convergence-package.py` explicitly performs static checks only. Existing baseline: 28 completed, zero qualified complete cases. | Separate coached diagnostics from uncoached product tests; freeze unseen family/composition holdouts, mutation tests and independent runtime/security checks. Report provider/difficulty strata and all failures. |

## Executed counterexample

`evidence/20261111-review/composition-probes.json` records four local probes:
AWS, Azure, GCP and IBM each recognize a standalone typed container. Add the same
independent container to an invoice workflow and it becomes unimplemented. The
required node is preserved and the gap is visible: this is a composition limitation,
not silent requirement deletion. Renaming/reordering keeps the observed limitation.
This tests compiler behavior only; it does not test model conversation, provider
schemas, application runtime or deployment.

A prior source scan found no seven benchmark-case-ID dispatch in production logic.
The benchmark path in invoice test generation bundles a fixture; it is not production
scenario selection. Absence of literal case IDs is insufficient: recipe-level
coupling still restricts generality. Do not delete legitimate domain adapters simply
because their names resemble an evaluation scenario.

## Reuse acceptance rule

Every engine change must identify: reusable capability/invariant; applicability and
limits; consumer interfaces; representative counterexample; transfer test with a
new domain or combination; independent behavior evidence. A scenario regression is
allowed, but the production fix must follow requirements/contracts, never its case ID,
fixture name, expected answer or benchmark-specific prompt. Do not rename a recipe
"generic" while retaining the same hidden business assumptions.

Classify code as shared mechanism, provider adapter, domain policy, evaluator or test
fixture. Domain/provider code may remain specialized where the distinction is real;
its contracts must be reusable and composable. Shared code must not import evaluation
case files at runtime. Preserve existing supported behavior during extraction.

## Review completion gates before feature expansion

1. Inventory remaining planner, discovery, knowledge, UI/reducer, export and runtime
   paths, including duplicated source/embedded-runtime generation and qualification.
2. Run uncoached fresh conversations for AI and non-AI briefs, existing systems,
   simultaneous demands and changed constraints; retain transcripts, timing, questions,
   proposals and scope checks. No case-name or hidden answer coaching.
3. Map known runtime evidence to exact capabilities/providers and test missing
   composition boundaries, failure paths and extraction candidates.
4. Freeze independent holdout families and manual release acceptance before tuning.
5. Publish prioritized review addendum and begin release 1 shared-engine changes.

No claim is made yet that fresh conversation quality has improved, that 1,000
combinations work, or that the general-purpose engine is finished.

## Fresh uncoached product probe: first-turn observation

A community equipment-library brief (non-AI, Azure, Australia, existing website and
member spreadsheet) was submitted through the actual CLI-backed Architect runtime,
skills and product reducers with isolated review memory. The prompt contained no
benchmark ownership/question coaching. The first response proposed seven relevant
components, recognized no AI was required, preserved existing systems and asked a
material membership-admission question rather than a port/startup question. This is
positive evidence for broad intent reasoning on one probe, not generality proof.

The emitted first proposal was then passed directly through resourcePlan and
terraformSketch. The existing website/browser are covered; the spreadsheet and all
four proposed application/data/identity/email components are unimplemented, with
infrastructureComplete=false. This concretely exposes the reasoning-to-implementation
boundary. Missing implementations remain visible rather than falsely accepted.
Full requests/responses and the compiler diagnostic are under
`evidence/20261111-review/fresh-conversation/`. The second turn introduces shared
emails, offline returns, inspection-before-reloan and budget; its outcome must be
reviewed separately. This visible diagnostic is not a frozen holdout and cannot be
reused later as independent unseen-quality evidence.

### Second-turn observation

The second response retained shared email constraints, proposed distinct member IDs,
added offline synchronization/idempotency and inspection holds to component contracts,
and recorded the running budget without asserting affordability. It asked whether
volunteers use shared library devices or personal phones, a relevant security
boundary. Both turns preserved scope through the product reducers. Observed latency
was 80.41s then 63.77s: short prose alone is not fast convergence. The application
still requires custom implementation; no working package is demonstrated. This
supports keeping the broad reasoning foundations while repairing shared composition,
implementation selection and feedback latency, rather than replacing everything or
claiming the engine is already general.

## Knowledge carriage follow-up

The composition skill (`agent-skills/specialists/composition/SKILL.md`) already teaches
responsibilities, interfaces, ownership, failure behavior, applicability, alternatives
and verification. `server/skills.py` loads full, SHA-checked/versioned instructions;
its short catalogue summaries are separate and can be stale. Selection is rule-based
with an eight-skill cap, so selection coverage and omission effects need tests.

`server/engineering_knowledge.py` loads the local reviewed catalogue, validates pinned
source revisions/content digests and local proof receipts, publishes records into
AtMem and checks retrieved practice equality, provider applicability and freshness.
These mechanisms carry reviewed knowledge without training model weights. The current
catalogue contains 20 records, two locally tested and eighteen source-reviewed; those
counts describe storage, not breadth or demonstrated expertise.

Additional audit risk: context limits content with `[:3000]` and eight records. All
20 current serialized practice records are below 3,000 characters, so no current
practice truncation was demonstrated. Future longer records could lose conditions
or limits after identity checking; replace silent clipping with explicit structured
summaries/index retrieval or explicit rejection before growing the corpus. Non-practice
keys are also admitted as untrusted retrieved evidence: trace their producers and
ensure they cannot impersonate reviewed practices. Provenance checks are useful but
are not a semantic applicability/contradiction evaluator or proof the planner used a
practice correctly. Review must cover the full source → memory → context → decision
→ executable contract → verification chain.
