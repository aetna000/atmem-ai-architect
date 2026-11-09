# AtMem expert architecture engine programme

Owner direction: build an exceptional architecture engine with broad engineering
judgment. Four initial practice records and a compiler pipeline are bootstrap work,
not the intended scale or demonstrated expertise. Existing implementation tasks remain
active; this programme supplies the learning and evaluation framework around them.

## Product target

A client describes a problem without knowing infrastructure terminology. Architect
elicits material constraints, identifies suitable proven patterns, reasons about
alternatives, builds a tailored implementation and delivers a coherent, independently
checked package with understandable decisions and operational responsibilities.

World-leading quality is an ambition requiring comparative evidence, not a product
claim established by the constitution, source count or a model's confidence.

## Knowledge programme: compositional expertise

Owner refinement: quality and the ability to use blocks govern this programme. No
fixed corpus size or project count defines expertise.

A lesson is a contextual engineering decision with source evidence, not a paragraph,
repository download or copied project. Capture problem, constraints, chosen approach,
alternatives, rationale, dependencies, security boundary, failure/counterexample,
applicability, versions, provenance and supporting tests. Preserve uncertainty.

Build stratified coverage across requirements and trade-offs; system boundaries;
identity and tenancy; networking; storage/data modeling and migrations; compute;
queues/events and idempotency; application/API contracts; AI/retrieval/agents and
memory; reliability/recovery; observability; cost/performance; IaC lifecycle; delivery
and operations. Include simple systems, evolving existing systems, enterprise/hybrid
systems, mistakes, incidents, migrations and rejected designs. Cover AWS, Azure,
Google Cloud and IBM without pretending their services are interchangeable.

Source cohorts: maintained module/reference repositories, cloud primary documentation,
well-documented open-source production systems, published engineering case studies,
and our own verified runs. Deduplicate related repos/forks; do not treat repetition
as independent corroboration. Review licensing and provenance. Never import client
secrets or private examples into a public/shared training corpus.

Promotion states: candidate → source-reviewed → locally-qualified → independently
cloud-qualified for a precise scope. Training eligibility is a separate reviewed
property; no automatic learning from raw client chats or successful-looking model
answers. Stale, archived, conflicting and revoked practices must be excluded or
presented as historical evidence. Human/expert or independently checked review
receipts must support the claimed promotion.

## Retrieval and reasoning

AtMem is the memory/knowledge layer. Retain linked source/evidence artifacts outside
short memory records. Retrieve by semantic relevance plus exact provider/version/
constraint filters. Add reranking, conflict detection, citation chains and freshness
policies. Measure retrieval on labeled questions; assess whether the selected lesson
actually supports the proposed decision. Recalled text is untrusted evidence, not
instructions or tool authorization.

Keep shared engineering knowledge and private user/project memory isolated. Local
operation comes first; shared cloud hosting requires its own identity, authorization,
tenancy, backup, deletion and operational implementation and tests.

Use specialist roles for architecture, security, data, infrastructure, reliability and
FinOps where evaluation shows a benefit. A coordinator resolves disagreement through
requirements and evidence. Extra agents/models must earn their latency/cost through
measured improvement; consensus between models is not independent proof.

## Evaluation before scaling or training

Freeze an initial held-out set of realistic client projects before tuning retrieval
or training. Split by project/repository family, not random snippets, to reduce
leakage. Keep private client material out unless explicitly approved and sanitized.
Expand held-out coverage when a new competency, workload or failure boundary requires it; include
adversarial requirements, unsupported combinations and changing existing systems.

Compare the same model and resource budget under:
1. Native baseline without our engineering retrieval.
2. Skills + AtMem retrieval.
3. Retrieval + specialist review + deterministic verification/repair.
4. A fine-tuned candidate with the same retrieval and verification budget.

Evaluate constraint retention, quality of clarification, architecture trade-offs,
provider/resource correctness, interface completeness, security/tenant isolation,
build/schema/mock/runtime outcomes, operational readiness, cost, latency and human
review quality. Use independent executable checks where possible and blinded expert
review for judgment. Separate plan correctness from deployed behavior. Report failed,
blocked and skipped cases, uncertainty, and the exact evaluated scope.

No training/test overlap, requirement removal, permission weakening, suppression of
failures or invented evidence may improve the score. No release may knowingly
introduce a regression in critical access/ownership/secret tests.

## Specialist model research

Start with a strong existing model plus retrieval and tools. Keep changing cloud
facts in versioned knowledge rather than relying on model memorization. Build reviewed
instruction examples for discovery, decisions, contracts, implementation and repair.
Build preference pairs from reviewed alternatives and rejected unsafe/incomplete
results. These are candidate SFT/DPO datasets, not automatically labeled ground truth.

Train an existing open-weight model only after choosing a compatible license and
establishing useful data, baselines and a bounded compute plan. Evaluate quality,
regressions, inference cost and latency on the held-out set. Adopt only a demonstrated
improvement. Training from scratch is not the initial strategy. No training run or
paid cloud experiment is implied or authorized by this design document.

References:
- Retrieval-augmented generation: https://arxiv.org/abs/2005.11401
- TRL training/evaluation tooling: https://huggingface.co/docs/trl/index
- IaC evaluation research candidate: https://arxiv.org/abs/2607.20478

## What we need and execution order

1. Corpus schema, provenance/evidence store, source roster, deduplication and review
   tooling. Grow measured competency coverage; do not optimize for record counts.
2. Benchmark fixtures, independent checks and a reproducible native baseline.
3. Retrieval/reranking and practice applicability improvements evaluated against
   frozen labels, then the current generator and concrete Spec Kit outputs.
4. Connected and increasingly complex workload implementations, qualified per cloud.
5. Reviewed feedback/repair datasets and a bounded specialist-model experiment.
6. Shared hosting and continuous source refresh only with tested access/operations
   boundaries; maintain versioned knowledge, models, compilers and benchmark receipts.

Need access to appropriate licensed sources, expert review capacity, isolated test
runners, a selected base model and an explicit R&D spending/account boundary for paid
training or cloud qualification. Routine local research and implementation continue
without waiting for those later access-dependent tasks.
