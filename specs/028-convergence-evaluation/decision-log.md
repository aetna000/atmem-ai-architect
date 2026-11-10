# Evaluation and implementation decisions

## Preserve a frozen baseline; repair the generator concurrently

The first complete run uses an immutable source copy, corpus digest and per-case
transcripts/exports. Current source changes cannot alter that run's behavior. Failed,
missing and timed-out cases remain failures. Compiler-only regeneration retains the
exact evaluated project and original export, records source hashes and creates a new
artifact directory; it is never counted as a new successful conversation.

## Qualify vertical slices before claiming provider parity

Interleave the single-unit and connected-system work in plan 027 per provider/capability.
A qualified unit is the prerequisite for its connected slice; unfinished units on other
providers remain visible. This allows testing a useful whole application early without
marking GEN-007/GEN-008 globally done. The first repaired slice is bounded, human-reviewed,
flat-schema AI processing with authenticated web access on AWS. Azure/GCP/IBM connected
AI application generation remains work to implement and qualify.

## Treat model output and provider data policy as runtime boundaries

The structured operation rejects invalid, duplicate, incomplete and out-of-contract
output. It executes no model actions. User enablement/subject is checked before inference
and before return. Model-service retention and text logging are read and enforced before
input leaves the handler; unknown settings block inference. No account-wide setting is
changed automatically. Real model quality, cloud identity and account policy tests remain
separate from fixture-based tests and provider mock plans.

## Own malformed proposals internally

One schema/revision repair is allowed before returning a failed operation. The original
request stays unchanged; a rejected proposal is never applied. Observed repair counts
are host-owned receipts, not model claims. Complex connected requests receive a bounded
240-second native-response allowance; simple requests retain 150 seconds. The regulated
case exposed a missing retrieval/identity classifier term; its failed 150-second run is
preserved and the corrected rule is covered by the actual frozen scenario text.

## Preserve consultation records

Long read-only records are split by Unicode code points into bounded continuation items.
There is no silent 1000-character truncation. Exceeding the API record bound produces an
explicit error until a retrieval-based larger-context path is implemented.

## Compact model wire protocol and evidence-driven finalization

The model emits revision-bound, whitelisted field edits and explicit additions/removals.
The host atomically validates the whole candidate and returns the existing full proposal
API. Unchanged graph/brief content is not copied through model output. No arbitrary JSON
paths, executable configuration or accepted-record rewrites are admitted by this patch
language. Original request state is unchanged on failure.

An exact recorded enterprise request exposed repeated evidence lookups. Project and
selected skills are already supplied; the model now receives useful memory, engineering
knowledge and pricing lookup tools. Approved retrieved contents appear once in canonical
context, with receipt pointers/IDs, query caching and observed provenance. If a lookup
adds no evidence, the next model round must finish using what is known. The final wire
schema forbids further tool requests. Missing facts remain explicit; users are not asked
to repair a tool budget or to narrow a complete brief.

Existing-reference contradictions now fail before resource generation, rather than
allowing a reference binding to create replacement storage or another deployment.

## Azure connected application repair, 2026-11-10

Added an explicit composed `azure-structured-app` capability with emitted Python 3.13
application/browser source, hash-locked runtime and test dependencies, a pinned official
container base, native App Service/model resources, managed identity, scoped permissions,
and single-tenant Entra API/browser registrations. It requires an existing access group
and reviewed ACR rather than recreating either. Each composed block owns its internal
resources explicitly; unrelated blocks and untyped integrations remain implementation gaps.

Local source tests exercise real JWT signatures, wrong identity/audience/scope/roles,
ASGI requests, input/output boundaries and scripted account-policy/model faults. The
runtime fails before sending input when the approved account data-handling capability
cannot be verified. It never writes that account-wide policy. Role claims authorize
until expiry; continuous revocation and destination MFA are not silently promised.

