# Data model v1 — proposed

All records have schemaVersion, tenantId, projectId, immutable ID, createdAt UTC, actor and provenance. Mutations use revision compare-and-swap. Credentials are opaque broker references only. Export strips credential references and remote authorization; importing never restores permission.

- RepositorySnapshot: adapter/repository immutable identity, commit, selected roots, tree digest, resolved artifact digests, byte/file inventory and completeness findings. Moving refs are recorded but never cache keys. Unknown/missing Git/LFS/submodule/private dependencies remain explicit.
- DependencyGraph: snapshot set, parser identity, root/module/provider nodes, typed edges, exact source ranges, resolution state/reason and user-confirmed overrides. Overrides are audited facts requiring confirmation, not silent inferred edges.
- UpgradeRecipe: public recipe/version/digest, primary-source revision/date/digest, provider/version constraints, required input predicates, transforms/guidance, validator/tool contracts, forbidden changes, known limits, reviewer and withdrawal state.
- MigrationProject: snapshot set, graph/recipe digests, requested target, accepted decisions, compute policy, revision, jobs, candidates, review obligations, campaign state and event log. Unknown targeting never widens scope automatically.
- CandidatePatchSet: base commits, ordered diffs and per-file digests, dependency artifact substitutions, prospective module release mapping, semantic changes, manual steps and applicable policy digest. Imports of overlay artifacts never rewrite published module refs to temporary paths in final customer patches.
- VerificationReceipt: baseline/control/candidate class; source/graph/recipe/patch/tool image/lock/oracle/policy digests; sanitized command/result, exit and timeout; evidence class; expected/observed findings; missing input; worker identity; timestamps. Secret-bearing logs quarantined/redacted, never model context. Any changed bound identity makes receipt stale.
- Authorization: actor/token/repository scope, permitted operation, exact source heads and patch digest, expiry/revocation revision. Compute, network, remote publication and deployment are separate privileges. Initial product has no deployment capability.
- RemoteOperation: unique key(tenant, campaign, repo, patch digest, operation kind), expected upstream head, durable intent, discovered branch/PR identity, lease/fencing epoch, attempt receipts and outcome known/unknown. Remote IDs never trusted from model output.
- Schedule: selected repo scope, allowed targets, hold policy, cadence UTC, compute caps, last cursor and opt-in actor. Scheduler may prepare but cannot confirm PR publication.
- BudgetReservation: tenant aggregate ledger, credential owner (user-managed or service-managed), job idempotency key, maximum money/tokens/time, reservation revision, spend receipts, release/settlement; unknown spend prevents re-reservation. At most one active fenced executor per job.

## States

Job: queued -> inventory -> applicable | blocked -> baseline -> drafting -> checking -> ready_for_review | blocked | failed | canceled. Bounded repair returns checking -> drafting, preserves attempts. Any input change -> stale -> new job revision; no pass promoted across revisions.
Publication: unapproved -> approved -> intent_recorded -> publishing -> reconciled | outcome_unknown | needs_attention. Approval expires on base/patch/policy changes. No uncertain write is retried before read reconciliation.
Campaign: proposed -> preparing -> ready_for_review -> partially_published -> published -> partially_merged -> complete | needs_attention. Complete means coordinated repository changes merged/observed against approved expected commits, never deployed. Awaiting a module release follows module_release_pending -> release_observed -> consumer_reverification before ready_for_review for the consumer wave. Changed module release mapping requires new checks. Cycles require a tested compatible sequence; otherwise blocked.

## Data lifetime

Default proposed: ephemeral checkouts 24 hours after job termination; sanitized logs/receipts 30 days; audit metadata 90 days; artifact versions retained while their project is retained. Deleting a project revokes schedules and permissions immediately, queues blob/log deletion within seven days, leaves only minimal security tombstones until 90-day expiry. Snapshots in backups expire within 30 days of deletion. Tenant administrator can shorten; longer retention requires an explicit policy. Recipe catalogue contains public reviewed sources only. R4 must implement/test these policies before hosting; durations are design defaults, not existing service behavior.

## Review additions

ReleaseObservation: campaign/module/source address, resolved version/ref, immutable fetched identity, raw archive digest where applicable, normalization policy version, executable tree digest, expected overlay digest, equality verdict and fetch receipt. Mismatch blocks consumer finalization. Ranged resolution is snapshot data; lockfile provider identities cannot stand in for module resolution.

ModelEgressAuthorization: backend/model, allowed data classes/paths, source-selection digest (paths, redacted file digests, data classes), derived-request payload digests, secret-filter results and user confirmation, vendor terms reference/date, credential owner, actor, validity and revocation revision. Bind each model request/usage settlement to it. Redaction changes payload identity, not original source evidence.

The existing Architect versioned project file remains the logical authoritative model: add a versioned optional maintenance section through explicit project-format migration. SQLite is the transactional persistence of that same aggregate, not a second independently editable source of truth. Export/import round-trips it; every earlier supported format has migration tests. Imported historical receipts retain provenance but do not recreate current readiness/permissions.

Remote exact-once scope is one serialized campaign coordinator. Cross-install competing coordinators may race; detect remote campaign ownership and stop/reconcile rather than promising global exactly-once. Tenant aggregate spend reservation prevents concurrent per-job budget bypass.
