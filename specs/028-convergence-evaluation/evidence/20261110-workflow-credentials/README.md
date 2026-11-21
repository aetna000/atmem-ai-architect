# Fresh database credentials and safe native role bootstrap

The same exact workflow source passes **80 local checks on PostgreSQL 17.11 and
80 on PostgreSQL 18.6**, with hash-pinned Procrastinate 3.10.0 and psycopg pool
3.3.3. See postgres-17/receipt.json and postgres-18/receipt.json and their full logs.
These are two database-version runs of the same suite, not 160 independent features.
Exact checked sources are retained under qualification/source.

Implemented and exercised:

- Fresh credentials for synchronous business transactions and asynchronous queue
  pool connections. Real local password rotation and termination of only fresh
  fixture-role sessions verify reconnect behavior.
- AWS SDK SigV4 database token construction, Azure database audience/managed identity
  refresh, Google metadata protocol and managed Cloud SQL socket binding, and IBM
  separate SQL-password/instance-CA configuration. SDK/protocol fixtures are explicit;
  none establishes managed-cloud authentication or IAM correctness in an account.
- Native authentication-role admission without inherited business privileges.
  Effective PUBLIC, column-level, indirect-role and ownership grants cannot silently
  broaden append-only history or runtime membership authority.
- Operator-only, ownership-marked API/worker role bootstrap. Refuses adoption or
  repointing of unrelated logins. Azure's authoritative service/OID/tenant and
  non-admin mapping is scripted around real local PostgreSQL DDL; the vendor
  function is not present on local PostgreSQL. GCP requires a separately created
  native IAM user. That declaration is a bootstrap contract, not cloud proof.
- IBM-style SQL passwords use client-side SCRAM verifiers, with a real native login
  check. Repeat bootstrap preserves an existing password. Runtime IAM tokens are
  never passed off as IBM SQL passwords.
- Connection failures before domain lease acquisition retry safely. Notification
  reconciliation requeues only pending/approved work with no live native job;
  uncertain external outcomes never become an automatic new send.

Retained faults: the original PG18 run passed 66/69 tests because crash-test children
did not inherit the owned PG18 fixture selector. They queried the PG17 fixture. The
selector is now explicitly passed in the child's minimal environment. A separate
privilege-query failure called a sequence privilege function on a non-sequence after
SQL predicate reordering; CASE now selects the privilege function by relation kind.
Original failed output remains under retained-faults; neither is erased or counted
as a pass. The fresh two-version runs cover both repairs.

No cloud accounts, managed databases, registry, account plan or deployed system were
accessed. Fixture credentials and private connection configs are excluded. This is
still an unregistered workflow component: complete invoice provider resources,
parser isolation, native login/storage/model composition, retention/restore,
remaining medium/hard projects and the final 28-case evaluation remain unfinished.

Reproduce with scripts/start-durable-fixture.py --major 17 (or 18) and the isolated
durable runtime. scripts/qualify-durable-runtime.py --out requires a fresh .local
directory. PG18 uses ATMEM_WORKFLOW_TEST_CONFIG pointing to the owned private
.local/durable-postgres/fixture-pg18.json. The nonce guard rejects unrelated databases.
Do not substitute any destination/client database for the local fixture.
