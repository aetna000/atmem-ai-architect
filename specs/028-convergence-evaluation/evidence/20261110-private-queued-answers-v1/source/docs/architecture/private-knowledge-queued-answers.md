# Durable private-knowledge questions

The browser now submits an encrypted question job and polls its status. Document
parsing/model work runs in a dedicated Procrastinate 3.10.0 worker, rather than
holding the browser's question POST open. The workspace requires this service;
the older synchronous `/api/ask` remains an explicit compatibility API, not the
browser path. No private export capability or complete medium case is advertised.

## One owned question, one current authority

`enterprise_queries.py` uses the same owned SQL authority/credential box as company
sessions and source consent. `enterprise_queries_schema.sql` is a separate fresh
schema, with exact source hash/version admission. It is not a migration/adoption
script. Membership/source mappings stay operator-owned. Grant helpers reject
administrative/schema-owner roles and authority-table write privileges.

Question text and answer receipts are encrypted with purpose/account/person/session/
request contexts. Answer context also binds the attempt. Request equality uses a
keyed HMAC, with a separate HKDF-derived key and identity-bound context; the database
does not retain a guessable plain question digest. Raw cookies, JWTs, OAuth tokens,
questions and answers never enter queue arguments. Queue notifications contain only
the random domain question UUID. Queue/task namespaces and worker lookup/recovery
are bound to the configured company account.

Submission and the Procrastinate outbox INSERT commit in one SQL transaction. A
client request UUID deduplicates transport retries and cannot be reused with changed
question text. Domain row locks/lease tokens independently fence duplicate workers.
Cancellation clears stored question/result ciphertext and invalidates the lease.
Old attempts cannot overwrite later results or replay earlier answer ciphertext.

Defaults are three active questions per person, three processing attempts, a
120-second renewable lease, and a 15-minute job lifetime capped by the originating
company session. Renewals check current session/membership and domain ownership.
Transient source failures schedule fresh attempts after bounded delays. Recovery
reconciles expired worker leases and queued domains whose notification failed; it
scrubs expired question/results even when no browser polls. It does not blindly
reuse private source/model data during an outage. Queue/audit identity rows remain;
long-term audit/queue cleanup, backup and key rotation still need native operations.

## Delayed answers are not authorization caches

`EnterpriseKnowledge.answer_receipt` records the actual source selections and
document identities/versions alongside the verified answer. Only coordinator code
constructs these references; model output cannot select them. Receipts remain
internal encrypted server material, not browser/API authority.

On a ready poll, `enterprise_query_service.py` obtains current delegated source
credentials. `EnterpriseKnowledge.release` searches every configured source again,
including previously empty sources, compares the selection and revalidates all
selected versions/access. It checks company/job authority before and after those
calls. A source edit/selection change clears the old result and queues a fresh
generation automatically, within the attempt limit. Source outages withhold the
saved answer. A final SQL release fence and HTTP session check reject cancellation,
expiry or sign-out during release. These are distributed checks at defined points,
not a promise to erase information previously disclosed while authorized.

## Browser behavior

The browser sends `/api/queries`, polls the resulting identity and shows the pink
brain while processing. Cancel calls the owned DELETE endpoint; local request
epochs also prevent a late response restoring content. Source disconnect stops
the local question flow. Reload resumes the most recent current-session request
from the bounded recent-request list, without submitting it again. Completed results
still require fresh source validation. The list is three current recent requests,
not a durable full-conversation history or an extraction/authorization cache.

Current screenshots/checks cover desktop/mobile, active brain/Cancel layout, reload
without duplicate jobs, cancellation during model work, and sign-out during a late
streamed result. Private text remains rendered with textContent, not source HTML.

## Validation and remaining scope

- 17 real restricted SQL/crypto/outbox tests on each of PostgreSQL 17 and 18.
- 10 actual ASGI/session/source/queue-worker tests on each version, including real
  Procrastinate dispatch/retry, heartbeat renewal and cancellation during release.
- 45 enterprise contract/policy tests; 11 Chromium checks with loopback TLS/SQL.
- Prior authentication/session/API and actual restricted Linux document composition
  checks rerun; vendor source/profile and model responses are explicit fixtures.

Use `.local/durable-runtime/bin/python -I` with
`tests/runtime/enterprise_queries_postgres.py` and
`tests/runtime/enterprise_queries_http_postgres.py` against the owned fixture. The
browser qualifier is `node scripts/enterprise-browser-check.mjs .local/fresh-run`.
The tests create fresh synthetic databases/roles; they do not migrate a client DB.
For one exact-source, actual-server-version-checked receipt covering both SQL
versions, run `python3 scripts/qualify-enterprise-queries.py --out .local/fresh-sql-run`.

This removes the long processing POST and preserves authorization through delayed
release. It does not prove 3,000 questions/day, 10,000-document relevance, a cloud
source account, a cloud model or a deployable full private-knowledge package.
Next add parser-versioned encrypted extraction caching behind live source reads,
qualify clean Linux app dependencies, native models/audit/provisioning and all four
provider footprints/Spec Kit exports, then run actual complete project cases and
the remaining full28/held-out evaluation. Existing parser/security findings remain
open; passing these tests is not security or production acceptance.
