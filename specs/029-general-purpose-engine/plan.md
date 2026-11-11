# General-purpose engine: ten tangible release subgoals

Owner direction, 2026-11-11: the deliverable is an architecture engine that can
produce the original 28 projects and many unfamiliar combinations, targeting 95%
quality. The 28 projects are diagnostic/regression workloads, not production templates.
This programme governs the order of work in specs 027/028; it preserves their scope.
First complete the comprehensive review in review.md before extending specific workflows.

## What the percentages mean

Ten increments divide the agreed improvement programme into reviewable subgoals:
10%, 20%, … 100% are **roadmap completion**, not measured quality percentages.
Each increment must ship working software, exact validation evidence and a runnable
local version for the owner. A plan, renamed abstraction or passing unit-test count
alone cannot earn a release. No version is released by writing this document.

Proposed local prerelease series: `0.2.0-alpha.1` through `0.2.0-alpha.10`.
Alpha.1 and its patch alpha.1.1 are offered locally; alpha.2 through alpha.10 remain reserved. Remote publication has not occurred. Critical fixes may have patch candidates; evidence always
binds exact commit/artifact rather than a moving label. Remote publication/deployment
remains a separately authorized action.

## Subgoals and acceptance

| Subgoal / candidate | Tangible improvement | Required automated evidence | Owner manual test |
|---|---|---|---|
| 1 — 10% / alpha.1 | Specialized persistent native Codex engineering session, relevant skills and coherent user intake; capable local file/tool work behind simple progress. | Finish review; qualify project/workspace isolation, thread resume/steering, actual skill/tool use, exact model/effort and artifact capture. Freeze paired native baseline before tuning. Test uncoached briefs, concise progress and ownership. No release claim from transport tests alone. | Start a fresh project, add several demands while it works, observe the engineering progress and inspect/run the generated Terraform and local tests. |
| 2 — 20% / alpha.2 | Shared architecture work model: intent, responsibilities, delivery units, interfaces, assumptions, ownership and evidence. | Version/migration and save/reload tests; changing a requirement invalidates affected decisions/evidence without deleting scope; UI and export agree. | Edit a block requirement, save/reopen and see precisely what needs reevaluation. |
| 3 — 30% / alpha.3 | Capability composition replaces whole-project recipe selection for the first shared building blocks. | Standalone and mixed capability tests across four clouds, renamed/reordered/new-domain variants, resource/address collision and dependency checks; supported mixed units compile without suppressed gaps. | Add an independent service to an existing workflow; both remain implemented with clear interfaces. |
| 4 — 40% / alpha.4 | Provider-aware lowering and lifecycle ownership for those composed capabilities. | Exact provider schema checks, negative identity/network/region tests, reference/import/create preservation, adapter parity report and no provider fallback. | Bring an existing website and new backend; inspect what is preserved versus built. |
| 5 — 50% / alpha.5 | Reusable application and data contracts: APIs, identity, approvals, persistence and asynchronous work. | Extract shared mechanisms without regressions; clean-build and positive/negative integration tests for new combinations, tenant/authorization/idempotency invariants. | Try a workflow in a different business domain with the same mechanisms; inspect/run its package. |
| 6 — 60% / alpha.6 | Architectural judgment controller evaluates and repairs concurrent work at the appropriate abstraction level. | Independently detected requirement/interface/ownership failures trigger targeted repair; controlled stop conditions, no oscillation or scope deletion; changed/simultaneous demands tested. | Change a major requirement mid-conversation; see the design adjust and a short explanation of the trade-off. |
| 7 — 70% / alpha.7 | Knowledge-guided expert choices with applicability, alternatives and verified limits. | Pinned sources, freshness/conflict filters and retrieval tests; paired uncoached runs demonstrate useful transfer under the same model/resource budget; missing evidence remains visible. | Ask why a block was chosen and give a constraint that makes it unsuitable; see an appropriate alternative. |
| 8 — 80% / alpha.8 | Coherent reproducible Terraform, application code and actionable Spec Kit handoff. | Clean unpack/build/test, requirement-to-code/resource/test reconciliation, immutable artifact receipts, runbook/rollback checks and no unexplained placeholders for supported scope. | Export an unfamiliar combination and follow the generated local build/test instructions without repairing it. |
| 9 — 90% / alpha.9 | Reliability, recovery, isolation and operating behavior composed across supported providers. | Failure injection, retries/uncertain outcomes, remote-write settlement, backup/restore, tenant isolation and security regression tests. Local/mocked/account evidence explicitly separated. | Interrupt a local workflow, recover it and verify duplicate actions/access/data lifecycle behavior. |
| 10 — 100% / alpha.10 | Release candidate demonstrates generality plus depth with independently assessed results. | Rerun all original 28 plus untouched holdouts and generated constraint/composition variants; report every provider/difficulty, complete-project outcomes, interaction burden, failures and evidence levels. Meet agreed quality rubric or remain a candidate and repair. | Use your own unseen project, inspect output and give acceptance feedback before stable release. |

