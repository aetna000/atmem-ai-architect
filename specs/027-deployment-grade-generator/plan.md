# Deployment-grade architecture generator

Status: in progress; implemented slices and their evidence are tracked in progress.json. Full provider/scenario coverage remains unfinished. Owner request: improve the generator,
not individual exported bundles. No cloud deployment is authorized by this plan.

## Outcome

An engineer receiving a supported export can understand its design, inspect complete
infrastructure and application boundaries, supply account-specific inputs, execute
documented checks and proceed to an explicitly approved staging deployment. They
should not need to reverse-engineer chat history, repair the provider selection,
invent interface contracts or discover that claimed implementations are placeholders.

The target covers AWS, Azure, Google Cloud and IBM. Existing systems and hybrid
boundaries must be preserved. Capability must grow through implemented and tested
patterns; restricting exports or adding warnings alone does not achieve this goal.
Support for a pattern on one cloud is never evidence of support on another.

## Quality contract for every export

### Terraform

- Correct provider(s), resource types and reviewed provider versions; deterministic
  addresses; lock files; no provider fallback or borrowed provider-specific tests.
- Explicit physical deployment units, separate from actors, data flows and existing
  application source. Existing source does not mean a cloud service already exists.
- Complete resources and connections for the declared supported scope: identities,
  least-privilege grants, network paths, configuration, secret references, logging,
  health checks, retention and recovery settings. No secret values in the ZIP.
- Account/region/name/image inputs with validation and realistic, clearly marked
  example values. No invented approvals, prices or implicit placement decisions.
- Separate reference, import and create/update modes. Referencing an existing system
  must not recreate it; importing requires an explicit ownership transition.
- Environment/state strategy, migration/import guidance where relevant, versioned
  application artifacts, build instructions, outputs and usable operator runbooks.
- Generated tests assert intended resources, wiring and negative/security properties;
  a test passing only because a review gate rejects everything is insufficient.

### Spec Kit

- A concise system brief, users, included/excluded scope and accepted decisions;
  conversation fragments remain provenance, not the system description.
- Full, lossless requirements and component descriptions. Unknowns and conflicts are
  explicit and linked to the affected implementation; no truncated sentences.
- Exact interfaces: endpoint/event schemas, identity, authorization, ownership,
  error responses, retries, idempotency, limits and compatibility.
- Each requirement links to components, code/module locations, Terraform addresses,
  implementation tasks and executable acceptance tests.
- Tasks identify actual files/modules to change, dependencies, outputs and concrete
  completion evidence. No generic repeated checklist for every service or browser.
- Application runtime/dependencies, storage schema/migrations, tenancy boundaries,
  cost assumptions, monitoring, backup/restore and rollback procedures.
- Explicit distinction between supplied application code, generated code, referenced
  external services and unimplemented behavior. Referencing a container image is not
  proof that its application implements authentication or business requirements.

### Evidence

- Manifest ties source design, decisions, compiler, skills, provider schemas,
  generated files and checks to one immutable artifact digest.
- Checks separate schema/static, provider-mock, local runtime/integration, account
  plan and deployed-system evidence. Skips, stale receipts and missing credentials
  are not passes. No network probe of arbitrary diagram URLs during generation.
- Export preview shows findings before download, with a targeted correction or a
  precise missing implementation. Do not present an empty gate as infrastructure.
- A design-only handoff remains available, clearly named. A deployment candidate
  requires the mandatory checks for its pattern and no unresolved required behavior.
  This label still does not mean production deployed or account-plan approved.

## Architecture of the fix

1. **Lossless design model:** retain requirements, provenance, existing-system
   ownership, physical deployment units and supplied/generated artifact identities.
2. **Skill-guided planning:** select architecture, provider, Terraform, security,
   FinOps and workload skills against the design; record skill IDs/versions/digests
   and resolved decisions. Use current primary sources for changing cloud facts.
