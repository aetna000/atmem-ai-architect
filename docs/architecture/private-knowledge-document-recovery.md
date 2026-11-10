# Durable private-document cleanup

The Google document controller now records cleanup intent in PostgreSQL before
creating an input object. This is one part of the private-assistant implementation;
it does not qualify a complete export or any destination cloud account.

`enterprise_document_jobs.py` owns the metadata-only ledger. Each record binds an
account, immutable target fingerprint and unpredictable request identity to an
execution phase, deadline and fenced cleanup lease. The ledger stores no document
bytes, extracted text, question, title, user identifier, credential, endpoint or
upstream error body. The fingerprint covers project, region and bucket; image or
transfer-identity upgrades do not prevent cleanup of an older job at that target.

The fresh operator bootstrap installs the exact hashed schema and grants its
runtime privileges only to the worker. The API cannot read or modify job metadata.
Startup checks use catalog object identifiers to inspect table privileges without
requiring API access to the private schema. There is no automatic adoption or
migration of an existing database.

## Recovery behavior

The controller commits an intent before its first remote mutation, advances only
through acknowledged phases, checks its live lease around source and result work,
and withholds a result after expiry or takeover. Foreground cleanup claims a new
token and waits for owned job deletion before deleting its two exact object names.
It never lists a bucket or accepts arbitrary cleanup URLs from a database record.

An independent worker loop claims expired execution or cleanup leases with
`FOR UPDATE SKIP LOCKED`. Database transactions finish before remote calls.
Cleanup failures remain pending with bounded retry delay. Concurrent reconcilers
cannot claim the same live lease; an expired token cannot retire a newer claim.
Company sign-in changes fence new processing but do not erase cleanup obligations.

A successful, acknowledged job can retire its record after successful cleanup.
An incomplete operation may have committed remotely after a lost acknowledgement.
Its tombstone therefore schedules additional deletion probes at 60, 300 and 1,800
seconds, with a final probe at the 24-hour settlement boundary. Failed cleanup is
retried rather than silently abandoned. These are scheduling bounds, **not a hard
maximum document-retention guarantee**. Provider effects after that boundary and
native cancellation semantics still require destination evidence.

The document loop is separate from query lease/cache recovery, so a slow remote
delete does not block that maintenance. Cancelling an asyncio thread task does not
stop an already-running native call; the persistent cleanup lease allows a later
worker to recover after process termination.

## Qualification and remaining scope

SQL tests use ordinary nonadministrative worker/API roles on owned PostgreSQL
fixtures. The crash test actually exits a child process before acknowledgement or
`finally`; a restarted adapter removes its synthetic remote object, handles a
simulated late commit and eventually retires metadata. Google HTTP operations are
explicit fixtures, so this does not prove native VM termination or object deletion.

Before a complete private export is qualified, finish the generated worker/artifact
wiring, other three native launchers, operator monitoring and recovery procedures,
strict retention/backups and destination-specific verification. Moving project,
region or bucket requires draining the old target with its original configuration;
a new target must not adopt another namespace. Worker downtime delays retries.
The bucket's asynchronous age-based fallback is not a substitute for recovery or a
retention SLA. Existing database migration, security acceptance, whole-project
qualification and the final 28-project/held-out evaluation remain unfinished.