The live Azure ticket-triage case converged in two exchanges with zero technical
questions, zero compiler gaps and an independently consistent original handoff.
Its exact exported source, dependency versions, provider schemas and mock plans passed
local qualification. The current product emulation runs 15 emitted source tests with
external sockets denied. Container image startup/scan, live Entra/managed identity,
actual model quality and authorized cloud plans remain unverified. Production retains
the state/operations gate. This is one repaired case, not complete provider parity.

An invalid extra benchmark case selector was ignored by the old CLI while the valid
case ran. Original evidence is retained and counts exactly one case. Unknown and
duplicate selectors now fail before snapshotting or model invocation.

## Google application adapter and complete-brief acceptance, 2026-11-10

Added a separately implemented Google Cloud Run/IAP/regional Gemini composition.
Its keyless runtime, project-scoped prediction/policy-read role, image-pulling
platform identity, signed-header authorization and browser origin boundary are
explicit. Google-managed service identities use the pinned official Google-beta
provider; other resources use the pinned Google provider. The app never writes
project-wide model privacy controls. An expiring scoped owner review covers
abuse-monitoring terms that have no invented verification API; runtime separately
reads cache and model logging/sharing configuration. Review evidence is attested,
not independent provider proof. Existing project/group/registry are preserved.

Shared HTTP input/output/concurrency/origin handling was extracted and Azure's
15 emitted source regressions and provider checks rerun. Google has nine local
cryptographic/ASGI/scripted-transport checks, four browser checks, provider schema
and three plan-time mock tests. The live Google ticket-triage case converged in two
exchanges with no technical questions or compiler gaps; its unchanged original
handoff passed independent static and emitted-source/provider qualification.
Container images, real IAP/metadata/model behavior and cloud plans are not verified.

The acceptance audit found that reactive-facts runs may end before receiving
every corpus business constraint. They remain useful engineering regressions and
are never labeled semantically qualified. Added an explicitly versioned stronger
protocol that submits all remaining facts as one client update before export.
The corpus and acceptance criteria remain unchanged; preserve old results and
avoid direct exchange/time comparisons across protocols. Final matrix acceptance
must include every business fact and independent semantic/runtime checks.

## IBM composition, isolated SDKs and actual schema qualification, 2026-11-10

Added an explicit IBM Code Engine composition, preserving existing project,
registry/pull-secret and watsonx project/runtime boundaries. User authorization
uses a new owned App ID tenant, admin enrollment and process scope; workload
identity uses an exact compute-resource trusted-profile link and instance-scoped
Writer access. Project collaborator authorization remains a separate destination
prerequisite. No static application API key, fabricated approval API, existing
SSO/MFA, immediate revocation or global-logout behavior is claimed.

IBM's live complete-brief ticket case converged in three exchanges without a
technical question; its exact source/provider checks and regenerated Linux image
checks pass. Shared acceptance now exercises five simultaneous requests, failure
capacity recovery and the actual exported field schema through each model adapter.
Azure uses documented strict JSON Schema output; compatible model selection and
independent local result validation remain required. Original/failed exports are
retained. Shared SDK installation revealed a real dateutil conflict, so IBM gets
an isolated worker and missing dependencies cannot be reported as passed checks.

Image scanning drove a shared hash-pinned base/package update and removal of
unneeded installers. The exact latest three images still have 47 unfixed high
findings each; zero critical/fixable-high findings is not a security completion
claim. Evidence is in evidence/20261110-ibm-application. The next work remains public
retrieval with conditional authorized updates/deletes, then native permission-aware
connectors and durable workflows/tenancy. Full 28-case/held-out acceptance is open.


## 2026-11-10 — Public source lifecycle and independent service eligibility

Implemented the shared public-only FAQ catalog, authorized conditional editor CLI, source freshness, citation validation and four provider compositions. Preserve private enterprise/native connector requirements as separate work. New AWS FAQ systems use generated Lambda/HTTP API v2 source with hash-pinned MIT Mangum 0.22.0, not App Runner, which is closed to new customers. The original App Runner candidate and posthoc independent rejection are retained. Native schemas alone cannot establish service lifecycle eligibility.