3. **Capability registry:** each implementation declares provider, accepted typed
   nodes/edges, prerequisites, generated artifacts, required inputs, tests and known
   boundaries. Skills and UI use this same registry; no separate optimistic claims.
4. **Typed compilers:** compile provider-neutral intent through the selected provider
   and workload adapters. Reject conflicting selections; preserve scope and ownership.
   Add real missing implementations rather than rewriting the request into a smaller
   supported example. Separate infrastructure coverage from application coverage.
5. **Independent verifier:** inspect the output, not just compiler success. Compare
   expected and emitted resources/edges, validate provider schemas, check secrets,
   run applicable tests and verify requirement traceability and document consistency.
6. **Bounded repair loop:** use actionable findings to repair code/configuration and
   regenerate, then rerun affected checks. Reject removal of requirements, weakening
   of tests or clearing gates as a repair. Stop with a precise blocker after a bounded
   retry budget; never repeat a vague coaching loop indefinitely.
7. **Evidence-aware packaging:** generate Terraform and Spec Kit from the same model
   and verification receipt. Export only current evidence; never edit a fixture ZIP.

## Delivery stages: simple to complex

| Stage | Capability to deliver | Exit evidence |
|---|---|---|
| 0 — Correctness foundation | Reproduce r13 defects; provider dispatch across all four clouds; no truncation; distinguish existing source from existing deployment; meaningful briefs and accurate readiness | Regression fixtures reproduce old failures; corrected fresh exports have correct providers, intact descriptions and honest coverage; previous supported scenarios remain green |
| 1 — One deployment unit | Existing references, single private storage resource, single container/function with a defined application artifact; provider-specific inputs, identity and lifecycle | For every advertised provider-pattern pair: generated code parses, provider schema validates, positive mock plan and negative policy tests pass; actual local runtime test where applicable |
| 2 — Connected application | Web/API + compute + persistence + secrets + service identities, with explicit edge contracts; buildable runtime packaging | Local end-to-end request/storage flow, denied-access tests, artifact build, resource/connection coverage and usable Spec Kit tasks; no dangling required edge |
| 3 — Secure hosted product | User sign-in, server-side authorization, tenant/project isolation, durable memory adapter, abuse controls and observable operational behavior | Anonymous/other-tenant/expired-token denial, concurrency and restart persistence, deletion/retention, security-rule and application tests; complete deployment/runbooks |
| 4 — Commercial and asynchronous workflows | Credit reservations/settlement, top-up integration, email flows, analytics consent, queues/events and retries | Concurrent spend cannot overdraw; webhook replay cannot credit twice; failed jobs reconcile correctly; payload/consent exclusions verified; selected vendors have implemented adapters |
| 5 — Complex AI systems | Retrieval/source connectors, model routes, long-running workflows, ACL propagation and human approval | Real generated application integration tests; injected outages and stale permissions; bounded model costs; recovery/cancellation; source/model fixtures clearly separated from live verification |
| 6 — Distributed and hybrid systems | Multi-region/multi-cloud, existing enterprise systems, migration and rollback, scale and disaster recovery | Cross-boundary contracts, failure/restore/load evidence, explicit residency/egress and identity mapping; no automatic equivalence between clouds; approved account plans before deployment claims |

Do not build every feature on one cloud and defer the others indefinitely. Stage 0
and the validation architecture cover all four clouds. Later patterns ship as explicit
provider-pattern matrix entries, with cross-provider regressions on every addition.
Unsupported service combinations enter the implementation backlog; they must never
be silently translated into AWS storage or declared supported by a generic template.

## Initial work packages and dependencies

1. **GEN-001 Baseline and fixture suite** — preserve the original r13 bundle read-only;
   add a sanitized source fixture and minimal AWS/Azure/GCP/IBM/mixed/reference cases.
   Record current failures and supported baseline; establish artifact comparisons.
2. **GEN-002 Provider/capability dispatch** (001) — replace AWS/default-Google fallbacks,
   introduce capability/coverage contracts and provider-consistency verification.
