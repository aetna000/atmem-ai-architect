# Feature Specification: Infrastructure upgrade maintenance

**Feature Branch**: `spec/infrastructure-upgrade-maintenance`
**Created**: 2026-11-16
**Status**: Proposed; planning only, no product implementation or release
**Input**: Owner requests ongoing coordinated infrastructure migrations across repositories, available checks and repairs, and reviewable PRs. Independent Claude Opus 5.5 Medium review must precede agreement on release planning.

## Outcome and boundaries

When a supported infrastructure dependency changes, AtMem prepares the migration across affected repositories and maintains the proposal as those repositories change. It sells completed maintenance work rather than version notifications. Customers review, merge and deploy.

Initial scope is Terraform AWS provider migrations in shared modules and consuming root configurations. A supported migration must change configuration beyond a version number and prove why that change was necessary. Coverage is a published tested matrix, not a claim of arbitrary AWS upgrades. Terraform and OpenTofu qualification are separate. Other clouds, application/runtime migrations, database/data migrations, cloud account plans and deployment are later proposals, not initial scope.

Repository declarations describe intended configuration, not actual deployed infrastructure. A validation pass does not establish deployment safety. Subscription pricing and demand remain hypotheses; USD1,000/month is not an approved price or a measured outcome.

## User Scenarios & Testing

### US1 — Prepare a real migration locally (P1)

An engineer selects local repositories, a pinned current provider version and target version. AtMem prepares separate reviewable changes and reports exact checks.

**Independent test**: A public-source, frozen breaking-upgrade example fails with a version-only change and passes independent configuration checks after a meaningful migration. An unsupported case remains blocked without changing original repositories.

**Acceptance scenarios**:
1. Given a supported breaking migration, when the user requests preparation, then the proposal contains necessary configuration edits, source-backed rationale, unchanged original files and source-bound results.
2. Given an existing failing baseline, when candidate checks run, then pre-existing failure is preserved and candidate success never hides it.
3. Given a state move, import, replacement-sensitive change, unresolved variable or unsupported syntax, then AtMem identifies the review obligation; it never claims a cloud plan or runtime safety.

### US2 — Coordinate shared modules and consumers (P1)

A maintainer selects multiple repositories and accepted dependency relationships. AtMem prepares compatible module and consumer changes with a review/merge order.

**Independent test**: A shared module, two consuming repositories and an unrelated repository produce the expected affected set, coordinated patches and no unrelated edits. Include a second, structurally different held-out composition.

**Acceptance scenarios**:
1. Given a pinned shared module, when its schema/interface must change, then its consumer changes are staged against the exact proposed module artifact, not a nonexistent published tag.
2. Given dynamic/unresolvable refs or a dependency cycle, then the graph retains unknowns and blocks coordinated-ready status until resolved or a tested compatible sequence is supplied.
3. Given an unrelated or inaccessible repository, then it is not silently modified or counted as verified.

### US3 — Deliver and maintain coordinated PRs (P2)

A repository administrator grants scoped access and enables proposal publication for selected repositories. AtMem publishes related PRs and refreshes proposals after relevant changes.

**Independent test**: An owner-controlled disposable multi-repository organization demonstrates real branch/PR creation, interrupted-write reconciliation, changed-head invalidation, permission revocation and cleanup. Mocks alone cannot qualify this story.

**Acceptance scenarios**:
1. Given review of an exact patch set and permitted publication, then AtMem creates proposal branches and PRs only; never merges, pushes protected branches, tags releases or deploys.
2. Given a timeout after an upstream write, then recovery discovers the existing object before retrying and creates no duplicate branch/PR.
3. Given human edits or changed source heads, then old evidence is stale and AtMem never overwrites human commits; a new proposal needs fresh checks and publication authorization.

### US4 — Maintain a fleet continuously (P3)

A team enables scheduled discovery and bounded proposal preparation. AtMem handles recurring upstream changes, approved holds and cancellations.

**Independent test**: An accelerated schedule across 30 pre-materialized isolated repository snapshots handles duplicate events, held upgrades, changed recipes, budgets and restarts without duplicate work or unapproved publication.

**Acceptance scenarios**:
1. Given an upstream release in the supported matrix, when the schedule runs, then only affected repositories receive deduplicated jobs with visible budget and evidence state.
2. Given an ignored version, spending cap, revoked repository or expired worker lease, then new work stops appropriately and the prior audit history remains inspectable.
3. Given no supported release, then no AI call or proposal is manufactured to fill the schedule.

## Requirements

