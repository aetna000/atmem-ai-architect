# Research and decisions — 2026-11-16

## Product capability

Decision: prepare meaningful infrastructure migrations, not just notifications/version bumps. Rationale: AWS Health already identifies lifecycle events/affected resources; Renovate already updates Terraform dependencies. A strong model can perform isolated migrations; enduring value would require reliable inventory, coordination, validation and maintenance. Alternatives considered: provider alert feed (insufficient), architecture handoff (already core), performance optimization laboratory (large execution expansion).

Primary references checked during concept research:
- https://docs.renovatebot.com/modules/manager/terraform/ — updates providers/modules/constraints; do not claim that version updates are unique.
- https://docs.aws.amazon.com/health/latest/ug/aws-health-account-views.html — events and affected resource state; repo intent remains different from actual deployment.
- https://developer.hashicorp.com/terraform/language/syntax/configuration — parser must support actual HCL, not diagram regex.

## Execution and adapters

Decision: backend-neutral local core first, separate scoped GitHub broker and isolated check executor. Rationale: existing worker sessions provide integration candidates, not assurance that arbitrary repo tests are safe. Alternatives: run tests in checkout (rejected ambient secret/host risk), give GitHub token to agent (rejected), website diagram parser as authority (rejected incomplete language semantics).

Decision: Terraform AWS provider migration first with a reviewed per-recipe version matrix. Choose exact real source/target pair, parser/tool versions and migration oracle in T001/R0 using pinned official upgrade guides and reproducible failure. These are explicit research deliverables before coding, not fabricated resolved compatibility facts. If exact pair cannot demonstrate a meaningful change, R1 cannot begin.

Decision: use isolated overlays for proposed local/shared modules and record their digests; original Git/registry addresses in final patch require real version publication and human confirmations. Alternatives: invent a release tag or change customer module source to temporary disk (rejected).

## Governance and release

Decision: stable 0.3.0–0.6.0 proposals, no alpha/beta; numbers subject to current latest at release. Workstream does not reset027–029. Existing older constitution's local-only wording requires explicit alignment before hosted R4; plan cannot silently amend it. Owner-approved feature scope supplies authority for this specification, not production writes.

## Research backlog with blocking outputs

T001 must pin provider upgrade guide/source commits, Terraform tool hashes, parser/license decision, affected-schema diff, unsupported patterns and expected success/failure checks. T002 freezes fixtures and holdout. T003 qualifies worker isolation. R0 closes only when all outputs have receipts. No deployment plan/data migration qualification is inferred from local tests.

## T001 implementation contract — 2026-11-17

First recipe: `aws-batch-queue-v6`, exact AWS 5.100.0 → 6.0.0, Terraform 1.17.2. The version-only control must fail on `compute_environments`; the candidate replaces an explicit, nonempty list with ordered blocks, preserving each expression and ordinal. Dynamic lists, conflicting existing order blocks, computed old-attribute references and missing exact provider versions are unsupported. Do not infer state or replacement safety from validate.

Primary guide is pinned to provider commit `887f72b40b1d74adbb77b5fc7cf70acd2058064a`, [Batch queue migration](https://github.com/hashicorp/terraform-provider-aws/blob/887f72b40b1d74adbb77b5fc7cf70acd2058064a/website/docs/guides/version-6-upgrade.html.markdown#resource-aws_batch_job_queue). Artifact URLs, official checksum URLs and verified SHA256s are retained in `evidence/tool-artifacts.json`. Full schemas and baseline/control/oracle receipts are generated independently by real provider executables during R0.

Parser contract: python-hcl2 7.3.1 concrete Lark AST with byte-independent character source offsets, not evaluated expressions. Parse failures block. Source edits apply in reverse range order; untouched bytes remain untouched. Default-deny JSON HCL until a separate structured JSON policy is qualified. Bound files, total bytes, parse time and snapshots. Resolve only explicit sources; computed module sources/ranges/aliases remain recorded unknowns until graph qualification.

Execution: existing `server/local_validation.py` provides stdin-only artifacts, no host mounts, dropped UID, denied network, fixed image/command, output/time/resource limits and cancellation. Register a dedicated maintenance profile after actual provider memory measurement. Provider installation uses an official checksum-verified packed offline mirror; no remote fetch, credentials, arbitrary test commands or source Dockerfiles in execution. Hostile tests must exercise denied network, host secrets, source mutation and privilege changes. Unqualified image/platform fails closed.

Patch policy measures resource/data/block ASTs plus paths: provisioner, external/http data, remote backend/cloud blocks, source changes, `.github/**`, `.gitlab-ci*`, Atlantis and unknown executable constructs block readiness. Existing constructs are not grandfathered. Terraform's expression functions are not evaluated by inventory. Validation is sandboxed even after static screening. Missing automation files cannot establish absence of external automation.

R3 identity contract: per-resource-owner fine-grained token, metadata/contents/PR scopes only; OS keychain required, bounded polling, token expiry/revocation checked. Independently enforce `refs/heads/atmem-upgrades/` campaign ownership, deny default/protected/unowned refs and bind confirmation to exact source/patch/policy for 15 minutes. No workflow writes, merge, tag, release, cloud plan or apply capability. R4 governance conflict remains explicit in decision-log; no hosted scheduler adapter before resolution.

### R3 conditional-write research (development follow-up)

Primary contracts checked 2026-11-17: [GitHub commit mutation](https://docs.github.com/en/graphql/reference/commits), [Git references](https://docs.github.com/en/rest/git/refs), [pull requests](https://docs.github.com/en/rest/pulls/pulls), and [fine-grained permission requirements](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens). A preflight head read followed by unconditional ref update is not a compare-and-swap. The broker should append proposal commits with `createCommitOnBranch` and its expectedHeadOid contract; create refs atomically and reconcile uncertain results against exact persisted intent. Never use force ref updates or infer branch ownership from commit authorship. API behavior and race handling still need the R3 actual disposable-repository qualification.

For a macOS keychain adapter, use [Security framework generic-password items](https://developer.apple.com/documentation/security/adding-a-password-to-the-keychain) and SecItemCopyMatching/Update/Delete; do not place token bytes in process arguments. Other platforms stay publication-blocked without a qualified OS credential-store adapter. A local in-memory fake may test broker contracts but cannot qualify keychain or remote behavior.
