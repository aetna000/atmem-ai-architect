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
Alpha.1, its patch alpha.1.1 and alpha.2 are offered locally; alpha.3 and alpha.4 are now offered locally; alpha.5 through alpha.10 remain reserved. Remote publication has not occurred. Critical fixes may have patch candidates; evidence always
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

GE-003 implementation and automated local scope are complete. A versioned shared context/dependency model, retained review
history, proposed mapping import, scoped invalidation, ordered native client intent,
UI/export consistency and new pinned producer schema have component and real-browser
fixture evidence. Immutable current-context revisions now accompany existing native
work without changing original pins or client text.404 JS / 418 server tests, build
and browser checks pass. Two real native river-depth turns each pass18 independent
checks; the old package fails the changed unit requirement. Actual service/adapter
restart retains revisions and identical capture without inference replay.
Artifact-bound proposed mapping reconciliation now has component/browser and actual
native edit/regeneration evidence, including20 independent checks per package,
retained mapping versions and full Build restore. The frozen alpha.2 candidate
is verified and offered at5283.404 JS/418 server/build
and actual candidate version/model/draft/reload smoke pass. Two runnable increments
are recorded; owner manual acceptance remains separate and pending. See
`evidence/20261111-alpha2-candidate/README.md`, `evidence/20261111-context-revisions/README.md`,
`evidence/20261111-work-model-foundation/README.md` and
`docs/architecture/architecture-work-model.md` for limits and next actions.

GE-001A prospective holdouts/comparison, remaining seven increments and all original
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


Owner-requested alpha.2.1 patch priority: make Design the entry point, implement
Build this design using its saved context, and show durable public Architecture
activity during bounded model/tool turns. Preserve original native history and
no-replay recovery. Qualify this patch locally before resuming GE-004 composition;
it adds no roadmap increment or original-case acceptance. See
evidence/20261111-design-activity/README.md.


GE-004 checkpoint: explicit capability partitioner, registry and module linker are
implemented internally and qualified with429 JS tests, build,14 cached native-schema
packages and61 mock-provider plans. See evidence/20261111-composition-linker/README.md.
Keep public fixed dispatch until independent module-closure admission and actual
implementation-map/Spec Kit paths/DAGs are complete; never remove unreviewed-module
or missing-resource guards to promote the new output. Then qualify public exports,
additional combinations/counterexamples and a separate runnable alpha.3. This
checkpoint is not a new roadmap increment or whole-system acceptance.


Public composition checkpoint: default planner/compiler and all-unit handoff are
now wired behind independent owned-module admission.466 JS/425 server/build and
four actual provider schemas pass; see evidence/20261111-public-composition/README.md.
Actual service module-mock replay, combined-root assertions, browser exports and
the frozen runnable alpha.3 are the next dependency-ordered work. The prior internal
checkpoint's public-integration-pending status is historical. Owner storage direction
is persistent: use MEM0 for heavy ignored archives/cache data, retain stable local
read paths and keep active project stores/session logs/source local.


GE-004 local automated scope complete: alpha.3 frozen `ea11bf8` is offered on5285,
with473 JS/425 server/build, real HTTP/browser/native-unit validation and exact
source/archive/build identities. See evidence/20261111-alpha3-candidate/README.md.
Older checkpoints above remain historical. Three runnable increments are offered;
owner acceptance0, original complete local qualification1/28 and quality unknown.
Proceed GE-005 provider lowering/ownership, including explicit runtime constraints,
then all remaining contracts/judgment/knowledge/handoff/recovery/generalisation and
original28/unfamiliar full systems. Schema/mock checks do not establish application
runtime or connected-system correctness. No deployment required/authorized.


GE-005 checkpoint: exact byte-quantity memory/CPU lowering and independent artifact
inspection are implemented across four providers, with8 native schema packages/
40 mocks, earlier58 actual service module mocks,484JS/428server/build. See
evidence/20261111-provider-lowering/README.md. Explicit placement, environment/
network/identity/lifecycle/state policy and runnable alpha.4 remain required.
No new release, original complete-system acceptance or95% claim.