- **FR-001** Inventory only selected repositories at immutable revisions; record modules, provider constraints, lock identities, roots and source locations, with unresolved dependencies explicit.
- **FR-002** Match reviewed upstream changes using dated primary sources and a versioned applicability contract. Distinguish version availability from supported migration coverage.
- **FR-003** Preserve customer code, comments, accepted architecture decisions and ownership. Work in isolated candidate copies; provide reproducible patches and an exportable migration project.
- **FR-004** Resolve cross-repository dependencies and propose a tested compatible order. Never fabricate module tags or claim checks against a different artifact.
- **FR-005** Record baseline, version-only control and candidate checks separately, including exact source/tool/policy identities, command, exit status, scope and missing inputs. No skipped/stale/blocked check counts as passed.
- **FR-006** Bound repair attempts, execution time, model spend and output sizes. No silent truncation; preserve failures and cancellation/restart state.
- **FR-007** Keep repository/model credentials outside source, exports, model context and logs. Treat repository files, upstream docs and model output as untrusted evidence.
- **FR-008** Before publication, show changes, evidence, side effects and missing manual steps; bind authorization to repository, source heads and patch digest. Never auto-merge, apply, migrate data or write customer state.
- **FR-009** Reconcile uncertain remote writes with durable operation identities; stale leases cannot publish. Human changes and withdrawn permissions cannot be overwritten.
- **FR-010** Maintain tenant/project isolation, per-action audit and deletion policy. Shared learning must exclude private code, decisions and credentials; only separately reviewed public recipes are shared.
- **FR-011** Expose concise accessible progress, failure and next action; complete detail lives in the migration record. Original design/generation workflows keep working.
- **FR-012** Offer opt-in periodic matching with holds, exact target policies and independent compute/publication permissions. Every material change invalidates the appropriate evidence and authorization.
- **FR-013** Publish exact tested support boundaries and release evidence; never infer production state or successful deployment from repository checks.

### Key entities

Repository snapshot, dependency graph, reviewed upgrade recipe, migration project, candidate patch set, verification receipt, publication authorization, remote operation, schedule, budget reservation and audit event. See data-model.md for engineering contracts.

### Edge cases

Missing/ambiguous lock versions; multiple roots/provider aliases; mixed constraints; registry/private/Git/local modules; monorepo shared paths; cycles; inaccessible consumers; archived repos; symlinks/submodules/LFS; malicious tests/provider binaries; credential theft; recipe withdrawal; baseline failures; human commits; webhook replay; canceled uncertain remote writes; partially merged campaigns; lost worker leases; budget exhaustion; incomplete inventories.

## Success Criteria

- **SC-001** Every qualifying migration demonstrates a failing version-only control and meaningful candidate edits. All applicable mandatory checks pass on exact candidate bytes or readiness remains blocked.
- **SC-002** Across the frozen qualification set, affected-set precision and recall are 100% for explicitly resolvable declared dependencies; all unresolved dependencies are visible. These figures describe the fixtures, not arbitrary repositories.
- **SC-003** In failure-injection qualification, retries/restarts create zero duplicate PRs within one serialized campaign coordinator, cross-tenant writes, protected-branch writes, overwritten human commits or new publication intents after observed revocation; in-flight upstream operations are reconciled and disclosed.
- **SC-004** Every reported pass is independently reproducible from recorded artifacts/tool identities; changed inputs invalidate it. All unsupported/blocked cases retain actionable reasons.
- **SC-005** A 30-pre-materialized-snapshot qualification run (fetch/clone timing reported separately) finishes discovery within five minutes on a documented reference machine; per-recipe migration budgets are measured and published before release, not promised without evidence.
- **SC-006** Each story passes unit, boundary-contract and browser journey checks; existing npm/server/browser/build gates remain green. No adoption, revenue or time-saving result is claimed without measurement.

## Assumptions and decisions

GitHub is the proposed first remote adapter. Local operation comes first; hosted scheduling follows explicit qualification. Opt-in authorizes matching and candidate computation; publication requires a separate exact-patch confirmation in initial releases. Stable numbered releases only, with feature/coverage disclosure. User authorization covers specification and review now, not implementation, installation credentials, remote publication or deployment. This owner-directed maintenance feature does not complete or replace the unfinished generic-engine programme (027–029).

## Review-resolved requirements (normative)

- **FR-014** Verify patch safety independently: block new unapproved module/provider sources, external/http data sources, provisioners and CI/automation-file changes. Before each remote action disclose detected CI/Atlantis/Terraform Cloud triggers and unknown automation; draft PRs do not suppress automation. Customer confirmation explicitly accepts those possible side effects. AtMem has no direct deployment capability, but cannot promise customer automation will not deploy after a push/PR.
- **FR-015** Consumer proposals must wait for an actual released module, prove equality with the tested candidate, and revalidate against the fetched release before publication. Separate publication waves require fresh exact-action authorization. Ranged module resolution must be recorded, not inferred from provider lockfiles.
- **FR-016** Before source goes to a model, require explicit backend/data-egress authorization and secret/sensitive-path filtering. Detected secrets are removed or block submission; record coverage limits and require human confirmation of the selected payload. Model vendor retention terms and credential/spend ownership must be disclosed.

R3 uses a customer-owned fine-grained GitHub token in the OS keychain with local bounded polling. Hosted GitHub App credentials and inbound webhooks are R4-only proposals. No credentials are embedded in distributed packages. Unqualified platform sandboxes cannot execute code and must show that limit.
