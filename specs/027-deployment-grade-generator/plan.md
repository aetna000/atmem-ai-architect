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

### Exact live invoice recovery/images checkpoint

All4 original live export sources pass actual logical restore (10 checks each),
native-plan API startup/denial plus restricted queue image checks, and native-plan
operator checks (9/12/12/12). Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-live-recovery-images-v1.
347 JS tests pass. Exact production scans each retain 47 HIGH open findings, zero
CRITICAL/fixes in cached metadata; no security acceptance or medium-case promotion.
Continue native source/permission-aware medium implementation and remaining families
while retaining unresolved security/native-cloud boundaries.

### Private native-source implementation foundation

Implement caller-delegated Graph/Confluence source reads and a fail-closed concurrent
retrieval coordinator with live pre-context/pre-release authorization and exact-quote
citations. 23 scripted native-contract/policy tests pass. Primary APIs reviewed and
hashed. Evidence: specs/028-convergence-evaluation/evidence/20261110-private-native-foundation-v1.
No export capability is advertised: trusted company identity/OAuth broker, extraction,
cloud models, durable audit and all4 native export/Spec Kit wiring remain unfinished.
Continue those dependencies, then all4 exact live runs, other families and full28.

### Private identity/native OAuth/store checkpoint

Implement fixed company API JWT verification, live company access gates, actual
MSAL Graph PKCE/cache/refresh, Confluence native confidential 3LO and encrypted
per-person SQL credentials. Durable refresh intent/revision fencing prevents blind
rotating-token reuse after crash/uncertainty and late disconnect reversal. 34
contract/policy/crypto/SDK tests and 16 real restricted SQL tests on each PG17/18
pass; JS347/server214 pass. Evidence: specs/028-convergence-evaluation/evidence/20261110-private-native-auth-v1.
Browser callbacks/session/CSRF, clean Linux dependency qualification, extraction,
model/audit and all4 native export wiring remain unfinished. No source/IdP account
or cloud operation ran; do not advertise the new capability or count a medium case.

### Private browser/API checkpoint

Implement company opaque sessions, CSRF/origin boundaries, fixed source callbacks,
parallel source credential/retrieval composition and a pinned OIDC/PKCE browser
workspace. Fix native cross-profile quota deadlock and late initial-consent
revocation race at their source. Local evidence: specs/028-convergence-evaluation/evidence/20261110-private-browser-api-v1.
34 policies, 36 SQL/API/session cases per PG17/18, 9 browser checks and JS347/
server214/build pass. Vendor/model/source HTTP is scripted; no medium/export or
native cloud claim. Next clean Linux/general-document/model/audit/provisioning and
all4 native export/Spec Kit wiring, then remaining families and full28/held-out.

### Private document-extraction checkpoint

Implement the pinned Tika/Java company-document bridge and separate byte-only RPC,
retaining the unchanged invoice PDF/OCR path. Actual local Linux evidence: specs/028-convergence-evaluation/evidence/20261110-private-document-extraction-v1.
16 parser/RPC/composition checks and 39 enterprise policies pass. Exact image retains
65 HIGH open findings; shaded-Java image scanning omitted its dependencies, so the
89 embedded Maven coordinates were independently inventoried/scanned with explicit
coverage limits. No security acceptance, capability registration or medium-case
promotion. Next async extraction/cache with live permissions and retention/recovery,
clean Linux app/model/audit/provisioning and native all4 exports; then remaining
families and final full28/held-out. Preserve synchronous latency/format limits.

### Private queued-answer checkpoint

The browser submits durable encrypted question jobs and polls/cancels/resumes them;
real Procrastinate execution no longer holds the question POST. Stored answer receipts
recheck current source selections/versions and company/session/domain authority at
release; changed sources requeue a fresh generation. Evidence: specs/028-convergence-evaluation/evidence/20261110-private-queued-answers-v1.
63 native SQL/API/worker checks per PG17/18, 45 policies, 11 browser checks, 16
restricted Linux document checks and JS347/server214/build pass. Source/model HTTP
remains scripted. No capability/medium-case/security promotion. Next encrypted
parser-versioned extraction cache with live authorization and retention/recovery,
clean Linux app/model/audit/provisioning, all4 native exports, remaining/full28/held-out.


