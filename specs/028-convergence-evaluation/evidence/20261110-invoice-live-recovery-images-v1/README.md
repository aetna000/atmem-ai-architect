# Exact live invoice recovery and native-image checks

All four original live application artifacts built Linux production images. Their
exact source bytes and pinned dependencies passed native API startup, signed-out
API denial, five real restricted PostgreSQL queue cases per image and native-plan
operator command/configuration checks (AWS 9, Azure/Google/IBM 12 each). Operators
use real loopback SQL; cloud credential transports/mapping remain explicit fixtures.

The logical restore probe now admits paired original application/native receipts
before imports, validates all source hashes and checks they remain unchanged.
All four exports passed ten checks each with actual local pg_dump/pg_restore into
fresh synthetic databases, uncertain-delivery quarantine, stale-job fencing,
retention purge and independently supplied synthetic receipt reconciliation.
Private database dump payloads remain local and are deliberately excluded here.
This is not managed backup/PITR, object-store recovery or an RPO/RTO guarantee.
Two admission regressions and all 347 JavaScript tests pass.

Trivy 0.76.2 scanned each exact production image against the preserved cached
vulnerability metadata with no database update. Each scan reports 47 HIGH package
findings, zero CRITICAL and no reported fixed versions in that metadata. All remain
OPEN; non-root execution or local tests do not dismiss vulnerabilities. The scan
process exit status is not security acceptance. No production readiness promotion.

No cloud account, native cloud authorization/service networking, managed backup,
alert routing, account plan, apply, image publication or deployment was performed.
The other medium/hard families, final full28 and held-out evaluation remain open.
