# Clean Linux private application core

`scripts/build-enterprise-runtime-lock.py` derives the exact 33-package CPython
3.13 Linux/amd64 closure for company identity/MSAL, encryption, HTTP, PostgreSQL
and Procrastinate from already reviewed metadata. No unpinned resolver upgrade or
ambiguous dependency is accepted. Native model/secret SDKs and production factories
are separate unfinished dependencies; this lock does not claim to implement them.

`enterprise-runtime.Dockerfile` builds from the reviewed Python platform digest,
downloads only hash-locked binary wheels, installs offline, checks the installed
dependency consistency and removes pip/ensurepip. The final process runs as UID
10001. It includes the already reviewed hash-pinned zlib security update from
`python-container-lock.json`. Its default command explicitly refuses to act as a
configured service: a production company factory has not yet been supplied.

The first clean import run caught an omitted implementation dependency: both the
cache and application RPC client imported the isolated parser's module for shared
validation. `enterprise_document_contract.py` now owns that byte/MIME/text contract
using only the standard library. The API/worker image does not include or import
the parser implementation, JVM, Office parser or OCR executables. The parser
reexports the existing names and uses the same contract without weakening limits.

## Qualification

`scripts/qualify-enterprise-runtime.py` builds a unique image and checks:

- Exact installed package inventory, real Python patch version, non-root identity
  and imports from the image's `/app`, without host Python packages or parser code.
- All 45 company identity/native-source/model-boundary policy tests offline.
- 57 actual SQL/encryption/queue-store/cache tests on each owned PostgreSQL 17/18
  fixture, with a fresh synthetic database/role and the fixture ownership guard.
  The actual SQL version is checked before each suite group.

The runtime is read-only with bounded memory/PIDs/CPU/tmpfs, dropped capabilities
and no added privileges. Only SQL checks join the existing owned database network
namespace. Qualification files and private synthetic fixture credentials enter via
stdin into tmpfs, never host bind mounts, image layers, command arguments, Docker
Env or retained logs. Test code can load qualification helpers, but application
modules resolve to the actual installed image. Container inventory excludes Env
because it contains the database fixture password.

The actual parser's 16 Office/PDF checks and composed 14-check queue/cache workflow
were rerun after splitting the protocol. Every composed question still rereads
current source bytes. Vendor and model HTTP remains scripted; these are not native
source-account or model-quality tests. The Linux core checks do not include the
queued HTTP fixture suite, browser, native secret/model factories, deployment
provisioning or all four provider exports.

## Preserved findings and next work

Early Linux qualification failures retain evidence of missing VM host mounts and
the omitted parser module. The qualifier now transfers fixed test assets via stdin
and uses an explicit protocol-only application dependency. Parser qualification
also caught BuildKit treating a bare local `sha256:` image ID as a repository name;
it now creates a unique owned build tag for the already inspected exact base.

The initial core scan found two fixable HIGH zlib findings. The pinned Debian
security package was already reviewed for the common Python image; the new core
now installs it too. Current primary status:
[Debian CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091)
and [Debian CVE-2026-76844](https://security-tracker.debian.org/tracker/CVE-2026-76844).
Keep the scanner's original results, including inconsistent display titles. A
successful scanner exit is not security acceptance, and unfixed findings remain.

Continue with native model/secret factories, durable audit and operator membership/
source mapping provisioning, provider-specific per-file parser isolation, all four
native Terraform/application/Spec Kit exports and actual private-project cases.
Then finish the other families and final full28/held-out evaluations. No new
generator capability or completed medium project is advertised by this checkpoint.
