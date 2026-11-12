# Local engineering and architecture-work candidate

Projects open in Design. Describe the outcome and develop its requirements and components with Architect, then choose **Build this design** to implement the saved design. Build shows implementation progress, files and local checks. Existing engineering jobs remain recoverable through the Build tab. The Codex CLI is the first backend worker adapter; the browser uses project-bound backend APIs. Hosted transport and tenant isolation remain unfinished.

## Start in an installed checkout

Use the Node/Python dependencies in [Installation](INSTALLATION.md). The development environment qualified here uses Node26.5, Python3.14 and Codex0.167.1. The native worker's local macOS sandbox is qualified on this machine; other operating systems are unqualified. Sign in through your installed official Codex client outside the project; do not copy its credentials into the app, a brief or an operator JSON file. The application retains your selected model and effort exactly. This qualification uses `gpt-6.1-sol` / `high`; account entitlement is separate.

```sh
python3 scripts/engineering-preview.py --home /absolute/private/app-data --port 5278 --sidecar-port 8870
```

Choose a new app-data directory and free local ports. The home argument is application data; it does not change the process HOME or Codex's account directory. Open the printed numeric-loopback URL. Stop only this launcher's terminal with Ctrl+C. A missing validator/tool registration remains unavailable; the basic command does not silently find Docker, install tools or pull images.

For local checks, the operator explicitly supplies `--tools`, `--validators`, `--isolation-profiles` and `--validator-endpoint` registrations. These are private machine configuration, not receiving-project build inputs. Tools JSON has `readRoots` and `tools`; the latter admits python/node/terraform/providerMirror/dependencyMirror. Every tool must be within an explicitly approved root. Keep roots narrow and do not register credential directories. Validator definitions select cached immutable image IDs, executable arguments, platform, limits, optional reviewed isolation profile, file applicability and optional pinned runtime receipt. Public dependency mirrors are bounded hash-pinned flat catalogs with provenance/licenses; there is no runtime network resolver or installer. See the operator preparation/evaluation scripts and their `--help` before preparing a new environment. No cloud credentials are needed for local checks.

When runtimes share file names but contain different dependency sets, applicability
may include `anyFileSha256`: up to sixteen objects with exactly `pattern` and
`sha256`. A matching regular file in the immutable capture must have the complete
lowercase SHA256 pin, in addition to the existing anyOf/allOf/noneOf file rules.
Use reviewed dependency-lock hashes tied to qualified runtime inputs. Never use
client/evaluation package hashes to choose or hide checks. The generic selector
does not inspect provider names, run source, resolve dependencies or prove semantic
coverage. Formatting or dependency changes invalidate an exact lock match; inspect
the visible plan and qualify/register the changed contract rather than silently
substituting a runtime. Existing registrations without digest rules retain their
original shape and contract hash. Changes to these rules bind a new check contract;
previous evidence is retained separately.

For a qualified standard or PostgreSQL checker, the operator may explicitly set
`executableScratch: true` to admit freshly installed native dependencies. This adds
only `/dependencies` as bounded executable scratch and sets TMPDIR and
ATMEM_TEST_DEPENDENCY_ROOT there. Source stays read-only, /work and /tmp stay
noexec, and existing nonroot/network/capability/resource limits remain. Default is
false; combination with the browser profile is unqualified and rejected. The
catalogue discloses executableScratchDirectories. Observe/register this changed
runtime binding separately and retain older failed reports. A global package/hash
match does not prove a clean receiving install; do not bypass noexec, spoof module
origins or omit required checks when the offered runtime lacks this capability.

## Manual test card

