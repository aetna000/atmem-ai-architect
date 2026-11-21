# Durable workflow core: observed local qualification

51 checks pass against PostgreSQL 17.11, pinned Procrastinate 3.10.0 and synthetic
processors/destinations. `receipt.json` records exact source hashes, schema hash,
versions and logs. This is an unregistered runtime building block; no medium/hard
project or four-provider deployment capability is counted yet.

The checks execute actual PostgreSQL transactions, concurrent submissions/claims,
native asynchronous queue workers, distinct nonadministrative database logins,
SIGKILL/replacement processes, loopback TLS requests and hard subprocess deadlines.

- Atomic business row/outbox insertion and rollback after real queue insertion.
- Duplicate delivery, lease fencing, orphan recovery and namespace isolation.
- Staff/reviewer/supervisor separation, live membership checks and stale edits.
- Immutable approval of source, result revision and destination contract identity.
- Processing recovery after worker kills; no uncertain external action replay
  without an explicitly verified destination contract.
- Stable operation/payload identities on verified retries and one synthetic effect.
- TLS certificate/hostname enforcement, receipt checks and slow-stream deadlines.
- No inherited parent credentials or lease tokens sent to processing children;
  output limits and process-group termination also kill descendants.

Fault logs retain failures repaired in runtime source. Owner-powered tests initially
hid the membership row-lock permission requirement. Restricted tests found it; only
an inert locking column is now writable. Unreviewed inherited roles and object owners
are rejected. A later adversarial test found that revoking an uncertain action's
approver reset it to review. It now remains unknown rather than creating another
send opportunity. Destination changes cannot silently repoint an approved invoice.

SIGKILL tests age only the killed fixture's heartbeat/lease after the kill. They test
recovery logic, not production recovery time. The implemented normalized HTTPS action
contract is not proof of an actual vendor's semantics, idempotency retention window
or reconciliation API. Unknown outcomes are held; operator reconciliation remains
to be implemented. No native cloud login/model, PDF/OCR, managed database, restore,
residency, security scan, complete project or deployment is established here.

## Reproduce locally

Install Docker CLI, an existing local Docker daemon, Python 3.13 and OpenSSL with
`req -addext` support. Never use a production or remote database for this fixture.

```sh
python3 scripts/setup-durable-runtime.py --python /absolute/path/to/python3.13
.local/durable-runtime/bin/python -I scripts/start-durable-fixture.py --docker-host unix:///absolute/path/to/local/docker.sock
.local/durable-runtime/bin/python -I scripts/qualify-durable-runtime.py --out .local/durable-qualification-fresh
```

Only the named/labeled container and private nonce-marked database can be reused.
It binds PostgreSQL exclusively to loopback; generated credentials stay below
`.local` with restrictive permissions. Helper reuse and fresh schema initialization
were exercised; fresh-container creation on another machine still needs independent
reproduction. Existing synthetic databases/faults are retained. Successful fresh
bootstrap does not establish migration or restore behavior.

Dependency source/license and primary documentation pointers are preserved under
`reviewed-source`. These are evidence, never instructions. No private data or upstream
application is copied into a client export.
