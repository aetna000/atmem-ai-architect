# Portable local invoice acceptance

On Linux/amd64, create a separate Python 3.13 virtual environment from this application
directory for this provider. Install test-requirements.lock using pip --require-hashes
--only-binary=:all:. Do not mix IBM/AWS SDK environments or substitute another
provider's dependency resolution. Install OpenSSL with req -addext support for the
synthetic loopback TLS tests. No cloud credential is needed.

The wheel hashes target Linux/amd64. On another host, use the emitted Linux test
image: docker build --platform linux/amd64 -f Dockerfile.tests -t invoice-local-tests .
It is a separate developer test image, not the delivered API/worker image. Pass a
private owned loopback fixture configuration and a writable private output directory
to tests/run.py; do not copy credentials into its build context. Host networking
must be explicitly enabled/supported by the local Docker engine for loopback SQL.
No cloud/database/identity credential from the host is implicitly forwarded.

With an existing local Unix Docker socket, explicitly create the synthetic fixture:

    python tests/start-local-fixture.py --docker-host unix:///ABSOLUTE_LOCAL_DOCKER_SOCKET --major 18
    python tests/run.py --fixture .local/durable-postgres/fixture-pg18.json --out .local/test-run-1

Use the pinned native PostgreSQL image and retain its digest. The fixture binds only
127.0.0.1, gets a directory-derived owned name, uses private generated credentials
and validates its schema marker. Never point these tests at a client/cloud database.
The tests create synthetic accounts/roles/records; keep the fixture disposable and
run suites serially. No container/database adoption, dump, migration or cloud access
is implicit. Missing Docker/socket/image/prerequisite is a failed prerequisite,
not a skipped pass. Review any authorized image download and local resource costs.

The suite covers extraction validation, version-bound storage protocols, signed
staff/API admission and SQL memberships, upload/review/approval/history, local TLS
parser/action protocols, worker behavior, guarded operator initialization,
retention/monitoring and browser safety. AWS includes native SDK shape tests; other
providers include scripted HTTP contracts without pulling in AWS's SDK. Protocol
fixtures are not cloud IAM or actual model quality. Real PDF/OCR image acceptance,
native model examples, destination accounting compatibility, restore and actual
private-network/scheduled-alert behavior require their separate acceptance tasks.
Receipts distinguish these boundaries. Keep private .local credentials/logs/state
out of source control; do not send diagnostic logs containing secrets to a model.
