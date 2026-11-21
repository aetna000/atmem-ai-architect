# Restored extraction recovery correction

Continues ../20261110-invoice-worker-delivery without rewriting that checkpoint.
The older helper did not fence restored extraction leases or clear their stale
native doing jobs. The extended operator regression fails against its retained
source. Current code resets extraction to pending, clears/fences old leases and
queue rows, preserves attempt limits and audit, and rebuilds pending notifications
through the normal worker only after expiry cleanup. External deliveries remain
unknown, never silently resent. Authorization that workloads are stopped remains
an explicit operator assertion, not a software proof of cloud state.

Current qualification: 55 API/operator/identity/parser/worker checks; 10 actual
local pg_dump/pg_restore checks; 85 core checks on each PostgreSQL 17.11 and18.6;
six AWS native provider-mock Terraform runs; four exact newly built delivery images
with native startup and five restricted local queue cases each; and four actual
isolated operator CLI entrypoints. JavaScript299 tests and build pass. The previous
checkpoint retains exact unchanged browser12/PKCE5, real-OCR/local-model14 and
parser image evidence. Sources/receipts are immutable snapshots, not an assertion
that a historical whole tree and the current working tree are identical.

All new application image scans have zero critical and47 unfixed high findings.
Parser65 high findings remain open in the related checkpoint. No clean security,
cloud plan, native managed backup, external vendor, deployment, complete invoice
project or full28-case acceptance is claimed. Native operator scheduling/bootstrap,
other cloud adapters and complete exporter/Spec Kit admission remain unfinished.
No private credentials, nonce configurations or database dumps are included.
