# Composed invoice workflow: local evidence, cloud integration unfinished

The generator now has reusable source building blocks for immutable private invoice
storage, PDF text/OCR, independently validated model suggestions, authenticated
upload/review endpoints and durable approval/delivery. This increment does not
register a complete cloud application or count a medium benchmark project as passed.

## Observed execution

- 54 native PostgreSQL/queue/role/crash/TLS/deadline checks, including immutable
  result revision history and account/workflow-scoped listing. The history cannot
  be rewritten/deleted by runtime database roles.
- 10 exact Linux parser/decoder tests, plus CLI checks on text, scanned, mixed and
  encrypted invoices. The qualified image is
  `sha256:fa27c11f9ca0ebc5f3c4ac1db4d552cc75a9c81a2f0fec6bb61e2841e6f0dbb6`.
  Execution is nonroot, read-only, network-disabled, without capabilities, with
  512 MiB memory, one CPU, 32 PIDs and a 64 MiB writable tmpfs.
- 7 SDK/scripted native storage contract checks across AWS/Azure/Google/IBM:
  conditional creation, pinned versions, ownership, digest verification and denial.
  These do not establish actual destination IAM, versioning or regional deployment.
- 9 ASGI API checks against actual PostgreSQL with separate restricted producer and
  worker roles. Identity/object storage are explicit fixtures. Twenty repeated
  uploads create one invoice and one queue job. Ordinary staff cannot approve;
  stale edits, cross-account cursors, oversized uploads and late access revocation
  are denied. Earlier extraction/reviewer revisions remain readable after edits.
- Five actual PDF/OCR -> signed-in local model -> independent decoder probes pass
  for text, scan, mixed, competing subtotal/total and injected-instruction invoices.
  This is a small authored English corpus, not production/cloud-model accuracy.
- The composed workflow executes two jobs concurrently: actual ASGI upload, native
  restricted-role queue workers, the locked Linux parser, two local model calls,
  independent fields/evidence checks, server approval and actual loopback TLS
  delivery. Duplicate uploads/approvals produce one record/effect per operation.

The composed probe uses a test-owned Docker socket to invoke the parser. No Docker
socket or container-launch authority is proposed for an exported application. A
matching production parser/service isolation composition remains to be implemented.
Identity and object persistence in that probe are fixtures; separate storage tests
exercise native SDK/request contracts. No live IdP/model/storage/account, cloud
plan, deployment, 90-day retention/restore or accounting vendor guarantee is proved.

## Faults repaired at the source

The initial native OCR dependency closure included libxml2 with critical-rated
CVE-2026-6653. That candidate is retained and not promoted. The reduced build pins
upstream Tesseract 5.5.3 at `db0ec62f81b0737fbbe184d8fea40af5738f8eef`, disables
archive/URL-fetch features at compilation and omits their libraries from the final
runtime. A native dependency probe verifies both package absence and actual dynamic
links. Scanner metadata is retained. The compiled OCR executable has its own source
revision, SHA256, version output and Apache-2.0 license; it is not a Debian package.

The final scan reports **0 critical, 65 high, 129 medium, 198 low and 2 unknown**;
none of the high findings has a reported fix. This is not a clean security pass.
The scanner's OS-package coverage is not a complete assessment of the custom binary
or all runtime behavior. Keep the remaining findings open before production use.
All raw original/final reports are retained under `security/`.

The new build exposed a language-data location mismatch; the parser now uses an
explicit reviewed installed data directory. The isolated CLI exposed an import-path
bug; its explicit owned module path is fixed and covered by real CLI execution.
Invoice decoding rejects forged page/quote/value evidence, action/role fields,
unknown fields without uncertainty, ambiguous numeric dates, broken decimal grouping
and positive-value substitutions for negative refunds. Every result requires review.

Primary Azure REST review also exposed a missing required HTTP date in the shared
catalog adapter. The generator source, embedded source and transport regression now
include that header. Prior exact FAQ artifacts remain unchanged historical evidence.

## Engineering knowledge reaches the engine

The portable queue/approval lesson is published through the real pinned AtMem SDK,
with explicit provider applicability and a hash-pinned local evidence receipt.
Regression testing discovered that AtMem 2.3.10 adds a terminal sentence period to
interpreted facts. Previously, JSON-only parsing silently excluded those practices
from model context. The adapter now accepts exactly that known normalization, then
compares the entire record/key to the reviewed catalogue. Trailing instructions,
tampering, expiry and unsupported providers remain excluded. A native AtMem recall
test verifies that the actual durable practice reaches context on retrieval.

## Reproduce

The durable fixture/runtime setup is documented in the preceding durable-core
increment. This parser build additionally requires a local Docker daemon with
BuildKit and Linux/amd64 support. Source/dependency downloads are public, pinned and
local; no account authentication or image publication is performed.

```sh
python3.13 -I scripts/qualify-invoice-parser.py --docker-host unix:///absolute/local/docker.sock --out .local/parser-check
.venv/bin/python -I scripts/evaluate-invoice-semantics.py --live --out .local/invoice-semantics-check
.local/durable-runtime/bin/python -I scripts/evaluate-invoice-workflow.py --live --out .local/invoice-workflow-check --parser-receipt .local/parser-check/receipt.json --docker-host unix:///absolute/local/docker.sock
```

The standalone semantics probe requires installed native Poppler/Tesseract and a
signed-in local Codex CLI. The composed probe uses the qualified container. Local
API test tooling currently uses the existing pinned Azure/common SDK directory;
complete generated worker/API dependency closures are pending provider integration.

Next: complete the application/UI bootstrap, native login/object/database/credential
and parser isolation resources on all four providers; implement retention, recovery
and reconciliation operations; qualify fresh exact exports and rerun complete client
briefs. Native enterprise sources, support actions, tenant credits/memory, full 28-case
acceptance and held-out validation remain unfinished. No cloud operation is authorized.