Subgoals have dependencies, not arbitrary calendar promises. Each release retains
previous subgoal checks and critical invariants. Four-provider ambitions are not met
by a successful AWS example. If a check fails, repair the engine and regenerate;
never hand-patch the export, coach the test or silently narrow the brief.

## Measuring the 95% target

Freeze the rubric and holdouts before implementation tuning. Report a vector:
constraint retention; architecture/interface correctness; executable package quality;
security/ownership; operational evidence; interaction burden; transfer/generalisation.
Use independently executable checks and reviewed judgments with explicit denominators.

Proposed release target for owner review: at least 95% of applicable noncritical
acceptance checks **within each provider/difficulty stratum**, alongside complete-
project acceptance rates. All applicable critical security, ownership, secret-handling
and must-have scope checks must pass; skipped, blocked or untested work is not a pass.
Do not use a weighted average to hide a broken project/cloud or claim 95% of all
possible systems. Confidence and sample coverage accompany every generality claim.
Engineering measurement protocol v1 is frozen in `benchmarks/engine/evaluation-contract.json`; the95% target has not been demonstrated.

"1,000 combinations" expresses broad transfer, not a promise proved by enumerating
1,000 renamed fixtures. Test unseen families, capability combinations, existing-system
boundaries and requirement mutations; deduplicate equivalent cases. Keep a frozen
holdout away from production selection logic and tuning. Disclose holdout exposure
and replace contaminated sets before making independent claims.

## Every release delivered to the owner

Provide a versioned local Git tag/build or reproducible bundle; exact commit and
artifact digest; local start command and verified address; changelog with visible
before/after behavior; automated results and their evidence level; a short manual
test card; known limitations and rollback instructions. Start and smoke-test the
local candidate before reporting its address. Track offered, manually tested and
owner-accepted separately. Do not block routine authorized development waiting for
optional manual feedback; incorporate feedback into the next candidate.

## Current implementation

GE-002 implementation and automated scope are complete. First increment and patch
alpha.1.1 remain available on frozen708d6a4 at http://127.0.0.1:5280; owner manual
acceptance is pending. One original AWS project locally qualifies against the frozen
protocol after one disclosed bounded native repair; the other 27 remain unqualified.

GE-003 is in progress. A versioned shared context/dependency model, retained review
history, proposed mapping import, scoped invalidation, ordered native client intent,
UI/export consistency and new pinned producer schema have component and real-browser
fixture evidence.393 JS / 388 server tests and build pass. Native current-context
revisions and artifact-bound graph/file reconciliation remain unfinished; no alpha.2
release is claimed. See `evidence/20261111-work-model-foundation/README.md` and
`docs/architecture/architecture-work-model.md` for limits and next actions.

GE-001A prospective holdouts/comparison, remaining nine increments and all original
provider/difficulty strata plus unfamiliar combinations remain in scope. Previous
implementation status notes are preserved in `implementation-checkpoints.md` and
exact evidence directories rather than presented as current counts.

## Local emulation acceptance — explicit owner clarification

The owner requires validation of individual blocks and the connected system through
local emulation; real cloud deployment is not required. This applies to the whole
programme, including the final 28-case acceptance. Account plans/deployed tests remain
separate optional evidence levels, not prerequisites for completing the authorized
local programme. Native cloud behavior that local emulation does not cover must be
stated precisely; do not imply it has been proven or use that limitation to avoid
implementing executable local contracts and journeys.

For every supported block, execute generated implementation against local real or
emulated dependencies, including success/denial/failure behavior. For connections,
exercise producer/consumer schemas, identity, authorization, retries/idempotency and
partial failure. For the whole system, execute requirement-linked user journeys,
including concurrency, isolation, state transitions and recovery. A mock's acceptance
or a standalone block pass cannot establish system acceptance. Track expected versus
executed behavior, failed/blocked/unsupported checks and the exact generated artifact.
Use independently authored acceptance oracles in addition to generated tests.

