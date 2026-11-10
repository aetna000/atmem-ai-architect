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

## 2026-11-10 — Private Google SQL transport and queue reconnection

Added an explicit maintained private-IP Cloud SQL proxy path with separate native
identities, startup ordering and continuously allocated background CPU. Staging and
production now have distinct stable physical names; misspelled environments fail.
A PG17 rerun exposed queue exit during connection termination/credential rotation.
The deterministic killed-transaction regression fails against the prior worker;
the corrected supervisor closes/reopens its pool with fresh credentials and bounded
backoff, preserving domain fencing/approval/uncertain-delivery rules. It does not
retry schema, permission or programming failures. Both PG17/18 now pass 89 checks.

302 JavaScript tests/build, 61 API/operator checks, native AWS/Azure/Google schemas
and 6/7/6 mock plans pass. Three exact rebuilt images pass generated-environment
startup/denial plus five restricted queue cases each. Full medium conversation
acceptance remains zero; operator/registry/Spec Kit/IBM integration is incomplete.

Application/parser scans retain 47/65 high findings without reported fixes. The
pinned upstream proxy platform scan reveals one fixable high, one fixable medium
and an unknown finding. Keep it unaccepted pending repair or independent resolution;
do not claim a clean scan from a failed Docker multi-architecture export. Failed and
passing runs, exact source and inventory are preserved in:
specs/028-convergence-evaluation/evidence/20261110-gcp-invoice-and-queue-recovery

No cloud account operations, deployment or remote pushes occurred. The owner’s
periodic local Git checkpoint policy remains active. Continue implementation and
the original full 28-project/held-out evaluation without narrowing the objective.

## 2026-11-10 — Repair IBM operator credential callback

The complete CLI path exposed a one-argument password callback where the native
bootstrap requires purpose and principal. Repair and verify both owned fields;
retain the failing CLI regression. Actual SQL login creation, SCRAM authentication
and restricted grants pass on PG17/18. API aggregate: 62 checks. Native IBM cloud
resources and the complete invoice export are not qualified by this local proof.
Evidence: specs/028-convergence-evaluation/evidence/20261110-ibm-operator-bootstrap

## 2026-11-10 — Resolve exact upstream proxy finding applicability

Retain the original module-version vulnerability inventory. Independent official
govulncheck binary analysis finds none of the affected HTML/OpenPGP packages in the
exact upstream AMD64 binary. An intentionally affected compiled Linux control must
report all three issues at symbol level; it passes that positive detection check.
Keep raw scanner/OpenVEX data and a derived record bound to image/platform/binary.
This resolves these three findings for this artifact, not arbitrary future images
or unknown vulnerabilities. Re-review on changed image/findings. Compiler exports
the bounded review and rejects a mismatched artifact. Fresh Google schema/six mock
plans, 302 JavaScript tests and build pass. Wider project acceptance stays pending.
Evidence: specs/028-convergence-evaluation/evidence/20261110-proxy-binary-applicability

## 2026-11-10 — IBM invoice native adapter and shared endpoint repair

Added private Classic PostgreSQL 18, regional versioned documents/90-day lifecycle,
separate API/worker profiles, staff App ID/PKCE, minimum-one queue worker and a
private TLS parser with separate 256-bit admission authority. No database/model/
object/action or Code Engine API authority is given to the parser. Native platform
origin metadata avoids trusting request headers or a Terraform own-endpoint cycle.
Seven native mock plans, exact IBM image startup/denial/five restricted queue cases,
17 parser checks and 68 aggregate API/operator checks pass locally. No actual IBM
account, private network, model, registry login or deployment is claimed.

Review caught the shared region+'.icr.io' generator error. Sydney uses au.icr.io;
structured/FAQ/invoice exports now share explicit mapping with no global fallback,
and independent native resolved-image regressions pass. The observed documentation
and pinned receipt support a bounded AtMem engineering-practice admission.

305 JavaScript tests and build pass. Exact rebuilt IBM/parser images retain 47/65
high findings, zero critical or reported fixes; this is not security acceptance.
Keep medium invoice conversations uncounted until native operator/maintenance,
monitoring, state/Spec Kit/registry and whole-export qualification are implemented.
Then continue all remaining medium/hard cases and full 28-case/held-out evaluation.
Evidence: specs/028-convergence-evaluation/evidence/20261110-ibm-invoice-native


## 2026-11-10 — Serialized reusable operator bootstrap checkpoint

Extracted complete deployment/binding validation and shared operator initialization
for the CLI and upcoming fixed native jobs. All scope validation precedes connection
and native role creation. Azure postgres identity mapping remains separate from app
schema admission. A shared database-local advisory lock protects initial schema
check/create; autocommit is rejected before native DDL. Owned retries preserve SQL
passwords and do not adopt unrelated roles. No requirements or ownership changed.

Actual simultaneous bootstrap into a fresh synthetic database, native-profile SQL
login/grant checks and repeat initialization pass on local PostgreSQL 17 and 18.
71 API/operator checks, 7 PG18 operator checks, 305 JS checks, 208 server checks and
build pass. Evidence does not qualify newly rebuilt images or cloud jobs/identities.
Native operator/scheduled retention/monitoring, full state/Spec Kit/registry wiring
and complete medium conversations remain next. Full 28 and held-out pending.
Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-operator-core