3. **GEN-003 Lossless model and ownership** (001) — remove silent text truncation;
   distinguish existing code, external infrastructure, imports and proposed deployments;
   validate round trips through chat, storage, export and reimport.
4. **GEN-004 Skills and planning contract** (002,003) — connect skill selection to
   registry capabilities and structured design decisions; test selection and receipts
   across every provider and increasing workload complexity.
5. **GEN-005 Terraform verification pipeline** (002) — schema/static, provider-mock,
   coverage/security and immutable receipt checks; prohibit incorrect export claims.
6. **GEN-006 Spec Kit compiler** (003,004) — concrete interfaces, code paths, acceptance
   criteria, dependency graph, operations and requirement-to-test traceability.
7. **GEN-007 Single-unit implementations** (004,005) — complete and validate Stage 1
   patterns for each advertised cloud, with actual runnable artifacts where required.
8. **GEN-008 Connected-system implementations** (006,007) — implement Stage 2 patterns,
   including application packaging and tests of each required connection.
9. **GEN-009 Hosted-product implementations** (008) — Stage 3, then Stage 4. Record
   unresolved vendor/account/scope choices; do not silently choose a payment/model
   provider or replace emailed-code sign-in with a different authentication flow.
10. **GEN-010 Complex-pattern expansion** (009) — Stage 5 then Stage 6, one tested
    workload/provider combination at a time, preserving all prior baselines.
11. **GEN-011 Export UX and release qualification** (005,006; repeated with 007–010) —
    pre-export results, actionable repairs, fresh evidence, sample ZIPs and cold-start
    recipient verification. Candidate export requires a passed clean-room review.

## Reference acceptance projects

- Empty/ambiguous/mismatched provider designs: clear findings, no fabricated resources.
- Existing website + external browser: preserved reference, no import/provisioning.
- Single store and single compute/container cases for AWS/Azure/GCP/IBM.
- Web/API/data scenarios with and without an existing front end, on each provider.
- User's Architect-to-atmem.ai design: preserved website, correctly modeled new hosted
  deployment, authentication, memory, credit/payment and analytics requirements intact.
- Multi-tenant retrieval, event-driven jobs, vendor connectors and mixed-cloud systems.
- Adversarial fixtures: conflicting regions, stale evidence, unsupported service names,
  long descriptions, missing edges, secrets, permission expansion and attempted scope
  removal. Include graph/name/order changes to test determinism and identity stability.

## Definition of done for a near-deployment export

The recipient can unpack into a clean environment, follow START_HERE, supply only
documented destination/business inputs and execute the included build, Terraform
validation and local tests. Every required behavior is implemented or references an
explicitly supplied external artifact with an acceptance contract. There are no hidden
generator gaps, wrong-cloud resources, missing files, untraceable tasks or invented
test results. A separately authorized account plan and staging validation remain
mandatory before claiming deployment readiness in that actual environment.

No milestone is complete because documents exist, a model says it is correct or a
review gate blocked a plan. Record commands, versions, observed results and limitations.

## First execution batch

Complete GEN-001–003, then GEN-005 and GEN-006 alongside skill integration GEN-004.
Review newly generated minimal exports for all four clouds and the unchanged r13
fixture before expanding runtime capabilities. Show concrete before/after artifacts
and passed checks at each batch; do not wait until the most complex scenario to find
basic generator defects. Do not deploy or modify the user's original exported bundle.

## Governing refinement: knowledge-informed architecture

Read CONSTITUTION.md. The owner clarified that public projects should teach Architect
reviewed engineering practices; the product should design, build and verify a tailored
solution rather than copy a public repository into the user's project.

The central pipeline is: client discovery → source-backed practice retrieval through
AtMem → architecture and trade-off planning → typed generation/composition → independent
verification and bounded repair → traceable Terraform/application/Spec Kit package.
Existing compilers and the capability registry support this pipeline.

