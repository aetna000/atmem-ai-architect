# Dependency-bound runtime selection and provider checker preparation

## Reusable engine repair

Different provider runtime packages share Python tests and SQL schema file names.
File patterns alone would select all registered SDK images for the same artifact.
Add optional `anyFileSha256` applicability alternatives: exact regular-file pattern
and lowercase SHA256 pairs, at most sixteen. Existing positive/required/excluded
file rules still apply. Selection reads only immutable captured manifest digests;
there is no source execution, provider/business-name dispatch or dependency resolver.

The operator binds these alternatives to the reviewed public SDK dependency locks
used to build each runtime. Changing bytes, omitting the lock or supplying only a
symlink does not match. Unknown locks need explicit qualification/registration or
manual checks; they are not silently accepted in another image. The plan exposes
required pins and matches. No selected check remains `no_available_applicable_checks`,
which finalization treats as needing attention. Exact bytes are intentionally strict:
even comment-only lock changes need a new reviewed pin. This selects a technical
runtime contract, not complete package compatibility or requirement acceptance.
Several applications can still require additional independent checks.

Legacy rule output and contract identity remain unchanged. New digest alternatives
participate in existing check contract binding, retaining older artifact receipts.
The backend regression captures actual changed files, selects the matching runtime,
rejects a changed lock, preserves the original artifact plan and invalidates the
contract when the operator pin changes. Unknown fields/commands, malformed digests,
duplicate/unbounded rules, linked/missing/wrong-path files are denied.

`lock-selection-v1.json` verifies all four actual SDK materializations with renamed
paths: each exact test lock matches only its own rule; changed bytes match none.
These are manifest-selection fixtures, not completed client applications or holdouts.
`backend-catalog-v1.json` uses real registrations/observations/worker and captured
immutable SDK fixtures with synthetic control rows, no inference. It confirms the
three new runtimes are available and select only their corresponding lock.

## Actual AMD64 runtime preparation

The same operator-owned offline builder now produces Azure, Google Cloud and IBM
Python3.13/PostgreSQL17 check images for Linux AMD64. It additionally asserts actual
built OS/architecture against the selected platform. The SQL qualifier accepts an
explicit platform; its previous ARM64 default remains available. There is no target
fallback. All runtime/application dependency versions remain pinned.

For each provider, the `*-wheels-v1.json`, `*-image-v1.json`, `*-runtime-v1.json`
and `*-qualification-v1.json` files bind exact inputs and results. The38 Azure,
34 Google and36 IBM test-lock wheels are checked against allowed hashes, public
registry metadata, dependency/extra closure, target Python/platform and preserved
embedded notices. Shared wheels were copied by exact version/hash from the existing
public AMD64 mirror; only seven additional locked releases were downloaded. No
package was upgraded. Builds use only cached pinned bases, offline hashed wheels
and the reviewed fixture driver; no model Dockerfile or account operation occurs.

The Python AMD64 platform descriptor48d884… is verified against the unchanged
e48f59… source index. PostgreSQL uses its pinned996e9d… AMD64 descriptor. Empty-source
runtime probes actually initialize/authenticate/query/stop PostgreSQL17.11 and
observe Python3.13.18 plus each requested package version. Installed metadata alone
does not prove imports; `probe-sdk-imports.py` separately exercises actual core and
provider-module imports, RSA JWT verification with wrong-audience/signature denials,
SQL and absence of an AWS SDK fallback inside each target image. Those receipts
prove imports/local cryptography, not managed identity or native cloud API behavior.

All eighteen fixture scenarios across the three images behave as expected: actual
editorial/inventory transactions and roles, wrong-password/read-only/capability/
network denials, fresh state, same-source missing-fixture failure, skipped/zero-test
classification and timeout cleanup. All owned containers are removed without replay.
`runtime-summary-v1.json` explicitly keeps application transfer acceptance false.

`focused-v1.log`:42 focused tests pass. `javascript-v1.log`:553 pass, no skips.
`server-v1.log`:449 pass. `build-v1.log`:production build passes with its existing
size warning. These full regression logs cover the selector change. Actual builds,
observations and SQL/import probes cover the operator-script platform changes.

## Storage and reproducibility

`storage-v1.json` records migration of1,342,830,420 logical bytes of inactive ignored
AWS validation archives to MEM0, after no-open-reader checks. All content digests,
modes and links were verified before cutover; the original path remains a symlink.
Git, source, active candidate worktrees, control databases and owner previews stay
in place. A separate unused public Java base image was archived with verified OCI
blobs and a restore command before removing only its cached reference without force.
That removal did not demonstrably reclaim old-VM filesystem space; no claim is made.

The original qualification VM had only284MiB free after receiving the AMD64 base.
It was neither restarted nor pruned. A fresh2CPU/2GiB local validator VM uses an APFS
sparsebundle stored on MEM0, with32GiB data disk and8GiB root. Its configuration,
cache and disk are external. It does not activate global Docker context, edit SSH
configuration, mount host directories or forward application ports. Its explicit
endpoint is `unix:///Users/javadtaghia/.avm/c/engine/docker.sock`; the original
endpoint remains running separately. Profile/environment locations and volume UUID
are saved in ignored `.local/provider-sql-validator-vm.json`. The use of separate
profile/home/cache variables follows [Colima's official FAQ](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md).

After reconnecting MEM0, mount the existing image if necessary:

```sh
hdiutil attach -nobrowse -mountpoint /Users/javadtaghia/.avm \
  /Volumes/MEM0/AtMem-AI-Architect/validator-vm.sparsebundle
COLIMA_HOME=/Users/javadtaghia/.avm/c \
COLIMA_CACHE_HOME=/Users/javadtaghia/.avm/c/cache \
LIMA_HOME=/Users/javadtaghia/.avm/c/_lima \
DOCKER_CONFIG=/Users/javadtaghia/.avm/c/docker-client \
  colima --profile engine start --activate=false --ssh-config=false
```

Do not attach over an already mounted/nonempty directory. Heavy contexts, wheel
metadata/notices, base archives, logs, fixture data and observed registrations remain
at `.local/external-artifacts/provider-sql-validation/v1`. `validators-observed.json`
is operator configuration for the new endpoint; no owner preview was upgraded.
Use fresh output paths for the existing image builder, runtime observer and SQL
qualifier; pass `--platform linux/amd64` and the explicit new endpoint. Repeat the
import probe only with a fresh output version to preserve earlier evidence.

Retained diagnostics: the first symlinked external VM home resolved to an overlong
Unix socket path, so the new dedicated volume has a short actual mount path. A base
image archive restored unnamed descriptors without repository references; registering
the exact public digest restored those bindings. The legacy builder then tried to
export an incomplete multi-platform index; the verified single AMD64 descriptor
avoids that cache ambiguity. Original failed contexts/logs remain on MEM0. These
were operator preparation failures; no application or check assertion was weakened.

## Remaining scope

Fresh native Azure/Google/IBM applications and independent connected acceptance
remain next, followed by full receiving handoff/resource composition and runnable
alpha.5. Images, SDK imports and fixture checks do not qualify native provider
identity/database/resource semantics or whole client systems. Four increments are
offered,1/28 original is locally qualified, owner acceptance is0 and measured quality
is unknown. All ten increments, original28 and unfamiliar complete local systems
remain in scope. No deployment, cloud account operation or UI/CSS change occurred.
