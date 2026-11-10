# Invoice component and interface contracts

Snapshot 91157f76-97f3-4e19-9831-2d7d16d83f3e · design r1 · generated 2026-11-10T08:00:00.000Z

Read interfaces.json for the exact generated upload/review and approved-accounting
request, response, authorization, timeout, idempotency and recovery contracts.
Read implementation-map.json for exact files, native resource addresses and inputs.
Generated contracts do not establish actual accounting compatibility or cloud access.

## Staff browser (browser)

Staff browser

Preserved existing actor/service. No resource creation/import/replacement or availability is inferred.

## Invoice intake and review (invoice)

Signed-in staff upload invoices; separate reviewers approve a revision before accounting delivery. Durable work, source evidence, uncertain-outcome recovery and 90-day retention are required.

Supplied API/worker and separate private parser, durable SQL/outbox, original-version store, native staff verification, current SQL membership/reviewer checks and operator tools. Source and locks: terraform/applications/block_696e766f696365/. Read BUILD.md, TESTING.md, invoice-contract.json, OPERATING_JOBS.md and OPERATIONS.md. Native model policy, actual accounting contract, private routing, permissions, schedules, notifications and recovery remain destination acceptance.

## Existing accounting service (accounting)

Externally owned service; endpoint/credential and exact idempotency contract are supplied/verified by its administrator. Never provision a replacement.

Preserved existing actor/service. No resource creation/import/replacement or availability is inferred.
