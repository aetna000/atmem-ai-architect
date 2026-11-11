# Explicit executable dependency scratch

## Engine change and invariant

Operator registrations may enable `executableScratch: true` for standard or local
PostgreSQL checks. The default remains false; the unqualified browser combination
is rejected. Browser/model requests still select registered validator IDs and cannot
supply this setting, mount paths, images, commands or arbitrary environment values.

The capability adds only a128MiB `/dependencies` tmpfs with exec/nosuid/nodev and
sets TMPDIR plus ATMEM_TEST_DEPENDENCY_ROOT to that directory. Source remains
root-owned/read-only; /work and ordinary /tmp remain noexec. UID65532, empty effective
capabilities, no-new-privileges, network-none, no host mounts/socket, read-only image
and existing CPU/memory/process/output/deadline bounds remain in effect. Code loaded
from scratch is untrusted check code with those same privileges. This deliberately
admits temporary native code; it is not a claim of complete security acceptance.

The public catalogue discloses executableScratchDirectories. Registration/check
contracts and runtime observations bind the capability; observations without it
cannot qualify it. Legacy default runtime-binding/spec shapes remain unchanged.
Older reports and failed artifacts are retained rather than rewritten. Fresh
handoffs explain the capability, missing prerequisites and forbidden workarounds.

## Evidence and counterfactual

The native Azure run exposed the gap: the image had the exact required packages,
but a clean receiving install into noexec temporary storage could not map its native
extensions. Standard package metadata and global import/hash equivalence are not
clean-install proof. Preserve that failure and all required assertions.

- `default-denials-v1.json` and `enabled-denials-v1.json`:actual copied CPython C
  extension loads across museum CSV/weather JSON examples. Default scratch denies
  loading; enabled scratch loads and executes both extensions. Both cases verify
  ordinary tmp/source noexec, root read-only, UID/capability/root-escalation and
  network/socket denials. No policy bypass or alternative loader is used.
- `checkpoint-before-v1.json` and `checkpoint-after-v1.json`:identical immutable
  native Azure checkpoint, same AMD64 image/command/120-second budget. The original
  noexec check fails at fresh native imports; executable scratch passes all16
  generated tests, zero skips. Source/assertions were not changed by the evaluator.
- `final-package-after-v1.json`:the actual settled archive
  `22d35c9d11612c91094b4b1e89b1a429000e5ae0be9dc3a6697758ab8843f7ab`
  independently passes all16 in96.46seconds. Its stricter receiving verifier excludes
  global dependency sites, checks all38 distribution versions/origins and key native
  module origins, executes restricted SQL and synthetic RSA verification. Real
  HTTP/queue/children/TLS, identity/role/revision/fence/restart/unknown tests also run.
  Generated tests do not replace independent client-semantic acceptance.
- `runtime-observation-v1.json`:new empty-source observed runtime binding explicitly
  includes executableScratch. It is not reusing the old noexec observation.
- `focused-v1.log`:33 focused contract/evidence/delivery checks pass.
  `server-v1.log`:452 pass; `javascript-v1.log`:553 pass; `build-v1.log`:production
  build passes with the existing size warning. Three new tests cover strict operator
  flags/combinations, observation binding and old-check/contract retention.

`probe-scratch.py` reproduces the native-extension counterfactual with fresh output.
Heavy archives and detailed results stay on MEM0 under
`.local/external-artifacts/executable-dependency-scratch`. The final native app's
original pins are unchanged. Its baseline service was frozen atde77256; the new
capability was qualified separately after that run, not silently injected into it.

Next activate the explicitly observed registration only after the synthetic service
is idle, retain its old plan/reports and recheck the exact artifact without new
inference. Independently review the generated domain/provider/receiving image and
shared-runtime adaptations. No release/original28/whole-system acceptance follows
from this checker change; existing owner previews and UI/CSS are untouched.

## Activated synthetic API checkpoint

The synthetic service was verified idle and restarted on frozen6c71fb7 with the
new separately observed operator registration. `api-activation-receipt-v1.json`
records a same-artifact recheck through the actual backend: local_checks_passed,
16 tests, zero skips,95.472seconds, executableScratch true. The prior failed
check/needs_attention plan remains in history under its original contract. Exact
gpt-6.1-sol/high and original run remain unchanged; complete pagination of1506
events confirms only the original and one automatic repair were accepted. The
recheck submitted no inference. This is local generated-suite evidence only.

The next step stated above is now complete for this isolated synthetic service.
Independent connected-domain/provider/receiving-image assessment remains pending.
Owner previews, UI/CSS and other registered profiles are unchanged.