Stricter Azure mocks exposed and fixed the paired health-check interval omission in both templates; isolated mutation tests prove rejection. Exact original/current FAQ artifacts and private-runtime regressions are locally qualified; model/storage fixtures are not live cloud evidence. Security reports distinguish the exported Lambda ZIP from AWS qualification tooling and retain remaining image findings. See specs/028-convergence-evaluation/evidence/20261110-public-faq/README.md. The 28-project target and medium/hard implementation remain unfinished; no cloud account operations or deployment authorized.


## 2026-11-10 — Durable queue and immutable approval core

Selected hash-pinned MIT Procrastinate 3.10.0 after reviewing its external-transaction
and stalled-worker contracts. Native local PostgreSQL/queue/role/TLS/process tests
now cover atomic outbox, deduplication, lease fencing, approval, crash recovery and
uncertain external outcomes. Approval binds a destination contract as well as the
source/result revision. Revocation cannot reset an uncertain send into a new action.
Separate migration/API/worker identities and hard processing deadlines are explicit.

51 observed checks and faults are retained in
specs/028-convergence-evaluation/evidence/20261110-durable-core. This core is not yet
a registered provider application: PDF/native identity/storage, complete provider
resources, retention/restore and vendor reconciliation remain implementation work.
No full project, final 28-case acceptance or cloud deployment is claimed.


## 2026-11-10 — Invoice composition and verified learning recall

Added bounded text/OCR and evidence-linked invoice suggestions, private immutable
object adapters for all four native contracts, restricted-role upload/review API,
append-only result history and actual local composed queue/model/TLS evaluation.
The first OCR image retained a critical-rated XML dependency; the reduced source
build removes unused archive/URL features and their libraries. Its actual runtime
passes, with 0 critical but 65 unfixed high scan findings still open. No full cloud
project is registered or counted before native resource/identity/isolation work.

A real AtMem round-trip test exposed sentence normalization that excluded reviewed
JSON practices from context. Accept exactly the pinned SDK's terminal period, then
verify full reviewed record/key equality; reject tampering and added instructions.
Portable locally-tested lessons now retain their evidence receipt and limitations.
See specs/028-convergence-evaluation/evidence/20261110-invoice-runtime. Full 28-case
acceptance, medium/hard provider composition and production qualification remain open.

## 2026-11-10 — Refreshable native database identities and recovery

Added separate native credential factories and operator-only owned role bootstrap.
AWS uses RDS IAM authentication membership, Azure checks authoritative Entra
service/OID/tenant mapping, GCP admits the package-created Cloud SQL IAM user, and
IBM uses a separately managed SQL password and instance CA. No cloud database or
IAM operations ran. Native mapping protocols remain fixtures until authorized
destination checks. API/worker roles cannot inherit broader workflow authority.

Local password rotation exposed a pre-claim queue failure path. Retry and bounded
notification repair now preserve pending/approved business intent without replaying
uncertain external effects. The same 80-check suite passes on PostgreSQL 17.11 and
18.6. Retained faults and exact sources are in evidence/20261110-workflow-credentials.
Continue composing complete invoice resources/UI/bootstrap and operations; CV-005
and the final full-project matrix remain in progress.

## 2026-11-10 — Native invoice API and review workspace

Implemented native staff login bindings, private storage/database producer bootstrap,
pink upload/review/history browser, PKCE and proxy-session handling. Cryptographic
claims and live database membership are independent boundaries; the API receives no
model or dispatch credential. Local qualification: 31 API/identity/storage/decoder
checks, 12 review browser checks and 5 PKCE browser checks. Cloud/JWKS/object/model
fixtures remain explicitly distinguished from real managed-service behavior.

