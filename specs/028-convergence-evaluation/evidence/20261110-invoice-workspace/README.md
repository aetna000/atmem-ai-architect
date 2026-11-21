# Invoice workspace, native login bindings and concurrent bootstrap

Observed local evidence:

- **31 API/decoder/storage/identity checks**: api/receipt.json. Actual JWT signature
  verification for all four providers feeds the native API factory, then independent
  live PostgreSQL membership and approval checks. Cloud signing keys, object stores
  and destinations are explicit fixtures. No native cloud authentication is claimed.
- **12 browser checks**: browser/validation.json. Real local HTTP, restricted SQL
  roles and queue worker exercise upload, processing, corrections, conflicting edits,
  approval, protected original download, revision history, reload and revocation.
  Background updates preserve edits. Source text renders without executing markup.
  Synthetic extraction/storage/delivery do not establish OCR or model quality.
- **5 PKCE browser checks**: pkce-browser/validation.json. Actual browser state,
  challenge/verifier binding, in-memory bearer use, expiration and suppression of
  late private responses. Authority responses are explicitly intercepted fixtures.
- **82 workflow checks on each of PostgreSQL 17.11 and 18.6**, with the same source:
  grant-serialization-postgres-17/receipt.json and the corresponding postgres-18 file.

The native API bootstrap binds database credentials, private object adapters, login
verification, browser and durable producer. It never reads model configuration or
outbound credentials. API/worker/migration identities remain separate. All four
provider login bindings retain their own issuer/audience/client/tenant semantics;
token roles cannot replace the application's database membership.

Retained faults: running browser suites concurrently exposed a PostgreSQL shared-ACL
catalog collision during grants for separate roles. A transaction-scoped database
advisory lock now serializes owned grant admission; a four-way concurrency regression
passes, as do both browser suites running together. Two aggregate API harness runs
failed first for an absent separately isolated boto3 dependency and then for runpy
leaving unittest's argv incorrect. Both failed receipts/logs are retained; the fixed
runner explicitly supplies the pinned SDK path and its final 31 checks pass. No test
was skipped or converted to success. An earlier history assertion raced the HTTP
response; the browser test now waits for the retained revisions to arrive.

Exact sources, scripts and acceptance tests are in qualification/source. Screenshots
were inspected at desktop and mobile widths. The fixed browser uses pink #F3A2B4 and
brain activity; no private tokens are persisted. Proxy requests use the documented
AJAX header and handle 401 without following login redirects. Public configuration
cannot introduce an arbitrary token authority, CSP directive or client secret.

This is **not yet a complete generated cloud project**. Worker bootstrap, native
parser transport/isolation, complete four-cloud resources, retention and restore
still need composition and qualification before registering this capability. No
medium benchmark case or final 28-case acceptance is counted here. No cloud account
operations, publication, account plan or deployment occurred.
