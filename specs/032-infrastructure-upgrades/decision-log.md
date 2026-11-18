# Decisions and scope

- 2026-11-17: Owner requests full development against this specification and release train. Implementation begins locally on `feat/infrastructure-upgrades`, incorporating public main 0.2.4. Remote migration publication, npm publication and hosted deployment retain their separate authorization gates.
- T001 selection: Terraform 1.17.2, AWS provider 5.100.0 → 6.0.0, Batch queue `compute_environments` → ordered `compute_environment_order` blocks. Qualification must demonstrate a real schema failure and an independently specified passing rewrite before R1. Unsupported expressions remain blocked; no state writes, plans or deployment tests.
- Structured parser: python-hcl2 7.3.1 (MIT), Lark 1.3.1 (MIT), regex 2026.11.15 (Apache/CNRI). Use concrete AST source ranges to preserve comments and expressions; no regex-based HCL rewriting. New maintenance dependency lock remains separate until packaging qualification.
- Integration: reuse the digest-bound DockerValidationWorker controller, never a host shell runner. Native Linux containers require independent maintenance qualification on each advertised architecture. macOS/Windows without a qualified Linux VM are inventory-only. Current local qualification target is macOS arm64 with Colima Linux arm64; amd64/Windows remain unqualified.
- Governance: R3 remains fine-grained customer tokens in OS keychain with bounded outbound polling. R4 hosted/local constitution alignment is unresolved and blocks hosted maintenance; existing hosted Architect functionality is not maintenance authorization.
- R1 source acquisition uses explicitly selected browser file bytes rather than an HTTP host-path picker. It cannot follow Git hooks, submodules or LFS fetches. Missing module artifacts remain unresolved; no arbitrary host path reaches the API.
- R1 nested records inherit aggregate tenant/project scope. Unknown scope fields are rejected, preventing inconsistent nested ownership. Portable imports rebind the aggregate to the receiver, retain source/tool receipts and remove current readiness. This refines the proposed data-model layout without changing authorization requirements.
- Initial drafting is a deterministic reviewed AST recipe, with one attempt and zero model calls/spend. Source-egress filtering/confirmation and aggregate budget primitives are present for future adapters; no implicit model permission exists.
- Baseline initialization never upgrades an inconsistent existing lock. Candidate locks preserve the independently computed Linux h1 and add 14 pinned official archive zh checksums; exact locked candidates must reproduce. Other host execution platforms remain blocked, not implicitly certified by checksums.
- R1 qualification uncovered older browser fixtures targeting retired navigation/labels and missing the activity callback argument. Refresh those fixtures against the accepted five-stage UX, preserving numeric, artifact, memory, explicit-change, undo/reset and mobile assertions. Configure optional test runtimes from existing pins; do not weaken product gates to hide missing dependencies.

- 2026-11-16: Owner authorizes Spec Kit and read-only Claude Opus 5.5 Medium review, with release planning after agreement. This turn creates planning artifacts only.
- Proposed workstream032 is adjacent to Architect and preserves027–029 unfinished scope. No engine quality, migration coverage, paid subscription or release is claimed.
- Local AWS/Terraform migrations precede multi-repository and GitHub publication; exact source/target recipe research is an R0 blocker. No provider default borrowed from a model response.
- User-confirmed exact-patch publication remains separate from opt-in recurring compute. No auto-merge/apply/state/import/database operation exists in initial scope.
- Stable0.3.0–0.6.0 release numbers are proposals, subject to latest package/version and owner release authorization. No alpha/beta naming.
- Generic graph, artifact identity, budgets, reconciliation and source evidence are reusable mechanisms. Per-provider migration recipes are explicit adapters; transfer/negative cases required.
- Older `.specify/memory/constitution.md` local-only wording conflicts with hosted expansion; R4 requires explicit alignment, not silent reinterpretation. Owner's new request authorizes this scope's planning but not arbitrary governance edits.
- Opus review round1 B1 accepted: choose local customer-owned fine-grained token in OS keychain plus polling for R3; defer App broker/webhooks/governance alignment to R4.
- B2 accepted: patch verifier rejects executable-source/CI changes; exact-action preview warns that customer automation can run/deploy. Draft status is not CI isolation.
- B3 accepted: add release-observation equality, pending states, fetched-release consumer rechecks and separately authorized publication waves. R2 uses explicitly labelled local operator-release simulation; R3 real observations.
- B4 accepted: explicit model egress permission, sensitive-path/secret filtering and confirmed payload with credential-owner/aggregate-budget attribution.
- Nonblocking review accepted: explicit conditional Git write mechanism, coordinator scope for deduplication, per-OS sandbox matrix, debounce/budget admission, schema-error breaking class, single project aggregate and materialized-snapshot timing.
- Opus round2 agrees with planning/release sequence, zero blocking findings. Close N1–N10 with source-selection egress confirmation (derived repair requests individually filtered; changed source scheduled jobs wait for confirmation), proposal-ref allowlist, commit-SHA provenance, explicit approved module release refs, broader CI trigger disclosure, R0 coverage measurement, per-owner keychain tokens, R2 simulation label and terminology fixes. No broader authorization granted.