Concurrent browser startup exposed shared SQL ACL catalog collisions. Owned grant
admission now holds a transaction-scoped advisory lock, refuses autocommit, and has
a four-way concurrency regression. All 82 workflow checks pass on PG17 and PG18.
Evidence and retained faults: evidence/20261110-invoice-workspace. Next complete the
first medium project export end to end, including worker/parser/native resources
and operations, then qualify its four providers before expanding further families.

## 2026-11-10 — Separate parser RPC, delivery images and operator recovery

The invoice worker now composes native private objects, separate bounded PDF/OCR
RPC, provider model transport and the independent evidence decoder. Extraction and
dispatch run in trusted deadline-bound child processes; neither inherits database
configuration or the other stage's secrets. Child environment separation is not an
OS sandbox. Untrusted PDF parsing remains a separate workload with no data/model
authority. Only the local test fixture owns Docker access.

Four exact native-SDK delivery images pass startup and five restricted PostgreSQL
queue cases each, including IBM's independently resolved dateutil 3.0 dependency.
Cold concurrent SDK creation exposed twenty separate S3 clients; lazy S3 and RDS
client initialization now serializes construction. Recovery preserves historical
uncertain external outcomes even when a later attempt never obtains a credential.

The isolated AWS compiler emits private Fargate/API/parser/database networking,
native identities, immutable repositories, TLS/private ingress, versioned storage,
native secret references and concrete operator outputs. Six native Terraform mock
runs pass. A real emitted image starts with the actual mock-plan API/worker settings,
including its now-emitted, pinned AWS database CA bundle. This does not admit the
complete invoice pattern into the product registry or certify cloud behavior.

Invoice payload access expires after ninety days independently of asynchronous
physical cleanup. Separate operator authority performs bounded scoped SQL purges,
staff membership changes, restored-delivery quarantine and exact approval/receipt
reconciliation. A real local pg_dump/pg_restore drill passes nine checks. Native
managed PITR, RPO/RTO, object restore and an actual accounting lookup remain outside
that evidence. Native scheduled operator bootstrap/maintenance delivery is still
required; the operations guide makes that ownership explicit.

Current evidence: evidence/20261110-invoice-worker-delivery. Local checks: 55
API/identity/parser/worker/operator checks, 85 workflow checks on each PG17/PG18,
12 review browser checks, 5 PKCE browser checks and 14 composed real-OCR/local-model
checks. Application images retain 47 unfixed high findings each; parser retains 65.
No clean-security, complete medium case, full 28-project or deployment claim is made.
Continue the other native cloud adapters, whole-export registry/Spec Kit/operations
integration, complete invoice conversations, then the remaining medium/hard families.

## 2026-11-10 — Fence restored extraction as well as delivery

A further restore audit found that historical extraction leases/native doing jobs
could block expiry cleanup after restore. The extended regression fails against
the prior retained source. Restore now fences those leases to pending, removes
stale notifications in bounded progressing batches, preserves attempt limits and
reconstructs pending work only through normal recovery after expiry cleanup.
Delivery remains unknown and cannot be silently resent. Updated logical restore
drill: ten checks. Four newly rebuilt images pass startup/queue and actual isolated
operator entrypoint checks. Evidence: evidence/20261110-invoice-restore-recovery.
The earlier checkpoint is preserved. This repairs a component operating gap; it
does not complete CV-005, native cloud adapter parity or a medium benchmark case.

## 2026-11-10 — Periodic local recovery checkpoints

The owner requested periodic repository backups during implementation. Save local
Git commits at meaningful work boundaries, including unfinished work with explicit
status. This checkpoint preserves the Azure emitted-image/parser-plan checks and
the initial GCP private Cloud SQL proxy adapter. Seven targeted application tests
and syntax checks passed; retained qualification receipts remain scoped to their
recorded source hashes. Full generator integration and the repaired 28-project
evaluation remain in progress. No remote push or deployment was performed.

Evidence: evidence/20261110-generator-backup-checkpoint.