Owner-priority alpha.3.1 focused UI patch is offered at
http://127.0.0.1:5285/dist/index.html (same origin/data/backend). Actual Claude
consultation informed compact Design activity/history; owner rejected broader
Build/scrolling work, which was removed. atflow.css unchanged.480JS/425unchanged-
server/build/focused browser/live built-view pass. An active owner implementation
job prevents a service restart; keep it running. See
evidence/20261111-inline-activity-patch/README.md. This patch adds no increment or
original-case acceptance. Resume GE-005 region/ownership, then full programme.


GE-005 placement checkpoint: configured destinations are retained through standalone
and composed inputs/providers, with native read-only Azure environment and IBM
project region/identity checks and independent supplied-image footprint admission.
501JS/428server/build,12 native packages82 mock plans and70 actual service unit
mock plans pass. See evidence/20261112-provider-placement/README.md. Lifecycle
parity, deeper identity/network/state policy and frozen runnable alpha.4 remain;
three increments, original complete local qualification1/28, owner acceptance0,
quality unknown. No owner UI or running project was changed.


GE-005 ownership checkpoint: imported cloud-state metadata cannot become newly
managed container infrastructure via create mode. Frontend/backend validation and
four-provider counterexamples/regressions preserve existing-source deployment and
external reference boundaries.505JS/429server/build pass; all twelve qualified
placement artifacts remain byte-identical. See
evidence/20261112-imported-ownership/README.md. Full lifecycle/network/identity/
state parity and runnable alpha.4 remain outstanding.


GE-005 supplied-image safeguard checkpoint: native AWS network membership and
account/region-scoped role trust, independent actual IAM/task inspection and
four-provider lifecycle/image/provider/review protections.511JS/build,unchanged
429server,12 native packages102 mock plans and72 actual service unit mocks pass.
See evidence/20261112-container-safeguards/README.md. Read-only network membership
is not full routing/firewall/egress policy; lifecycle configuration is not state
custody or migration. Complete remaining parity/operations/browser/export before
runnable alpha.4; full programme and28/unfamiliar systems remain in scope.


GE-005 state-custody checkpoint: explicit environment/backend/owner/residency/
decision survives save/export and native context; state changes invalidate prior
context review. Shared backend factory retains the invoice compatibility policy,
independent root admission rejects diversion/credentials/forged acceptance, and
a concrete Spec Kit custody task precedes account planning.520JS/build,18 native
roots and68 actual service unit mocks pass; unchanged429server evidence retained.
See evidence/20261112-state-custody/README.md. No backend connection or migration
was performed. Local protocol/operations, remaining lifecycle/provider parity and
frozen runnable alpha.4 remain. Three increments,1/28 originals, owner0, quality
unknown; full programme remains required without cloud deployment.


GE-005 local state protocol checkpoint: root packages emit a byte-bound Python
checker with concrete instructions. Two exact unpacked helpers each pass18 real
native client/local SQLite fixture checks, including writer exclusion, owner-safe
unlock and checksum-verified recovery.521JS/build pass; project native configs/
tests/locks are unchanged. Both contexts use the same synthetic loopback HTTP
contract, not their selected-platform behavior; no custody acceptance/gates change.
See evidence/20261112-state-protocol/README.md. Continue remaining lifecycle/
reference/import and provider operating-policy parity before frozen alpha.4,
then the full remaining programme and28/unfamiliar local systems.


GE-005 lifecycle provenance checkpoint: exact supported Pulumi URNs/types survive
project/native context/export; explicit reference markers stay external beside
new source deployment. Native state adoption/move/removal and forged ownership
claims are rejected.529JS/build,72 actual service unit mocks and isolated browser
16 mocks/122 ZIP file hashes pass. See evidence/20261112-lifecycle-ownership/README.md.
Parity review exposed AWS China placement accepted by commercial ARN templates;
repair the retained counterexample before freezing alpha.4. No release/full-case
count changed. Full programme and28/unfamiliar local systems remain required.


