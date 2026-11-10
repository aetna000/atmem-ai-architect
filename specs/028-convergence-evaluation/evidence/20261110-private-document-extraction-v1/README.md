# Private document-extraction checkpoint

Original private-knowledge and all 28 project requirements remain unchanged.
No private export capability or complete medium case is promoted here.

Implemented the pinned Tika 3.3.3/Java bridge, byte-only parser workload, fixed
HTTPS application transport and reproducible restricted Linux qualification.
The existing invoice PDF/OCR protocol is unchanged.

- **16 actual Linux tests**: Office/text/PDF extraction, admission/RPC, byte-bound
  MIME/schema/size checks and composed retrieval/citations.
- **39 enterprise contracts/policies**, including five parser-client fault tests.
- Existing browser bundle verification passes; no browser behavior changed.
- Both owned PostgreSQL 17.11/18.6 fixtures passed guarded reads after expansion
  of the dedicated qualification disk; no database migration/deletion occurred.

`native-final/receipt.json` identifies exact image/source hashes and success.
Checks include Word headers/tables/footer, multiple spreadsheet sheets, slide
notes, HTML script exclusion, RTF/Unicode text, native/scanned/mixed PDFs,
revocation during parsing, edits during model work and fresh outage recovery.
Source-account HTTP/model output are scripted. Parser/JVM/OCR and source/retrieval
code are actual. RPC is loopback HTTP inside the isolated container, not cloud TLS.

Retain earlier failures: full test disk, non-root jar permissions, OCR language
path, omitted test schema and source mutation invalidating otherwise passing
tests. Final producer uses unique image tags to preserve observed manifests.

**Security is unaccepted.** Exact image scan retains 65 HIGH, zero CRITICAL and
zero HIGH/CRITICAL fixed versions in cached metadata. Automatic Java image
coverage was absent. Separately scanning 89 exact jar-embedded Maven descriptors
found zero known findings; that is not complete shaded-bytecode/Java-runtime
coverage. No findings were waived. See `review/security-summary-v1.json` and scans.

Next: asynchronous extraction/encrypted immutable regional cache with live
authorization and retention/recovery; clean Linux app/model/audit/provisioning;
all4 native exports/live projects; remaining families and final full28/held-out.
Synchronous latency, format semantics, security and cloud boundaries remain open.

`manifest.json` records source/fixture/evidence bytes. Exact dependency archives
remain referenced by public URL/hash. No company content, secrets, private fixture
configuration, SQL dumps or private signing keys are included.
