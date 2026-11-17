# Infrastructure maintenance — local development candidate

AtMem prepares a reviewable Terraform migration. It never edits the selected source
directory, merges changes, accesses cloud state or deploys infrastructure.

The first supported recipe converts explicit AWS Batch queue compute-environment
lists into ordered blocks when moving **AWS provider 5.100.0 to 6.0.0**, using
**Terraform 1.17.2**. This is an intentionally narrow, real breaking migration.
Other provider versions, arbitrary migrations, dynamic lists, unresolved modules
and state-sensitive work are not qualified by this recipe.

## Local setup

Execution currently requires **Linux arm64 containers**, tested locally using
Colima on macOS arm64. Docker must be running. Native Linux hosts, Windows and
other image/platform combinations remain blocked until independently qualified.
The inventory and export interfaces do not imply execution support on those hosts.

From this development checkout:

```sh
uv pip install --python .venv/bin/python --require-hashes -r server/maintenance-requirements.lock
.venv/bin/python scripts/setup-maintenance-worker.py \
  --endpoint unix:///absolute/path/to/docker.sock \
  --output /absolute/private/product-data/maintenance-worker.json
```

The socket is explicitly operator-selected. For Colima it is typically
`unix:///Users/YOUR_USER/.colima/default/docker.sock`.

An installed candidate also supports:

```sh
atmem-architect --maintenance-setup --docker-endpoint unix:///absolute/path/to/docker.sock
```

This command downloads checksum-pinned public tools and a pinned Python container
base, builds a local image, then runs actual hostile isolation, cancellation,
timeout and output-bound tests. No customer source, model credentials or cloud
account credentials are used. Allow approximately 5 GB of local disk space for
downloads, unpacked providers and image layers. Setup is separate from checks;
checks never pull images or fetch remote dependencies.

Tool downloads and build contexts stay beside the private worker configuration,
including for global npm installations. The installed package is never made writable.

Keep the configuration and adjacent `.qualification.json` private. Registration
binds the exact cached image, architecture, runner and controller policy. Changed
tools require rebuilding and requalifying. Development can select registration
with `ATMEM_ARCHITECT_MAINTENANCE_WORKER_CONFIG`; otherwise the application reads
`maintenance-worker.json` in its private product data directory.

## Prepare and review

1. Open **Infrastructure upgrades** in the local workspace.
2. Select the Terraform folder, then **Inspect files**. Dependencies, state, tfvars
   and secret files are excluded or rejected. No path authorizes host filesystem
   exploration. The browser submits the explicitly selected UTF-8 files.
3. Review selected paths and click **Prepare migration** to approve local compute.
4. AtMem checks the original baseline, demonstrates the version-only break, prepares
   the structural patch, generates the target provider lock and rechecks exact
   candidate bytes. Real phases are shown; no invented percentage is displayed.
5. Review the diff and export the migration with source-bound receipts. Imported
   receipts are historical and must be reproduced before current readiness.

Existing locks must verify in the registered Linux worker. Initialization failures
remain blocked with diagnostics; AtMem never loosens checksums to force an upgrade.

The selected directory remains unchanged. The first recipe is deterministic;
**no source is sent to an AI model and model spend is zero**. Future model adapters
must use separate backend/source/terms confirmation and aggregate spending limits.
Pattern scanning cannot prove arbitrary source secret-free; review the selection.

Maintenance source, patches and diagnostics are also withheld from the ordinary
Architect generation context. Private saved files and exports remain complete;
model-readable projections explicitly mark the withheld section and bind both hashes.

Schema validation does not inspect deployed state, prove absence of replacements,
run an account-specific plan or establish deployment safety. A destination operator
must review provider state upgrades, authorized plans, rollout and rollback.

The initial worker runs only fixed `init`, `validate` and schema-inspection commands
offline. Existing provisioners, external/HTTP data sources, backend/cloud blocks,
overrides and Terraform test files block readiness. Application tests, hooks and
automation are never executed by this worker. Repository automation is disclosed;
absence of workflow files does not prove absence of external automation.

Bounds: 1,000 selected files, 2 MB per file, 8 MB selected source, 64 MB portable
migration aggregate, 20 minutes per job and three maximum repair attempts. This
deterministic recipe makes one drafting attempt. Oversized inputs fail explicitly;
files and evidence are not silently truncated. Architect's enclosing project-file
format retains its existing 2 MB limit; larger migrations use the separate migration
export. Do not claim an enclosing project save succeeded when that limit is exceeded.

## Reproduce checks

```sh
ATMEM_MAINTENANCE_TEST_CONFIG=/absolute/path/maintenance-worker.json \
  .venv/bin/python -m unittest discover -s server/tests -p 'test_maintenance_*.py' -v
node --test tests/maintenance/*.test.mjs
ATMEM_MAINTENANCE_TEST_CONFIG=/absolute/path/maintenance-worker.json \
  node scripts/maintenance-smoke.mjs
```

Without explicit local worker registration, actual-container tests are skipped and
cannot qualify a release. Evidence distinguishes these runs from unit tests.
Fixtures include a different alias/local-expression composition and a pre-existing
failure that must remain failed. Source-pinned qualification and the release gates
are tracked in `specs/032-infrastructure-upgrades/`.

## Release boundary and rollback

This branch is under development. No npm maintenance release or hosted maintenance
deployment is claimed. Public stable versions and remote repository writes retain
their separate owner-approval gates. R2 adds dependency coordination; R3 adds actual
confirmed GitHub publication; R4 remains gated on hosted governance and qualification.

To disable local execution, stop Architect and remove or move its maintenance worker
registration. Existing source folders are unaffected. Export evidence before deleting
the private maintenance SQLite database. Do not delete unrelated Architect projects,
credentials or memory. Tool images may be removed separately through Docker.

Parser license notices are retained in `server/maintenance/THIRD_PARTY_NOTICES.txt`.
Terraform and provider licenses are preserved in the locally built image. Artifact
hashes establish exact bytes fetched over HTTPS; no publisher-signature verification,
vulnerability clearance or cloud deployment certification is claimed.

Maintenance-bearing Architect project exports use format 4.0.0. Older clients must be upgraded before opening them. Ordinary project formats remain unchanged. Complete migration JSON export is separate from the existing 2 MB Architect design-file bound; oversized design exports are refused without truncation. General generation receives a source-free projection, never the maintenance repositories or diagnostics.