GE-005 partition release blocker resolved: supplied-image ARN lowering now uses
native partition metadata across commercial/China/GovCloud identifiers; repository
partition/region-family and native metadata guards retain exact selection. The
commercial invoice policy remains separate blocked work for other partitions,
including independent protection against suppressed planner/root gaps.537JS/
430server/build,7 partition packages97 native mocks,12 four-provider regressions
108 mocks and53 actual service unit mocks pass. Identical-input frozen before
compiler fails the exact China ARN oracle despite8 generated passes. See
evidence/20261112-aws-partitions/README.md. Proceed frozen runnable alpha.4 and
actual candidate/browser/export/manual/rollback qualification; GE-005 remains
in_progress until that delivery. Full28/unfamiliar local systems and remaining
contracts/judgment/knowledge/handoff/recovery/generalisation remain required.


GE-005 local automated scope complete: frozen108981b alpha.4 is offered on5286,
with537JS/430server/no skips/build, two actual HTTP/browser cases49 unit mocks/
152 matched ZIP files, exact source/archive/build/manual/rollback. See
evidence/20261112-alpha4-candidate/README.md. Earlier checkpoint statuses above
are historical. Four increments offered; owner0, complete originals1/28, quality
unknown. Continue GE-006 reusable application/data contracts and full remaining
programme. Native configuration mocks are not application or cloud acceptance.
State adoption and selected backend behavior remain unqualified. Owner5285 and
UI/AtFlow CSS untouched during this release qualification.


GE-006 checkpoint: shared immutable bounded application input/result contract binds
to durable destination/approval identity. Changed-contract pending work cannot be
claimed by the repaired runtime. Two domains cross real PostgreSQL/Procrastinate/
human approval and synthetic TLS destination; exact emitted application repeats
the checks. See evidence/20261112-application-contracts/README.md. Generic model
selection/API/identity/persistence/bootstrap and connected full application tests
remain before alpha.5. Current invoice validation remains its own domain policy.
Four increments, original complete cases1/28 and owner0 are unchanged.


GE-006 HTTP checkpoint: a typed generic API now admits data into the shared durable
workflow, lists/reads its state and enforces revision-bound review/approval. Server
owns account/kind/origin and identity transport; SQL membership remains live.16
new tests include two-domain ASGI intake through real queues/workers and synthetic
TLS, concurrent duplicate HTTP requests, cross-account denial, membership revocation
during streaming and the actual body deadline.115 exact unpacked package tests
pass. See evidence/20261112-workflow-http/README.md. Continue shared model selection,
provider-owned bootstrap/identity/database/async composition, full application
qualification and runnable alpha.5. Four increments/1-of28/owner0 unchanged.


GE-006 native assembly checkpoint: shared identity/database helpers now serve an
immutable owned application profile, with exact API/worker roles, issuer-scoped
membership and account/kind guards. The initial candidate allowed an older draft
approval after policy changed to supervisor-only; retained counterexample now
rejects through full application-declaration binding.16 bootstrap checks, four
native identity profiles with real JWT crypto/separate local SQL roles and131 exact
unpacked package checks pass. See evidence/20261112-workflow-bootstrap/README.md.
This is local injected database/key-source evidence, not managed cloud acceptance.
Model selection, resource/environment linkage, entrypoints/domain implementations,
handoff and frozen alpha.5 remain. Four increments/1-of28/owner0 unchanged.


GE-006 selection checkpoint: complete node-owned declarations now pass structured
producer/browser validation and reach actual source/lock/container/API exports and
concrete Spec Kit tasks. Four exact selected entrypoints pass native JWT/SQL tests;
old-reader format3 rejection prevents silent intent loss.546JS/432server/build and
131 full-package regressions pass; see evidence/20261112-application-selection/README.md.
These are partial API assemblies with required domain/worker/resource work, not
whole applications or planner-quality proof. Intent-to-template/deferred native
bindings, provider/environment linkage, worker/domain implementation and full
requirements/handoff remain before alpha.5. Four increments/1-of28/owner0 unchanged.