Next knowledge work: source qualification and review, evidence-level records, semantic
retrieval and applicability ranking, source/version freshness, conflict handling,
knowledge-use receipts, adversarial retrieval tests and evaluation of complete exports
against unseen client scenarios. Start locally; shared/cloud hosting follows only after
identity, tenant isolation and operational requirements have an implemented contract.


## Architecture harness implementation checkpoint

Owner clarified that the product builds reusable architecture judgment, not a target
number of memorized projects. The composition specialist is always considered before
provider selection. Security guidance is also selected for trust-boundary questions
before a diagram exists. AtMem retrieval passes bounded, provenance-linked practice
contents with freshness/provider/tamper checks; full local skill instructions remain
separate from short knowledge index records.

Existing-source/create ownership, lossless record limits, unsafe-generation admission
and exact-file export receipts now have regression coverage. See
`evidence/20261110-harness-qualification-r2/README.md` for the current source/evidence
snapshot. Previous evidence snapshots remain historical. No deployment is authorized.

Three bounded live reasoning scenarios exercised access boundaries, concurrent credit
processing and autoscaled durable memory. They are observations, not an independently
scored benchmark. They exposed missing pre-diagram security selection (now fixed), and
the responses still asked questions despite the evaluation requesting none. Keep that
instruction-following limitation visible. These cases cannot establish general expertise
or qualify application generation. Next implementation work remains concrete connected
contracts, application behavior and cross-provider runtime evidence under GEN-008/009.

## Component-first interaction refinement (owner instruction, 2026-11-10)

Keep topology reasoning and grouping in the engineering model. Users work with
plainly named components and their connections in one component canvas, and open
component details when needed. Architect proposes the necessary components from
known requirements rather than asking users to assemble or understand a topology.
Existing ownership, IDs, services, requirements and connections remain authoritative;
removing the overview control does not change deployment semantics or authorize
model proposals, cloud deployments or runtime validation claims.

Implemented: overview switch and editable topology grouping removed; old saved
overview preferences reopen as components; Escape returns from details without
opening topology. Both server and client guidance now express this interaction.
Validation: 12 canvas/component unit tests, 5 server abstraction tests, production
build and both real-browser checks (component canvas and sequential component
review, including mobile layout) passed. Browser checks use
synthetic API fixtures and do not establish live-model component selection quality.


## Live convergence evaluation and vertical slices

Plan 028 runs the owner-requested 28-project matrix and preserves the original source,
transcripts and failed exports. Single-unit and connected work proceeds per qualified
provider/capability slice; this does not mark global GEN-007/GEN-008 complete. The first
repair adds generic bounded structured output and an AWS authenticated web composition,
verified through emitted builds, application tests, actual provider schemas/mocks and
explicitly scripted local emulation. Other providers and complex behavior remain work.
See ../028-convergence-evaluation/decision-log.md and progress.json.


### Invoice public-export checkpoint

The four-provider invoice composition, explicit interface/state contracts and
portable acceptance/Spec Kit phases are implemented locally. Current evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-public-export.
Next qualify actual complete live conversations and exact resulting handoffs/
runtime, then continue the remaining medium/hard families and full28/held-out.
Fixture/schema/mock passes do not complete business cases or authorize deployment.

### Exact live invoice artifact checkpoint

Fresh IBM rerun and independent static checks passed. Four actual live exports
passed native schema/mock validation (42 plans) and their delivered portable Linux
application tests (333 checks total, real loopback PG18; explicit cloud fixtures).
Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-live-native-v3. Six artifact admission regressions and 343 JS tests pass.
Zero complete medium cases counted until composed semantics/recovery/security are
reconciled. Remaining families and final full28/held-out work remain in progress.

### Composed live-export workflow checkpoint

All four actual live application sources passed 15 composed local checks each with
real PDF/OCR, local model, restricted PostgreSQL and loopback TLS; identity/storage
remain explicit fixtures. Exact artifact admission and parser source/lock matching
precede execution. Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-live-workflow-v1. 345 JS tests pass.
Recovery/security/native-cloud boundaries and full project qualification remain open;
continue remaining families and final full28/held-out evaluation.
