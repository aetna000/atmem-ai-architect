# Isolated PostgreSQL and SDK validation checkpoint

The generic artifact checker can now supply a private PostgreSQL17 database to
Python tests. This closes an environment prerequisite exposed by the native
equipment transfer without editing its exported application or clearing its failed
checks. This is a reusable validation capability, not a domain recipe or release.

## Contract and applicability

An operator registers an immutable cached image, platform, observed runtime receipt
and `postgresql-local-v1` isolation profile. The image-owned command is
`/usr/local/bin/python3 -I /opt/atmem/sql_validation.py -m unittest discover -v`.
It initializes a fresh database after the existing artifact bootstrap drops to
UID/GID65532. PostgreSQL uses a private Unix socket, SCRAM password authentication,
no TCP listener, private0700 state and no host database or credential mount.
Tests receive `ATMEM_TEST_POSTGRES_DSN`, standard PG connection variables and
explicit private data/tool paths. They must create and exercise their application
roles; the setup administrator is not production authorization evidence.

The same container retains network-none, read-only image/source, no effective
capabilities, no-new-privileges and bounded CPU/process/output/deadline resources.
The SQL profile reserves512MiB memory and192MiB temporary storage. Normal exit stops
the server; controller timeout/cancellation removes the entire owned container.
Missing startup prerequisites produce `sql_fixture_unavailable`; they do not request
speculative application repair. Existing digest/project/policy/worker check binding
and denial of caller-provided credentials remain in force. Wrapped unittest counts
and skipped/zero-test classification reach the public catalogue and reports.

Fresh handoffs describe the neutral fixture contract. Existing workspace pins and
running sessions are unchanged. Registration is an operator action; the model and
browser cannot supply an image or executable. The standalone catalogue smoke uses
a disposable backend store, without restarting any preview or launching inference.
The separate synthetic preview's prepared registration is not claimed as activated.

## Qualified inputs and results

- `image-v4.json`: offline operator-built Linux ARM64 image
  `sha256:d2f7bcb589a14c4dac1ed2bb4d839eb97906ea4202e3b9a48862be04a0bdc948`.
  It combines pinned public Debian PostgreSQL17.11 binaries, Python3.13.18 and
  all38 exact AWS test-lock wheels. The builder can accept the other provider
  locks/platforms with matching cached inputs; those variants were not qualified.
  PostgreSQL dependencies stay in a private library path, with package inventory
  and copyright notices retained. JIT is explicitly disabled; LLVM bitcode is absent.
- `runtime-observation-v2.json`: actual isolated initialization, authenticated SQL
  query and shutdown with empty source. Reports PostgreSQL17.11 and installed SDK
  versions rather than assuming them from image names.
- `qualification-v2.receipt.json`: five actual editorial/inventory transaction,
  role/authentication, read-only identity/capability and network-denial tests pass.
  A second job confirms fresh state. Identical tests without the fixture fail;
  skipped tests stay incomplete, zero tests fail and a timed-out job fails with
  confirmed cleanup. All six cases confirm removal without work replay.
- `registered-catalog-v1.json`: actual backend registration accepts the pinned
  observation, advertises availability and reports `unittest` with PostgreSQL17.11.
- `source-binding-v1.json`: current implementation/qualifier hashes, exact driver
  equality with the image and hashes of detailed bulk qualification reports.
- `javascript-v1.log`:553 passed, zero skips. `server-v1.log`:445 passed.
  `build-v1.log`:production build passed with the existing bundle-size warning.
  `focused-v1.log`:45 focused validator/receipt/finalization checks passed.

The qualification schemas are synthetic editorial and inventory examples. They are
independent of the equipment project and production selection logic. The original
28 and held-out requirements are not inspected or used as dispatch keys.

## Reproduction and retained failures

Bulk contexts, wheels, public base descriptors, image build logs and detailed
per-case results remain on MEM0 at
`.local/external-artifacts/isolated-sql-validation/v1`. Existing source archives
are preserved. Run these from the repository with a local qualification Docker
endpoint and both pinned public base platforms already cached:

```sh
.venv/bin/python scripts/engine-evaluation/prepare-sql-validation-image.py \
  --output .local/external-artifacts/isolated-sql-validation/v1/build-next \
  --postgres-image docker.io/library/postgres@sha256:f998bd5067cabb2b023800c6fbf04f24bd22fbb7f8430cfd8c8503a6c3834777 \
  --python-image docker.io/library/python@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 \
  --wheels .local/external-artifacts/native-runtime-access/sdk-mirror-arm64-v1/wheels \
  --provider aws --platform linux/arm64 \
  --endpoint unix:///Users/javadtaghia/.colima/architect-qualification/docker.sock
.venv/bin/python scripts/engine-evaluation/check-sql-validation.py \
  --image sha256:d2f7bcb589a14c4dac1ed2bb4d839eb97906ea4202e3b9a48862be04a0bdc948 \
  --output .local/external-artifacts/isolated-sql-validation/v1/qualification-next \
  --endpoint unix:///Users/javadtaghia/.colima/architect-qualification/docker.sock
```

Use fresh output directories. The image builder never consumes an application
Dockerfile, pulls missing bases or resolves newer dependencies. Runtime observation
uses `observe-runtime.py` with the operator SQL registration and Python package
arguments; its receipt binds the exact image/profile/executable/worker policy.

Retain the failed v1 runtime observation: upstream PostgreSQL sample configuration
was a symlink outside the copied tree. The operator builder now dereferences trusted
shared data during image construction; no application or isolation policy changed.
The initial qualification expected EACCES for an image write; the actual read-only
filesystem returned EROFS. The corrected oracle accepts either denial and still
requires the write to fail. Earlier diagnostics and final logs are preserved here;
they are not counted as passing runs.

## Limits and next action

This qualifies the fixture and shared checker, not arbitrary test semantics,
security acceptance, managed PostgreSQL or a complete generated client system.
The caller's tests can intentionally log their own setup credentials; the driver
itself prints neither passwords nor private server logs. The instance is disposable
and all check code shares one untrusted nonroot identity. It provides no additional
isolation between tests within a job and no application backup guarantee.

Activate the reviewed registration only in the separate idle synthetic preview,
then have the native engineer adopt the neutral fixture in its own generated tests
without weakening assertions. Inspect the complete report. Independently execute
the actual application image/SQL/TLS journey and equivalent provider transfers before
freezing runnable alpha.5. Four increments offered,1/28 original locally qualified,
owner acceptance0 and measured quality unknown remain unchanged. No cloud account,
deployment, owner preview, UI or AtFlow CSS change occurred.