GE-006 public binding checkpoint: templates preserve unknown native public outputs
as exact graph-owner/provider/environment references; the emitted isolated resolver
creates a fresh concrete profile plus receipt, and API startup rejects incomplete,
stale-policy or mismatched bindings before native setup. Separate Spec Kit binding
tasks follow source/component owners and precede connected acceptance with a checked
acyclic DAG. Four exact emitted provider-context APIs pass JWT/SQL tests;552JS,
434server/build and138 exact package regressions pass. Terraform/lock bytes are
unchanged on the same concrete/deferred graph, not newly schema-qualified here.
See evidence/20261112-deferred-bindings/README.md. Structural resolution does not
verify the supplied source or cloud. Provider resource/environment and executable
domain/worker linkage, full requirements/handoff and runnable alpha.5 remain next;
retain the complete remaining programme. Four increments/1-of28/owner0 unchanged.


GE-006 native runtime access checkpoint: the native engine now receives the same
shared production source and exact provider locks as optional pinned inputs, with
an offline portable materializer instead of merely prose naming unavailable modules.
A real virtualenv alias counterexample also exposed dependency loss; future native
and receiving registrations retain the selected environment behind a literal launcher
and require its read root. Real restricted-worker four-provider materialization/
imports,553JS/443server/build pass. A normal gpt-6.1-sol/high equipment-domain session
uses the supplied SDK and is being independently qualified; preserve its original
pins and observe the same job if an observation budget expires. See
evidence/20261112-native-runtime-access/README.md. This is not a frozen release or
whole-system acceptance; resource/domain/worker/connected handoff and alpha.5 remain.
Four increments/1-of28/owner0 and unmeasured quality are unchanged.


GE-006 equipment transfer qualification: exact gpt-6.1-sol/high completed one native
turn plus one bounded automatic repair. Latest captured source passes12 independent
real local SQL/queue/child/TLS checks and19 generated tests without skips; native AWS
schema/5 independent mock plans and clean offline Linux ARM64 image/factories pass.
The repair changes only documentation/diagnosis; all code/tests/build inputs match.
See evidence/20261112-native-runtime-access/assessment-v1.json. This is exposed source
journey/build component qualification, not whole-system or provider/holdout acceptance.
The backend's bare Python validator still lacks SDK/SQL prerequisites. Add an isolated
SDK/PostgreSQL validation fixture, run the complete image journey and equivalent
provider transfers before runnable alpha.5. Four increments/1-of28/owner0 unchanged.

GE-006 isolated SQL validation checkpoint: an operator-owned pinned image now gives
Python checks a fresh authenticated PostgreSQL17 instance inside their existing
isolated container. Neutral fixture variables, SDK dependencies and wrapped unittest
classification preserve missing/skipped/zero-test and prerequisite failure evidence.
Actual editorial/inventory transactions, role/auth/network/read-only denials, fresh
state, missing-fixture counterexample and timeout cleanup qualify the mechanism.
Backend catalogue registration and553JS/445server/build pass. Evidence:
evidence/20261112-isolated-sql-validation/README.md. Existing owner previews and
workspace pins are unchanged. Next activate only the separate idle synthetic preview
and qualify native test/report use, then actual application image/SQL/TLS and other
provider transfers. This checkpoint earns no release or whole-project acceptance;
four offered increments/1-of28/owner0 and unknown measured quality remain unchanged.

GE-006 native SQL and image checkpoint: the separate idle synthetic preview now
offers the qualified runtime. Same-session gpt-6.1-sol/high completed an explicit
test-environment adaptation,14 successful callbacks/three full22-test working
reports, and final archive22/no skips. No production source/locks changed and no
new automatic repair occurred. The independent unchanged Linux ARM64 image now
passes10 real HTTP/SQL/queue/child/TLS groups, exact36 runtime pins and fixture
cleanup. Synthetic native keys, local SQL injection, public ledger and CA remain
explicit; separate production tasks/native managed startup/full-project acceptance
are unproved. See evidence/20261112-native-sql-transfer/README.md and assessment-v2.
Next equivalent Azure/Google/IBM native transfers and full independent receiving
handoff/resource composition, then runnable alpha.5. All remaining ten-increment/
original28/unfamiliar scope and four offered/1-of28/owner0/unknown quality remain.