1. Open Connections and choose Codex with your accessible exact model/effort. Start in Design, describe the project and develop its components or responsibilities. Expand **Architecture activity** while Architect works to inspect public updates, model attempts, evidence lookups and response-format checks. Choose **Build this design** once; the saved context is included automatically, with no repeated brief.
2. Add two meaningful updates while it works. Reload the page. Verify the original request, ordered updates, exact selected configuration and continuing run are retained.
3. Switch to Design and back. Inspect progress without resubmitting the request. Design retains its graph; proposed mappings link native files to the same requirements/context without silently redrawing the graph or changing ownership.
4. On completion inspect the immutable package and each local report. A failed, skipped, absent or stale check remains a limitation. If a bounded automatic repair ran, inspect both original and repaired evidence.
5. If verification definitions have been updated after completion, choose **Recheck and repair** on the current package. Earlier reports remain available; a changed check plan can use at most the original request’s remaining repair allowance. An unchanged plan does not replay work.
6. Download the package; follow its public clean-environment build/test instructions. Receiving instructions must not require the worker's private `.tools` paths. Inspect Terraform and unresolved account inputs; do not apply it.
7. Close/reopen the candidate and select the saved project. Recover existing work if needed; uncertain execution must not be blindly replayed. Preserve its app-data directory and saved project file.

## Alpha.2.1 Design-first and activity test card

Open a fresh project: Design is selected, and an empty design cannot start a build.
Send an architecture request and inspect the expandable activity timeline while it
works. Each recorded attempt retains its exact model/effort, timestamps, public
updates, real host tool actions and format-repair status. Reload and reopen the
history; it must not replay inference. The timeline records public replies and
observed actions, not private reasoning or successful application verification.
Existing older services keep working but cannot supply historical details they
never recorded. Activity references travel in the project file; detailed events
remain in its backend service store. Keep that app-data directory. A service restart
marks unfinished activity as outcome unknown and never resumes it automatically.

**Build this design** starts or updates implementation using the current saved
context. Additional instructions in Build are optional. Reload starts in Design;
select Build to recover the existing job. Earlier alpha.2 remains a separate rollback.

## Alpha.2 shared-model test card

After a current engineering package completes, choose **Link proposed mappings**.
Expand **Architecture work context**. Inspect responsibilities, explicit delivery
units, interfaces, implementation/test file references and the exact artifact hashes.
They remain proposed; linking does not mean a requirement or test passed.

In Design, open a block with a linked requirement, edit that requirement and save.
The block and dependent records need reevaluation; the linked artifact says its
design changed. Accepted decisions and earlier reported outcomes remain retained.
Return to Build and request reconciliation against the current saved design. After
completion, link the new proposed mappings: earlier artifact/record values remain
available and the newest context matches. Save/reopen and compare the same projection
in Design, Build, exported architecture-artifact-mappings.json and the Spec Kit.

For a quick metadata-only example, open the public
[qualified orchard project](../specs/029-general-purpose-engine/evidence/20261111-artifact-reconciliation/native/project-m.json)
with the app's project-file picker. Its two mapping versions and local qualification
receipts are recorded beside that file. Imported metadata is not an authenticated
session: the new installation does not inherit its backend thread or artifact store.
Use it to inspect/edit context tracking; use a fresh project for new native work.
Do not strip old mapping metadata to force a different session to overwrite it.

Work state version1 migrates to2 with existing records/review history retained;
proposal files keep their separate format1. Older candidates may refuse version2
files. Retain those files unchanged and roll back using the older candidate's own
app-data directory, rather than deleting new fields.

## Limits and rollback

This is a runnable local candidate, not complete architecture or cloud acceptance. Independent positive component/system checks and observed failures are recorded under specs029. The current original-case acceptance count and release/owner status live in its progress and release records; generated tests alone cannot establish acceptance. The original28/four-provider programme, compositional lowering, complete-system reconciliation and hosted isolation are still required. Reviewed knowledge is a small pinned corpus, not live comprehensive AtMem. Billing is deferred. No deployment is authorized.

Before testing a candidate, retain the prior source checkout, its app-data directory and a saved editable project file. Use a separate candidate checkout/home and separate ports. To roll back, stop only the candidate launcher and reopen the previous checkout with its own unchanged data. Do not delete stores, copy credentials, overwrite other workspaces or re-submit uncertain native runs. Keep artifact/check receipts from both versions. Local tags and archives are source backups; remote publication and deployment are separate actions.