## Specialized native engineering session — owner direction

The owner requires a capable specialized Codex session, not a weaker model wrapped in
an architecture questionnaire. Use the native harness for persistent sessions, skill
selection, file/tool work, local validation and repair; augment its native instructions
with reviewed infrastructure knowledge instead of replacing its agent loop. Keep
short user-facing progress separate from internal engineering work and structured
canvas projections. The output language cannot be limited to a closed list of
business recipes. Existing verified adapters remain useful dependencies/regressions.

Selected first adapter: official Codex app-server protocol, initially exercised on
the development machine. It may run in an isolated backend worker later; it is not
a browser/client-computer dependency. Use backend-owned authentication, project-bound
persistent threads, progress events and steering/resume.
Do not extract OAuth tokens or implement custom login. Hosted execution and model
authentication use a supported backend integration when implemented; do not turn on
paid or cloud services merely to qualify the local foundation.
The transport foundation is not workspace isolation or product integration. Qualify
local file/network/tool boundaries before enabling engineering turns through the UI.
No deployment tools or cloud credentials are required for local generation/emulation.

Require exact selected model and reasoning effort in run receipts; no silent downgrade
or fallback. Compare stock native Codex and the AtMem-specialized session on identical
briefs, model/effort, local tools, repair budget and independent criteria. Include the
current restricted JSON chat path as a diagnostic, not the target baseline. Measure
actual artifacts, executed checks, constraint retention, question burden, latency and
cost. Skill invocation counts alone are not quality. Use reviewed infrastructure
skills to improve engineering, not to coach evaluation answers.

Terraform acceptance covers provider/schema/lock correctness, complete resources and
connections, identity/network/secret boundaries, explicit ownership/state/lifecycle,
correct configurable inputs and operational instructions. Run init/validate/tests
against pinned local providers as applicable; independent checks must detect missing
scope and unsafe behavior even when generated tests pass. Couple infrastructure
acceptance with generated application block/connection/journey emulation. No account
plan or cloud deployment is needed for this local release target.

## Web deployment portability — explicit owner constraint

The engine must support a cloud-hosted web application later. The browser submits
intent, project changes and attachments to an authenticated session service; it does
not run a CLI, supply filesystem paths, hold model credentials or need a local helper.
The session service owns tenant/project authorization, session/job identity, steering,
progress, cancellation and artifact access. An isolated worker owns the engineering
workspace, native harness adapter, reviewed skills and local validators/emulators.
Workers can run on a developer machine or backend infrastructure through the same
semantic session contract. Artifacts and evidence use project-bound IDs/digests,
not client-local paths or a provider's thread ID as authorization.

Keep four separations explicit:
1. Web UI/session service versus execution worker.
2. Engineering backend/model versus the target AWS/Azure/GCP/IBM architecture.
3. Portable project/skill/artifact/evidence contracts versus adapter protocol details.
4. Worker storage/isolation versus durable project/session metadata.

The current internal `server/codex_app_server.py` is only a Codex protocol adapter;
its local subprocess launcher is the development transport, not the product core.
Introduce the backend-neutral session/job boundary alongside the first real worker
integration, qualify both local and hosted-worker transport contracts, and avoid a
Codex-only browser protocol. Other capable backends may implement the same contract;
no automatic lower-quality fallback is permitted. Cloud-hosting architecture is in
scope for design; actually deploying it is not authorized by this programme.

## Deployment modes and future commercial product

Owner confirmation: the same product must be runnable locally and as a cloud SaaS
for paying users. Build one engine and worker contract with deployment configuration,
not separate local/cloud product forks. Local installations can use a local worker;
a hosted web installation uses backend workers and backend-owned model authentication.
No end user needs Codex installed to use the hosted product.

Prepare for tenant/project isolation, durable sessions/artifacts, worker scheduling,
secret injection, cancellation/recovery and model/tool usage evidence. These are
execution/ownership concerns. Architect's own subscriptions, checkout and paywall are
explicitly deferred; do not add them to release 1 or treat missing payments as a blocker.
This does not remove metering/credit requirements in the client projects the engine
is tasked to generate. Hosting this SaaS remains future work, not a request to deploy.
