# Deferred public native-output bindings — GE-006 checkpoint

Reusable capability: a component can declare its shared application source before
native public identity/origin/destination outputs exist. The source declaration
retains exact ownership, provider, environment, logical account, operation and
payload policy. Only the documented public input fields can be deferred. A bounded
public-output ledger resolves exact component/provider/environment/name references;
it never looks up a cloud, chooses a fallback or changes fixed policy.

`approval-application-template-v1` survives structured proposals and save/reopen.
The generator emits `application-template.json`, the shared runtime, API entrypoint,
exact locks and `resolve-profile.py`. It emits no invented concrete profile. Run:

    python -I resolve-profile.py --outputs /ABSOLUTE/PUBLIC-OUTPUT-LEDGER.json --out /ABSOLUTE/FRESH-BINDING-DIRECTORY

The owned API loads that directory as `runtime-binding` (read-only mount in an
operated installation). The concrete profile and matching receipt must both exist.
Startup re-resolves receipt inputs against the current immutable template; missing,
partial, changed-policy or mismatched artifacts fail before native runtime setup.
A fresh output directory is required. Receipt-last publication detects interruption;
it is not a filesystem durability or cryptographic attestation protocol.

Each ledger record contains componentId, provider, environment, public output name,
string value, sensitive=false and sourceSha256. Source digests are supplied metadata,
not proof that the source is authentic, reviewed or deployed. Duplicate identities,
mixed snapshots for one owner/environment, sensitive/credential-like records and
missing exact references are rejected. Secret-name/credential heuristics do not
certify an arbitrary value as public; operator review remains necessary. Public
records are limited to 128 and artifacts to 64,000 UTF-8 bytes. The receipt retains
only consumed records. Native adapter semantic/identity validation still runs at
runtime; the resolver provides structural binding only.

The Spec Kit builds application source before component resource tasks. A separate
binding task depends on the source assembly and every declared native-output owner,
including the application's own public origin. Connected acceptance depends on
binding. This avoids making source construction depend on its future runtime IDs.
Source-owner changes invalidate the dependent application review context.

## Observed evidence

- `template-manifest-v1.json`: four real provider-context projects saved/reopened,
  exported, zipped, unpacked and byte-checked. All runtime IDs are explicitly
  synthetic evaluation inputs kept separately from the original templates.
- Four `*-entrypoint-v1.receipt.json` files: exact emitted isolated resolver CLI,
  failure before native setup for missing/partial/foreign receipts, then actual
  emitted API with native JWT signatures/synthetic key lookup and restricted local
  PostgreSQL role; durable enqueue, one queue row on replay, account override denial
  and ordinary-member approval denial. No source was patched after emission.
- `handoff-manifest-v1.json`: four actual complete handoff ZIPs, exact file hashes,
  dependency existence/cycle checks, owner prerequisites and E2E binding dependency.
- `native-config-equality.json`: the concrete/deferred declarations on the same
  graph emit byte-identical Terraform/lock files on all four providers. Native
  schema checks were not rerun or claimed for this change.
- `js-final-v3.log`: 552 JavaScript tests, no skips; includes four provider template
  exports, context invalidation, producer parity, closed policy and task DAG checks.
- `server-final.log`: 434 server tests, including actual proposal preservation and
  owner/provider/environment/note/sensitive-reference denials. No runtime SDK is
  required to validate application declarations.
- `regression-manifest-v2.json` and `package-regression-v2.receipt.json`: exact
  emitted AWS-context regression package; 138 tests across 15 suites, no skips,
  unchanged source hashes. Includes seven new binding tests and all 131 existing
  extraction/HTTP/identity/worker/operator/shared-policy regressions. Actual
  loopback SQL/queue/TLS are distinct from synthetic provider/model protocols.
- `build-final-v2.log`: production build passed; existing bundle-size warning.

Bulk ZIPs, unpacked packages and fixture bindings remain under the ignored MEM0
mount `.local/external-artifacts/deferred-bindings`. Source, scripts, test receipts
and hashes stay local/in Git. `commands.json` records reproduction; choose fresh
artifact revisions and use only the nonce-guarded owned local SQL fixture. Exact
emitted dependency lock hashes match the reused locked qualification environment.
The earlier pure harness import failure is retained in `runtime-v1.log`; the harness
was corrected to add its own test directory under isolation. No guard was weakened.
`runtime-v2.log` and regression-v1 are earlier passes; v2 also checks stale-template
policy rejection. The CLI import path was fixed at the generator before qualification.

## Limits and next dependency

This transfers shared public binding/API mechanisms to an equipment-review contract
across the four existing native identity adapters; it does not infer or implement
business behavior from that contract. No provider resource linkage, domain worker,
cloud identity/SQL service, complete application or new original-case acceptance is
proved. Imported provider outputs are reviewed public inputs, not automatic Terraform
output extraction or source attestation. Model/backend selection was unchanged; no
model inference or account/cloud operation was run. UI/CSS and existing previews
were untouched.

Next implement provider resource/environment and executable domain/worker linkage,
then connected requirement/handoff acceptance and a frozen runnable alpha.5. The
programme remains four offered increments, zero owner acceptances and one original
complete local qualification out of 28; quality is unmeasured. All ten increments,
original 28 and unfamiliar complete systems remain in scope. This checkpoint earns
no additional release.