## 2026-11-10: Authorized immutable extraction reuse

Encrypted company/parser/bytes/MIME-bound extraction reuse with fresh native source reads and live consent checks; fixed Disconnect/reconnect in-flight authority and host-clock queue scheduling. 89 native SQL tests per PG17/18, 12 browser, 16 restricted Linux parser, 14 composed checks; 347 JS/214 server pass. No medium case or new capability promoted; native packaging/model/audit/provisioning/per-file isolation/all4 exports/full28 remain.

Use HMAC identities and encrypted derivatives, committed builder leases, absolute expiry and bounded purges. Every question still reads current authorized source bytes; no permission, title, selection or outage fallback is cached. Consent generations fence both queued and legacy APIs, and credential ciphertext is bound to that generation. Normal refresh preserves consent. Immediate jobs use NULL readiness and delayed retries use the database clock. Fresh unreleased schemas only; no existing database migration.

Evidence: specs/028-convergence-evaluation/evidence/20261110-private-extraction-cache-v1. Retained failures show the original withdrawal and clock defects; actual Linux extraction uses fresh restricted containers per file. Long-lived parser RPC does not prove containment across future files. See docs/architecture/private-knowledge-extraction-cache.md.


## 2026-11-10: Clean Linux private application core

Clean Linux private core has 33 exact dependencies, 45 offline policies and 57 native SQL/crypto/queue/cache tests per PG17/18. Shared document validation is separated from parser code; rebuilt parser16 and composed queue/cache14 pass. Core image scan: 47 HIGH, zero critical and zero fixable HIGH/critical after the already reviewed hash-pinned base update; security remains unaccepted. Native models/secrets/audit/provisioning, per-file isolation, all4 exports, actual private/remaining cases and final28/held-out remain.

Evidence: specs/028-convergence-evaluation/evidence/20261110-private-linux-core-v1. Pin the reviewed full dependency closure and existing zlib fix; do not silently upgrade packages. Native tests import actual installed application files, without mounting host runtime/packages; synthetic fixture secrets enter only bounded tmpfs over stdin. Preserve VM-mount, missing parser-module and bare-image-ID BuildKit failures. Protocol split preserves public parser imports and limits. See docs/architecture/private-knowledge-runtime-core.md. This is not a configured service or a cloud/private-project pass.


## 2026-11-11: Native private operations, secrets and durable audit

Private native model/secret/audit adapters implemented. All4 real native serializers enforce the fixed private operation with scripted HTTP; cloud dependency images have 60 policies and 66 native SQL/crypto/queue/cache/audit tests per PG17/18. Expanded host API/worker suites101 per version, browser13 and actual Office/PDF queue/cache/audit15 pass. No cloud account, configured production factory, full-case or security acceptance; all4 export composition/full28 remain.

Evidence: specs/028-convergence-evaluation/evidence/20261110-private-native-models-audit-v1. Use existing reviewed transports/retention checks, reject operation replacement and independently verify citations. Keep provider-specific dependency constraints (IBM requires dateutil3.0). Use owned platform secret files/injections, never static cloud keys or replacement encryption keys. Append bounded metadata-only SQL audit under a role without history read/change privileges; bind job attempts and withhold generation/release on audit failure. Do not incorrectly blame a source for generic workspace failure. Preserve CPython ABI, dependency conflict and cleanup-fault evidence. Fresh schemas only; no existing DB migration. See docs/architecture/private-knowledge-native-adapters-audit.md. Complete native factories/operator recovery and per-file isolation before advertising a private capability; remaining families/full28/held-out stay in scope.


## 2026-11-11: Native private factories and operator authority

Assembled separate native API/worker factories and non-superuser SQL operator lifecycle. Current registration/source/provider activation fences old runtime authority, opaque cookies and queued work; retained original200-vs401 cookie regression. 121 host SQL/API/worker checks per PG17/18,67 Linux policies and77 native SQL checks per version per cloud,13 browser and15 actual Office/PDF workflow checks pass. Native per-file cloud execution, complete export/whole-case/full28 acceptance and security acceptance remain unfinished.