## 2026-11-10 — Fixed operating jobs and AWS native delivery

Implemented shared explicit initialize/maintain/monitor jobs. Operator credentials
and authority are separate from API/worker; raw native secret injections become
private short-lived files. A real prototype check exposed HTTP/JWT coupling, fixed
by extracting owned deployment/native SQL configuration into a non-HTTP module.
Monitor is read-only and count-only; unknown/dead/stale work, expired leases and
retention overdue signal attention. Two-hour work and two-day cleanup-grace thresholds
are explicit operational defaults, not client SLAs. Deadline is 15 minutes.

Expired-only online maintenance is now admitted by actual SQL tests: live doing
jobs/leases block deletion, competing submissions wait and survive, exact scoped
bounded batches report real backlog. This changes only the daily expired-cleanup
operating boundary; restore/quarantine/reconciliation remain paused and isolated.

AWS native task definitions and schedulers are implemented. Bootstrap remains manual
and unavailable to the scheduler role. App release requires operating flags, not a
false claim of actual bootstrap. Exact runbook/request, scoped execution identity,
private SQL, failure queue and missing-success alarms are emitted. Existing SNS
notification policy/KMS/subscriptions remain explicit owner-reviewed references.
Scheduler trust uses the documented schedule-group SourceArn, not schedule ARN.
Observed primary source bytes and URLs are preserved; no cloud behavior is inferred.

82 API/operator checks, 9 PG18 maintenance checks, 9 native AWS mock plans, 9 exact
operator-image checks on each PG17/18, 5 exact-image restricted queue checks, 307 JS,
208 server checks and build pass. Exact image still has 47 open high findings with
no reported fix, zero critical in cached metadata; no production acceptance.
Other three native operating wrappers and full state/Spec Kit/registry composition
remain next. Complete medium conversations, other families and full28/held-out remain
unfinished. No account operation, publication or deployment. Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-operating-jobs


## 2026-11-10 — Azure fixed operating jobs and current log routing

Implemented native manual bootstrap and phased daily/hourly jobs with a separate
PostgreSQL Entra administrator identity, main-only availability and pull-only None
identity. Native start can override template/image/command, so its authority remains
trusted destination operator access; it is never assigned to product/worker/model.
No application secrets/model/object authority is supplied to the operator job.
Exact start URLs/runbook are emitted instead of requiring guessed resource names.

Current Azure Monitor destination plus both dedicated diagnostic categories and
regional 30-day workspace are emitted. Count-only success/failure and native system
warnings are queried against documented current tables, not legacy _CL schemas.
Manual bootstrap materializes/verifies logs; scheduled/application release requires
native query validation. Existing Action Group delivery is an explicit reviewed
reference, never adopted/modified. Ingestion, KQL and alerts remain destination
acceptance; local provider schemas are not evidence they worked in Azure.

11 native mock plans and schema validation pass. Exact image checks (12 each PG17/18)
exercise actual Azure SDK against scripted local metadata, wrong-identity refusal,
scripted six-column Entra mapping over real SQL role/schema/grants, bootstrap/retry,
monitor/maintenance and runtime denials. No native cloud authentication is claimed.
82 API/operator checks, 5 exact-image restricted queue checks, 308 JS, 208 server and
build pass. Generalized qualifier retains AWS historical-image compatibility (9).
Exact Azure image retains 47 high, zero critical or reported fixes in cached data;
not production/security acceptance. Removed one shared-module EOF blank line while
thawed; exact new image hashes qualify it, historical source receipts are preserved.

Google/IBM native operating wrappers, complete state/Spec Kit/registry and medium
business conversations/exports remain next. No medium case counted complete; full28,
held-out and remaining families unfinished. No cloud operation, publication or
deployment. Evidence: specs/028-convergence-evaluation/evidence/20261110-azure-operating-jobs


## 2026-11-10 — Google fixed jobs and actual proxy lifecycle

Implemented GA Cloud Run operator jobs, separate ops SQL identity/private VPC and
job-scoped Scheduler invoker/OAuth. Bootstrap is unavailable to Scheduler; no extra
SQL/data/override grant is conferred on product/caller. Paused scheduling and phased
release precede the application. An exact output-driven CLI helper previews writes
and waits for completion, without shell interpolation or exposed token arguments.

Stable concurrent container startup is handled by the operator's bounded loopback
startup wait. It always quits the pinned maintained proxy on success/work/metadata
failure; cleanup failure cannot produce an ok heartbeat. Local transport connection
establishment retries three times with fresh credentials, never statement replay
or authentication/schema bypass. 960-second native task bound covers startup and
900-second work deadline. No new proxy binary or vulnerability waiver was introduced.

