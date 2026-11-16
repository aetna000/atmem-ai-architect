# Proposed maintenance interfaces v1

Strict unknown-field rejection, bounded JSON/body/patch/log sizes, opaque IDs and authenticated owner/project scope. All source strings are data. Every response has requestId, record revision, status and actionable findings. No secrets in payloads. HTTP shape is proposed; local adapter is required first.

## Local sidecar / backend-neutral commands

- POST `/api/maintenance/projects`: explicitly select allowed local roots, initial target and policy. Local path adapter restricts canonical paths to user-approved roots, denies symlink escape, VCS hooks/submodule/LFS implicit execution and arbitrary filesystem discovery. Remote callers cannot select host paths.
- POST `/api/maintenance/projects/{id}/inventory`: expectedProjectRevision, repository snapshot identities. Computes graph without executing repository code.
- POST `/api/maintenance/projects/{id}/prepare`: expectedProjectRevision, graphDigest, recipeDigest, target, computeAuthorizationId, budget. Idempotency-Key required; returns job ID, no mutation to original roots.
- GET `/api/maintenance/jobs/{id}`: bounded phases/progress and evidence summaries, no synthetic percent or endless spinner. GET evidence separately with scoped access and redaction.
- POST `/api/maintenance/jobs/{id}/cancel`: expectedRevision; fences executor, stops new remote intents; reconciles writes already in flight.
- GET `/api/maintenance/projects/{id}/export`: versioned project, patch/evidence manifest; no credentials or reusable permissions.
- POST `/api/maintenance/projects/import`: validate manifest/digests/paths/size; approvals and credentials never restored; verification results imported as historical until reproduced.

## GitHub adapter — R3 only

Read customer-token-authorized selected repositories/commits, compare heads, create/update bot-owned proposal branches with conditional expected SHA, create/read PRs, inspect merge status. R3 identity: customer-supplied fine-grained GitHub token with metadata read, contents read/write and pull requests read/write on explicitly selected repositories; store only in OS keychain, never npm package/project/browser/memory. Local broker polls with bounded intervals and handles expiry/revocation. No GitHub App private key or inbound webhooks in R3. R4 may propose a separately qualified hosted App broker and signed webhooks only after governance alignment. No workflow-file writes in initial recipe scope; no admin, organization-member, merge or release operation. Existing branch protection remains authoritative. R3 customer token (R4 App credential only after qualification) never enters checkout/worker/model environment.

- POST `/api/maintenance/projects/{id}/publication-preview`: returns exact action/repository/base/patch digests, expected branch operations and missing review steps. No write.
- POST `/api/maintenance/projects/{id}/publication-authorizations`: human confirmation binds preview digest, expires after15 minutes, exact enumerated actions in one publication wave only.
- POST `/api/maintenance/projects/{id}/publish`: authorizationId, previewDigest, expectedRevision, Idempotency-Key. Durable intent before remote write; recheck current permission/base immediately before each write. 202 may mean reconciliation pending, never guaranteed success.
- GET `/api/maintenance/projects/{id}/publication`: actual PR URLs/heads plus pending/unknown/manual-action state. A PR is not marked ready until its relevant exact checks and dependency policy hold.

Errors: 400 invalid input; 401/403 scope failure; 409 stale head/revision/idempotency mismatch; 413 size; 422 unsupported/unresolved applicability; 429 budget/concurrency/rate cap; 503 temporary adapter failure. Never log tokens, diff secrets or upstream error bodies verbatim.

## Worker / recipe contracts

Worker input: read-only snapshot artifacts, approved tool/image digests, allowlisted dependencies, candidate writable directory, bounded resource/network profile. Worker output: proposed patch and raw check findings; verifier derives readiness independently. No host mounts, broker tokens, user shell setup, cloud credentials or ambient environment. Provider download/hash policy separate from plan/state access. Network denied while executing repository/tests/providers; fetch artifacts in a separate credential-scoped broker then mount read-only.

Recipe predicates can return applicable, unsupported or unknown; unknown never means safe. Model adapter can propose edits, cannot set verdicts, change budgets or execute arbitrary commands. Repair limit defaults 3 attempts, 20 minutes/job, USD5 model spend/job; explicitly adjustable downward and opt-in upward. Caps are enforced by the broker, not prompt text. Static-check artifacts may contain secrets and require the same isolation/access controls as repository source.

## Remote write reconciliation

Fenced lease+write-ahead operation prevents local duplicate dispatch. Remote APIs do not support our fencing atomically: deterministic bot branch and stable campaign marker enable discovery; conditional-ref update prevents clobbering. Before each write, query for existing corresponding object. On ambiguous timeout, stop further writes, reconcile until bounded deadline, then needs_attention. Revocation cannot undo a request already accepted upstream; report that race and resulting object, never promise atomic revocation across GitHub. Human commits stop automated branch updates. Do not force-push. Cleanup of remote proposals is a separately confirmed action, never automatic rollback of merged code.