### R1 private source compatibility and general generation

Maintenance exports use project format 4.0.0; ordinary designs retain 2.3.0 or approval format 3.0.0. Older released readers reject the new major rather than forwarding unknown private maintenance extensions into general generation. Current imports preserve source but demote receipts to historical. General model projections omit maintenance repositories, patches and diagnostics, retain all design requirements, and use the compatible ordinary/approval format. Original private context bytes and their separate digest remain authoritative. Tests cover initial and supplementary model contexts and legacy imports.

### R2 graph boundary

Use separate selected roots and explicit remote materialization bindings; R1 snapshot history remains history. Preserve provider aliases, constraints and provider maps as declarations; do not infer registry resolutions from lockfiles or solve versions implicitly. Source-local modules resolve only inside the same selected repository snapshot. Unknown refs, missing modules, stale bindings and cycles block coordinated readiness. Graph discovery alone is not a checked migration. Frozen fixture module names differ between consumers; bindings must use each actual name.

### CI-discovered hosted project creation race

R2's hosted transactions CI exposed an existing interleaving: creation read an uploading receipt, another identical request completed it, then the first caller's duplicate chunk was rejected. Completed uploads now acknowledge only a byte-identical retained chunk, with the same index/size/hash, without writing or changing content. Altered, canceled, missing and foreign chunks remain denied. A deterministic test completes the real nested creation between begin and put; existing concurrent creation and storage tests remain required. This is a regression repair, not a hosted maintenance rollout.

### R3 broker and publication foundation

Native macOS Keychain uses Security.framework directly; no token is placed in subprocess arguments or plaintext fallback files. A dummy round-trip and deletion was exercised; six broker protocol tests use fake HTTP and confer no network acceptance. The CLI prompt is out of band, with explicit selected owner/repositories/project and expiry.

Private publication authorizations, intents, leases and branch claims stay outside portable campaigns. First proposal refs point to a unique nonce-bound candidate commit rather than the shared base commit, so an uncertain ref response cannot silently adopt another installation's base branch. Canonical Git object hashes are independently checked with Git. Exact approvals expire after 15 minutes, serialize a campaign, and must disclose automation. Unknown PR outcomes are reconciled, never blindly repeated. Module-wave fake protocol checks pass, but the coordinator remains inactive: consumer release observation, checked refresh, UI and T016 actual network qualification remain unfinished.

R2 client CI passed all three OS clients on c302bd7; the hosted creation race repair also passed Firestore transactions/native worker CI. Campaign readiness now becomes historical when its current worker is missing or has changed, in addition to policy changes.

## R3 development follow-up: gated UI, receipts and inert CI

Implemented default-closed local publication routes/UI, private authenticated module-release observations, separate consumer wave confirmation, partial-merge invalidation and expected-head conditional refresh. Browser reload is read-only; it restores no authorization. Confirmed PR creation receipts appear immediately even during the bounded remote poll interval; creation receipts do not invent merge observations.

Campaign root projection preserves known automation files as inert bytes while nested executable Terraform/configuration layouts remain blocked. Independent patch policy still refuses automation changes; the isolated worker never executes repository CI. Real offline worker checks plus fake GitHub demonstrate preserved CI bytes and explicit automation disclosure. These are not actual GitHub acceptance.

Prepared a staged real acceptance driver and exact four-repository private scope in r3-acceptance.md. No repository creation, account token enrollment, remote publication, tag, merge, cloud start, public release or hosted maintenance deployment was performed. T016 authorization/remote evidence and later R4 governance alignment remain mandatory.