Provider-specific telemetry uses region-scoped owned log metrics, explicit first-
sample arming and a two-hour heartbeat. Google absence duration cannot cover the
other providers' 48-hour maintenance check; hourly SQL monitoring checks the existing
92-day-overdue invariant instead of inventing an unsupported condition. Existing
channel and organization log custody remain reviewed references. Native scheduling,
actual IAM/Cloud SQL privileges/TLS, telemetry and delivery require destination proof.

10 native schema/mock plans, 12 actual operator-image checks on each PG17/18, 2
network-disabled exact proxy lifecycle cases (including actual CLI failure), 5
emitted-runner/fake-CLI cases, 5 exact-image queue checks, 87 API/operator checks,
309 JS, 208 server and build pass. Metadata/IAM SQL marker fixtures are synthetic;
no managed Cloud SQL privileges or authentication are inferred from stock PG/root.
Exact image retains 47 high, zero critical or reported fixes in cached data; not
production/security acceptance. Historical AWS/Azure image evidence stays exact;
shared runtime changes require re-admission for future combined exports.

IBM native operating wrapper, complete state/Spec Kit/registry and medium business
conversations remain next. Zero medium cases complete; remaining families/full28/
held-out unfinished. No cloud operation, publication or deployment. Evidence: specs/028-convergence-evaluation/evidence/20261110-google-operating-jobs


## IBM fixed operating tasks, separate from scheduling acceptance

Added separate SQL operating job definitions and a package-owned isolated CLI
launcher with explicit destination selection and no task overrides. IBM 2.9 has
no cron subscription resource; scheduling/alerts remain explicit unfinished work.
Nine provider mock plans, eleven actual-helper/fake-CLI cases and 310 JS tests pass.
No native IBM job execution or cloud operation is inferred. Full wrapper, complete
medium cases and final28/held-out remain in progress. Evidence: specs/028-convergence-evaluation/evidence/20261110-ibm-operating-tasks


## IBM operating composition: tasks, explicit native schedules and Cloud Logs

Implemented fixed SQL jobs plus owned PingSource installer/observer instead of
inventing an IBM 2.9 Terraform cron resource. Separate maintenance/application
phases, private CLI/Kubernetes context, UID/resourceVersion ownership, no overrides
or implicit adoption. Current Cloud Logs thresholds reference existing verified
same-region logging and notification configuration without rewriting account
routing. Twelve schema/mock plans, eleven job-launch and eleven schedule-helper
fake-CLI cases pass; twelve actual image/operator checks pass on each PG17/18,
plus API image/five queue cases, 311 JS and build. Native secrets/config/TLS are
scripted or transport-substituted; no managed IBM job execution or cloud proof.
Cached security still has 47 high/no reported fixes: not production approval.
Whole state/capability/Spec Kit and business conversations now take priority; zero
medium invoice cases are complete. Remaining families/final28/held-out unfinished.
Evidence: specs/028-convergence-evaluation/evidence/20261110-ibm-operating-jobs


## Register complete invoice export composition and portable local acceptance

Four native invoice compilers are now selected through the strict public model/
resource/export path. Added exact interfaces, provider-specific protected state
guidance and phased Spec Kit tasks with real file/resource/input links. Extra
requirements/flows and invalid placement remain preserved gaps; critical native
workload omissions fail coverage. No source repository is reclassified as an
existing deployment. Portable acceptance no longer depends on monorepo SDK paths;
the observed foreign-Azure-SDK failure is preserved and provider-case selection is
explicit. The final IBM delivered suite passes 82 checks on its freshly bootstrapped
owned PG18 fixture; this is not real cloud authentication/model/deployment proof.
84 public-path native staging/production mock plans, 335 JS, 208 server plus four
new focused checks and build pass. Complete business-brief handoffs have 29 tasks
each, all todo. Zero complete medium business conversations are counted. Live
conversations, whole-runtime/emulation acceptance, remaining families/final28 and
held-out remain next. No cloud operation or remote publication. Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-public-export


## Freeze pinned knowledge proof receipts with live evaluation source

Initial invoice attempts failed before model replies: snapshot omitted pinned
local receipts required by the knowledge gate. Preserve all four failures; count
zero medium cases. Runner now validates/copied immutable proof bytes and records
provenance without weakening knowledge confidence checks. Six focused harness
tests cover valid copy plus missing/changed/escaped proof refusal. Fresh frozen
live conversations remain next. Evidence: specs/028-convergence-evaluation/evidence/20261110-frozen-knowledge-proofs


## Actual invoice conversations: low question burden and retained failures

All four frozen live conversations completed in three/four exchanges with one/two
business questions and zero infrastructure questions. AWS/Azure/Google have complete
structural exports; IBM correctly blocked annotated text in its region field. Fixed
the producer/output repair, not the export or gate. Historical incoming projects
remain readable. Exact IBM request replay now gives canonical au-syd with placement
uncertainty preserved and no new question; fresh full rerun remains pending.
Independent assessor updated for official Azure AzAPI with stricter source/scope
checks; original finding preserved. 337 JS and 214 server pass. Zero complete medium
cases counted until independent package/runtime/semantic acceptance. Remaining
families/full28/held-out unfinished. No cloud operation. Evidence: specs/028-convergence-evaluation/evidence/20261110-invoice-live-v2
