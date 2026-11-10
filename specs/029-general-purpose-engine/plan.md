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
These are reserved candidate identifiers, not published versions. The current package
version remains unchanged. Critical fixes may have patch candidates; evidence always
binds exact commit/artifact rather than a moving label. Remote publication/deployment
remains a separately authorized action.

## Subgoals and acceptance

| Subgoal / candidate | Tangible improvement | Required automated evidence | Owner manual test |
|---|---|---|---|
| 1 — 10% / alpha.1 | Coherent general-purpose intake: system purpose first; recommends routine engineering; concise progress and only material questions. | Finish review; uncoached AI/non-AI and existing-system transcripts; retain all constraints; no forced ports/startup questionnaire, no generator-error delegation. Compare frozen baseline and latency/question burden. | Start a fresh project in your own words; add several demands; see a useful architecture proposal and clear next action. |
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
The rubric is proposed; it has not yet been frozen or achieved.

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

## Current position

Review source findings and four composition counterexamples are recorded. The broad
review and fresh uncoached conversation audit are still in progress. No subgoal is
accepted, no quality percentage is established and no new software release has been
made. Preserve pending Azure work as an unqualified checkpoint; do not continue that
specific workflow until the review sets the reusable capability priorities.
