# Authorized immutable extraction reuse

`enterprise_extraction_cache.py` reuses the expensive decoder result, not source
permissions, document titles, source selection or model answers. A native source
still obtains current authorized bytes for every question. For Graph, the
`from_source` decoder protocol carries a live native metadata/access/version check.
It runs before lookup and around extraction, publication and return. A plain
two-argument call to a cached decoder is rejected, rather than assuming an
unreviewed adapter supplies equivalent checks.

The key binds company, complete parser artifact revision, declared MIME and original
bytes. The stored key is a contextual HMAC, not the raw document digest. Encrypted
values bind that key and contain the original digest/MIME/text for validation.
Other companies, different bytes/types and a parser upgrade cannot reuse the entry.
There is no public cache lookup endpoint or source/model-selected cache identity.

Committed building leases coordinate concurrent misses. Parsing happens outside SQL
transactions. Waiting is bounded and repeatedly checks company/job authority. An
expired builder can be replaced, but its token cannot publish over or abandon a
later builder. Failed, revoked, changed, oversized or invalid extraction is not
published. Corrupt/swapped ciphertext fails closed rather than becoming a successful
decode. Cache failure is not authority to use older private content.

Defaults are a 15-minute absolute derivative lifetime, a 150-second build lease and
a bounded 160-second follower wait. Hits do not extend retention. Worker recovery
purges expired entries, including older parser revisions, in bounded company-scoped
batches. This is logical SQL deletion, not a claim that all backup/MVCC copies are
physically erased immediately. Backup/key rotation and native retention operations
remain part of the unfinished provider/application handoff.

## Local consent is separate from a still-valid access token

A regression demonstrated that a worker could retain usable native credentials
after a different browser disconnected its source, and send parsed text to the
model. Vendor document checks alone could not enforce the local withdrawal.

Fresh `enterprise_auth` installations now give each completed consent a random
`consent_id`, also bound into credential ciphertext. `SourceWitness` combines it
with source/native subject/mapping version. Normal token refresh preserves consent;
disconnect/reconnect, mapping changes and failed reconnection invalidate the old
witness. `current_engine` brackets credential acquisition and supplies live witness
checks at context/release gates. Both queued and compatibility APIs use it.

The cache uses those same company/job/consent checks. A source disconnected or
reconnected during parsing cannot publish the derivative or supply model context.
Concurrent questions can refresh credentials without incorrectly cancelling an
already-authorized running answer. The unreleased fresh schema changed; no existing
client or prior synthetic database was migrated/adopted.

## Queue clocks

The composed native test caught an immediate job deferred with a host timestamp:
a drain-mode worker could see no due work. Immediate jobs now use the queue's
NULL/immediately-ready semantics. Retry scheduling uses PostgreSQL's clock, not
the API host clock. Native tests include a deliberately skewed SDK host clock.
This does not weaken company credential expiry checks.

## Evidence and limits

`scripts/qualify-enterprise-queries.py` now brackets exact sources and checks actual
server/dependency versions on PostgreSQL 17 and 18. It runs 89 checks per version:
21 auth, 4 session, 14 compatibility API, 19 question-store, 18 queued API/worker and
13 extraction-cache cases. Source/profile/model HTTP is explicitly scripted.

`scripts/qualify-enterprise-cache-workflow.py` uses the exact previously qualified
Linux parser image, actual Office/scanned-PDF files, encrypted SQL and real
Procrastinate jobs. Four initial questions plus outage recovery require two parses,
while every successful question rereads current bytes. Exact quotes are checked
against actual extracted text; a short numeric-only fixture quote was correctly
rejected and replaced by a complete supporting source line. This is local composition
evidence, not cloud model semantics, throughput or a whole private-project pass.

The workflow derives its parser revision from exact executable layers/runtime
configuration. Production factories must supply a reviewed full artifact revision;
an arbitrary model/caller label is not sufficient. Browser qualification separately
checks that repeat questions reread source bytes while reusing the encrypted text.

Next complete clean Linux app dependencies, native model/audit/provisioning and all
four provider exports. Before registering untrusted document processing, finish
the native per-file execution/isolation contract: the local workflow runs a fresh
restricted container per parse. A long-lived same-identity RPC parser is not proven
to contain a compromised parsing process across future files. Native jobs and secret/
result transfer need provider-specific primary-API review and qualification; no
cloud isolation claim or production/security acceptance is made here. Existing
65 HIGH parser findings remain open. Then run actual complete private projects,
remaining families and final full28/held-out evaluation.