## Alpha.3 composition manual test card

Open the public `composition-example.atmem-ai-architect.json` beside the alpha.3
release record with the project-file picker. It describes an invoice workflow
and an independent owner-supplied scientific image; it carries no backend session
or cloud credentials. In Design, inspect both units and preserved existing browser
and accounting ownership. Open Terraform: both local modules and their distinct
root inputs should appear. Run Terraform checks and inspect each unit's schema and
mock-test results. Download the delivery ZIP and follow its per-unit task paths.

Add a required connection without an implemented integration contract, or an
explicit memory setting to the scientific container. Scope must remain visible
and blocked until implemented. Save/reopen: both responsibilities and your exact
model/effort remain. The footprint requires a real supplied application image;
schema/mock checks do not execute that image or establish a complete system.
Use Build this design for native engineering work, with the saved scope attached.

Rollback using the previous candidate and its own app home; preserve newer project
files and existing sessions. Do not migrate Terraform state or strip history to
make older software accept a project. Keep MEM0 mounted for candidate dependencies.


## Alpha.4 provider and ownership manual test card

Open http://127.0.0.1:5286 and import
`specs/029-general-purpose-engine/evidence/20261112-alpha4-candidate/ownership-example.atmem-ai-architect.json`.
Inspect the existing website/accounting references beside the new supplied-image
source deployment and invoice unit. Run Terraform checks, download the ZIP and
inspect `deployment-ownership.json`: external identities stay references; new
source has managed resources. Regions and exact model/effort survive save/reopen.

Import `partitions-example.atmem-ai-architect.json` from the same folder to inspect
three independently placed commercial/China/GovCloud units. Inspect native
partition metadata and task-role/repository guards. Deliberately mismatched
repository/region partitions must fail the native negative checks. The supplied
image itself is not executed by these schema/mock checks.

State custody choices remain unverified; the emitted state checker exercises only
a synthetic local HTTP/SQLite contract. Existing-state adoption is unsupported
and must remain blocked. No account access, plan, migration or deployment needed.
Exact source/build/archive/start command and limits are in release-record.json.
MEM0 and the recorded installed dependency aliases are required.

Rollback to the preserved owner alpha.3.1 at http://127.0.0.1:5285/dist/index.html
using its own app home; stop only alpha.4 if needed. Keep new project files,
artifact receipts and uncertain requests unchanged. Do not strip fields or move
Terraform state. Owner acceptance remains separate from automated qualification.

## Operator workspace storage and named validators

`scripts/engineering-preview.py --workspace-root /absolute/existing/workspaces` selects the disk for **new** native workspaces. The directory must already exist on the intended mounted filesystem; missing/unmounted, relative environment paths or files fail rather than falling back. The backend setting is `ATMEM_ARCHITECT_ENGINEERING_WORKSPACE_ROOT`. Without it, existing installations keep `/tmp`. Existing workspace paths and their immutable input receipts remain registered across configuration changes; this setting neither moves nor rewrites them. The browser cannot select this directory.

Use a filesystem with native ownership modes, symlinks and Unix sockets. Keep the resolved workspace path short enough for the existing native worker's Unix-socket limit (its private `.worker-tmp` path must be at most80 bytes on POSIX). An exFAT drive or a long symlink alias does not satisfy those requirements. A separately mounted short-path APFS sparse volume backed by the external disk is one local development option; keep it mounted while work is active. Test modes, symlinks and private sockets before use. Large client artifacts and dependencies should remain on the external disk; do not move an active workspace behind a registered path.

`--validator-workers /absolute/operator/workers.json` loads explicit named worker registrations. It uses the existing reviewed endpoint/profile contracts and does no context discovery, pulls or installations. When absent, an existing `ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_WORKERS` environment setting is retained. Worker placement stays server-owned and independent of the target cloud/model backend.