Evidence: specs/028-convergence-evaluation/evidence/20261111-private-factories-operator-v1. Runtime startup validates exact schemas/privileges/activated metadata without creating or adopting state. Operator activation changes shared authority transactionally; old processes lose permission and outstanding questions/sessions are cancelled. Cookie/worker context matches that authority. Directory mappings are approved inputs, idempotent, versioned and revoked atomically, with operator-only history. The operator needs database ownership, not SUPERUSER/CREATEROLE or application keys. Native parser executor remains an explicitly owned byte-bound port, not proof of native isolation; no unsafe default worker is advertised. See docs/architecture/private-knowledge-factories-operator.md. Existing native roles/source/index/model/account consistency, retention/key recovery, all4 exports and final full28/held-out remain in scope.


## 2026-11-11: Mounted document jobs and actual native assembly

File-only per-file protocol and live executor guards implemented. Linux26/qualification23, SQL122 per PG17/18, policies79, JavaScript347 pass. All4 local native API/worker assemblies pass52 checks with8 actual Office/PDF parses and16 answer releases; observed-running cancellation removes owned containers/volumes. Provider-native job execution, complete exports/whole-case qualification/security and final28/held-out remain unfinished. Evidence: specs/028-convergence-evaluation/evidence/20261111-private-mounted-document-jobs-v1. See docs/architecture/private-knowledge-mounted-document-jobs.md.


## 2026-11-11: Native Google document-job prototype

Batch controller/GCS transport/sequential trusted transfer CLIs implemented. Exact Google core:93 policies,78 SQL tests per PG17/18,33 locked packages; emitted three-stage local Office/PDF pipeline18 passes. Official discovery revision20261103 independently checks emitted shape. Exact core scan47 HIGH, zero critical/fixable HIGH/critical; security unaccepted. Native account semantics, IAM/Terraform/provenance/worker wiring and durable orphan recovery unfinished; remaining three native launchers, complete private/other cases and final28/held-out stay required. Evidence: specs/028-convergence-evaluation/evidence/20261111-private-google-document-jobs-v1. See docs/architecture/private-knowledge-google-document-jobs.md.


## 2026-11-11: Google parser substrate emission and runtime target binding

Native bucket/identity/IAM/registry/private network/DNS module emits exact runtime config. Normal and hostile-ID packages pass22 native mock plans and two independent output/runtime/schema checks. Fixed reproduced Terraform JSON metadata interpolation; retain original failing plan, source and exact marker. Worker rejects wrong provider/project/region/identity and adapter config is immutable. Host SQL123 per PG17/18, Linux94 policies/78 SQL per version, real Office/PDF pipeline18 and JS354 pass. Exact core47 HIGH remains unaccepted. Complete application/worker/artifact wiring, orphan/retention/key/audit recovery, other three native launchers, full private/remaining cases and final28/held-out remain. Evidence: specs/028-convergence-evaluation/evidence/20261111-private-google-infrastructure-binding-v1. See docs/architecture/private-knowledge-google-infrastructure.md.


## 2026-11-11: Persistent private-document cleanup and restart recovery

Metadata-only document cleanup ledger, committed pre-creation intent, fenced leases, retries and uncertain-creation settlement; independent worker maintenance. Actual process-death SQL tests; native Google HTTP remains scripted. Host134 per PG17/18, final portable ledger10 per version, Linux95 policies/88 SQL per version, Office/PDF pipeline18, Terraform mock plans22 plus two independent config checks pass. Core47 HIGH remains security-unaccepted. Other3 native launchers, complete export/whole-case/final28/held-out remain unfinished.

Evidence: specs/028-convergence-evaluation/evidence/20261111-private-document-recovery-v1. See docs/architecture/private-knowledge-document-recovery.md. Settlement scheduling is not a hard raw-data retention SLA. Worker downtime, native late effects, destination rotation, monitoring and backup/key recovery still require operational work. Preserve the API-private schema-privilege failure and clean-Linux fixture-path failure; production validation reads catalog OIDs without expanding API privileges, and fixtures restore the installed schema.