## Mandatory patch and automation safety (FR-014)

Verifier AST/path diff policy denies new provider/module sources except exact reviewed recipe allowlist, external/http data sources, provisioners, `.github/**`, `.gitlab-ci*`, `atlantis.yaml` and other configured CI paths. Existing forbidden executable constructs make readiness blocked unless their nonexecution is established by the check profile; broad grandfathering is prohibited. Symlink/path aliases cannot evade policy. Model cannot edit policy or bypass denials. Secret filtering runs before model egress, exports and remote publication.

Publication preview lists EACH planned ref/commit/PR write with exact digest, detected workflows on push/pull_request, Atlantis/Terraform Cloud hints and unknown external automation. A draft PR may still trigger workflows; there is no universal no-CI switch. Customer must explicitly confirm detected/unknown automation side effects for each enumerated action. If they decline or cannot accept the risk, export local patches only. No inference of safe CI from missing workflow files.

GitHub conditional update uses GraphQL createCommitOnBranch expectedHeadOid where supported or Git commit with observed parent plus non-force ref update; REST ref update has no expected-old-SHA parameter. Human-commit races are independently tested. Per-repository proposal ownership keyed by source/recipe/target fingerprints and discovered remote markers prevents ordinary cross-install duplicates; concurrent first-time creators can race. Scope the zero-duplicate acceptance to one serialized campaign coordinator; foreign/competing campaigns require reconciliation/manual resolution before publication, never an absolute exactly-once promise across independent stores.

## Module publication waves (FR-015)

Module patches publish first. Consumer patches remain local provisional artifacts until module_release_pending resolves; they cannot reference imaginary tags or be published as ready. Human publishes the module version; AtMem never tags/releases it. ReleaseObservation captures canonical source address, resolved version/ref, fetched immutable identity, path-scoped tree digest for Git subdirectories or normalized package content digest for registry archives, overlay comparison and provenance. Comparison normalization is versioned, excludes only documented transport metadata and includes every executable/configuration file; registry archive SHA is additionally retained. Any mismatch blocks and triggers a new review/check revision, never an automatic equivalence waiver.

Module versions from ranges are resolved with a modules.json-equivalent receipt and content digest; provider lockfiles do not pin modules. Refresh drift invalidates checks. After equality, finalize consumer patches with the actual release reference, rerun required checks against the fetched released artifact and obtain a new 15-minute exact-action confirmation for that wave. Multi-level graphs repeat this protocol; cycles need a demonstrated compatible intermediate version sequence or remain blocked. R2 qualifies this with local immutable release artifacts and a simulated operator release; R3 qualifies real Git/registry observations and PR waves. Simulation cannot earn network/publication acceptance.

## Model egress and aggregate budget (FR-016)

ModelEgressAuthorization names backend/provider/model, permitted repositories/paths/data classes, reviewed vendor retention/processing terms, actor and expiry. It is independent of compute approval. Deny tfvars/secret files/private keys/credential stores by default; scan selected HCL/text and model-request payload for secrets. Sensitive source findings redact/block. Show selected paths and redacted payload summary for confirmation; pattern scanning cannot prove arbitrary source secret-free. Never silently send all checkout files. No project source becomes shared recipe training memory.

Budget ledger atomically reserves per tenant/project/schedule AND credential owner across concurrent jobs. Reservations and settlement include provider usage/unknown outcomes; a lower per-job cap cannot bypass a tenant cap. Source/recipe updates coalesce for 60 seconds by default; at most one active revision per campaign. Recompute needs fresh budget and egress validity. Strict commit invalidation is initial behavior; path-based optimization requires conservatively proven coverage.


## Final review clarifications

Egress confirmation binds an immutable source-selection digest (allowed paths, redacted file digests, data classes, backend and vendor terms), not a single request payload. Each repair request may use ONLY that selection, sanitized verifier findings and prior model output; it receives a new payload digest and filter receipt. New source bytes/path/data class/backend/terms require reconfirmation. R4 scheduled jobs stop at egress_confirmation_required whenever this confirmation is invalid; no standing permission for arbitrary new source is implied. Inventory/matching can recur unattended. A broader standing egress policy would require a separately approved future extension.

Broker enforces `refs/heads/atmem-upgrades/` plus recorded campaign ownership independently of token scope; default/protected/unowned refs are denied even in an unprotected repo. PR base is read-only. Scope/token owner is bound per repository; one fine-grained token per resource owner, explicit organization approval/expiry states. No qualified OS keychain means publication blocked. Workflow permission is never requested. Unknown branch commits are detected by exact expected SHA/provenance ledger, never commit author identity. A competing campaign stops for reconciliation.

Source policy permits a module ref finalized by an equality-passing current ReleaseObservation in addition to exact recipe sources; any other changed source/ref is denied. Publication preview also detects pull_request_target, workflow_run, check_suite and repository required-check apps where discoverable; unknown automation remains explicitly disclosed. Existing external/http/provisioner coverage limits are measured during R0 and published, never silently waived.
