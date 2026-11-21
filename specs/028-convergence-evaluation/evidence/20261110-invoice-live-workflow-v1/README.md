# Composed workflow using actual live-export application sources

The workflow probe now supports an exact local application source and passing native
artifact receipt. It validates all original application file digests before importing
code. It imports the application and parser modules from that qualified output,
checks shared parser image source/lock equivalence and records the native receipt
hash. Original handoffs remain untouched. The preceding native/portable receipts
are in `../20261110-invoice-live-native-v3/`.

All four exports passed 15 composed checks each: actual mixed/injected PDF upload,
deduplication, locked network-disabled Linux OCR, actual signed-in local Codex calls,
independent field decoding, restricted PostgreSQL queue roles, no external action
before review, denied ordinary-staff approval, reviewer approval and repeated approval
without a second outbound send. Two actual model/parser operations per provider.
Source bytes remained unchanged. Emitted shared parser sources and requirements
match the earlier locked image receipt; using that shared image does not mean an IBM
cloud deployment was used to test the other providers.

Identity/object persistence and accounting use explicit synthetic/local fixtures;
TLS destination and queue/database operations are real loopback operations. This
is not native cloud identity/model/storage/database/hosting or a deployed system.
Recovery/security reconciliation and other medium/hard families, final 28-case and
held-out variants remain unfinished. Zero complete medium cases are promoted here.
Two admission regressions reject missing/non-local pairs, failed receipts and altered
Python before application import. The full JavaScript suite passes 345 tests.
