# Owned native application assembly checkpoint

GE-006 remains in progress. Four runnable increments,1/28 complete original local
projects and zero owner acceptances are unchanged. No alpha.5 or measured-quality
claim. Owner UI/AtFlow CSS, previews/jobs and private projects were untouched.

## Mechanism

An immutable `ApplicationProfile` binds complete component/provider/account/
environment identity, origin, public native identity settings, operation kind,
payload and destination. API/worker use the same derived native task alias and fixed
database-role selection. The complete declaration digest joins persisted destination
identity and human approval. Policy/identity changes keep the alias to find/block
older work; they never silently reinterpret it or erase uncertainty/history.

Native identity and SQL/origin helpers are shared without changing established
invoice behavior. extraction-proof.json proves the old identity implementation and
database/origin helper sections are byte-identical in their new shared modules;
legacy imports remain. Worker startup loads neither API/JWT nor invoice modules.
Account and operation kind are checked before stages; deadlines and reviewed adapter
attributes survive wrapping. Unknown profile code/credential selectors are rejected.

Membership keys derive from the complete verified native subject plus owned issuer
realm, after cryptographic verification. Different realms cannot share an enrollment;
client/scope changes within a realm preserve person identity while rebinding work.
The native IdP remains authoritative; operators retain native-subject mappings and
explicitly enroll roles. There is no automatic enrollment/migration or HTTP role
administration. See docs/architecture/workflow-bootstrap.md for interfaces and scope.

## Counterexample repaired

policy-counterexample.log records a real SQL failure in the initial unoffered
bootstrap: changing the profile to supervisor-only account changes still allowed
an older draft to be approved by its reviewer. Initial implementation bytes and
hashes are preserved on MEM0 in before-policy-source.json. Current regression
rejects this without changing/removing the older operation. Full application
binding and configured-kind checks cover insert, processing, result/edit, approval
and dispatch; mismatched destinations fail before credentials/network activity.
The profile declaration was also extended with pinned native public identity
settings during this unreleased implementation. The old failure and final runs
use their respective versioned source/fixture shapes; no byte-identical profile
input claim is made for this early bootstrap revision.

## Observed checks

- runtime-final.log:16 new checks pass. Four provider profiles use actual RSA/EC
  JWT signatures through the existing native verifiers, distinct restricted local
  API/worker SQL logins, real PostgreSQL/Procrastinate, ASGI HTTP and synthetic
  loopback TLS delivery. Ordinary authenticated users cannot approve; reviewers
  admit exactly one effect and foreign issuer credentials fail.
- Tests also cover immutable profiles, bounded/duplicate metadata, provider/account/
  environment/identity overrides, wrong-account/kind callbacks and misrouted queue
  work, stage deadlines, startup dependency separation, policy changes, full-subject
  keys, changed-issuer membership denial and stable identity across client/scope
  changes. Native credential-factory dispatch is checked for exact provider/role;
  actual cloud credential APIs are not called.
- durable-regressions.log:89 shared-runtime regressions pass, with legacy bindings
  and multi-kind behavior retained. The changed core source remains byte-identical
  through final bootstrap-only refinements.
- emitted-manifest-v4.json:four actual application ZIPs independently unpacked and
  byte-verified, with identical shared helper bytes. This is emission evidence,
  not four-cloud deployment/managed-service execution.
- The exact unpacked AWS dependency-context package runs its own tests/run.py:
  131 tests across14 suites pass, no skips, package sources unchanged. Its receipt
  is emitted-package-current.receipt.json. The previously installed hash-locked
  environment is reused after verifying the emitted test lock is identical.
- 537 JavaScript/430 server tests and production build pass in *-v4.log.
  source-manifest.json binds final source and dependencies; commands.json records
  actual commands. Bulk archives, setup artifacts and detailed package logs stay
  on MEM0; active project/session stores stay local.

runtime-v1/v2 were earlier10-check checkpoints; v2 added restricted SQL logins.
runtime-v3 added policy binding; v4 added membership realm tests. Earlier emitted
128/130-test receipts are retained beside the final131-test receipt. The failing
policy regression is intentional historical evidence, not an outstanding failure.
Intermediate broad-check logs are retained; *-v4.log binds the final code. Final
v4 removes one trailing blank line from shared configuration (AST unchanged);
exact package131 tests and broad checks were repeated for those bytes.

## Limits and next action

Public-key lookup and database connections are explicit local test injections.
No real IdP, managed database, cloud IAM/network, regional service availability,
business processor or vendor destination is qualified. This is application assembly
and component/connection evidence, not a complete original or hosted SaaS system.
Tests create only synthetic data/roles in the nonce-guarded local fixture. No cloud
account operation, schema migration, deployment or existing-work migration occurs.

Next connect shared architecture-model intent to generated per-unit profiles,
provider resource/environment linkage and executable entrypoints. Preserve real
domain behavior and source/ownership boundaries, qualify connected application
failures/handoff and freeze runnable alpha.5. All remaining increments and original28
plus unfamiliar complete local systems remain required.
