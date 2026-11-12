# Private company-document extraction

This implements the document boundary for the unchanged private-knowledge benchmark,
not a new public generator capability or a completed medium project. The native
source adapter still authorizes the caller, downloads current bytes and rechecks the
source version/access after extraction. The retrieval coordinator rechecks source
and company access before model context and before releasing an answer/citation.

## Composition

`enterprise_document.py` takes bytes plus source-declared MIME, never a URL or
document-selected command. PDFs use the existing native text plus English OCR
extractor without changing the invoice protocol. Other admitted formats use
`EnterpriseDocument.java`, a fixed Apache Tika 3.3.3 bridge in a separate JVM. Apache
identifies 3.3.3 as its supported maintenance release. The exact jar checksum,
verified release-signature fingerprint and Java build image are recorded in
`src/runtime/enterprise-document-lock.json`.

The bridge detects type from bytes before admitting document parsers. It includes
headers/footers, tables, slide notes and recursively parsed embedded content; it
does not extract macros or deleted Office content. Recursive metadata is inspected
for caught extraction failures and resource/write limits. No partial text is
returned after those failures. Office image OCR uses the installed English language
data explicitly; a missing OCR dependency is a failure, not a successful text-only
parse. This is extraction rather than visual/layout equivalence. Other languages,
equations, complicated diagrams and vendor-specific format semantics still require
additional acceptance fixtures before claiming coverage.

The checked fixture set covers DOCX headers/table/footer/Unicode, multiple XLSX
sheets, PPTX speaker notes, HTML text with script exclusion, RTF, UTF-8 plain text,
native/scanned/mixed PDF, encrypted/malformed input, a denied generic archive,
declared/detected MIME mismatch and oversized output. Legacy Office and OpenDocument
types are admitted by Tika but are **not yet independently qualified by this corpus**.
This must not be advertised as complete company-document format coverage.

## Isolation and contract

`enterprise-document.Dockerfile` layers the exact qualified PDF/OCR image with the
checksum-pinned Tika jar, compiled bridge and stripped Java runtime. Build the
supplied PDF Dockerfile and qualify its image first, then supply that local image as
`PDF_PARSER_IMAGE`. The qualifier verifies current PDF module hashes before use; the
argument alone is not an attestation. Jar permissions explicitly allow the final
non-root user to read it. The jar retains upstream LICENSE/NOTICE and bundled
dependency notices. The Java runtime retains its legal notices.

Native qualification runs as UID/GID 10001 with no network, a read-only root,
bounded noexec tmpfs, memory/CPU/process limits, no capabilities and no privilege
escalation. Parsing libraries and process deadlines are not a security sandbox.
Production hosting must provide the equivalent separate, credentialless workload
and deny arbitrary egress. The parser receives no source, database or model
credentials. Native cloud admission/egress and TLS are not proven by loopback tests.

Inputs are bounded at 10 MB, decoded text at 200 KB UTF-8, recursive Tika items at
64, JVM heap at 256 MB and JVM time at 30 seconds. The existing PDF path retains its
100-page/110-second limits. These are explicit resource limits; overflow rejects the
document rather than silently dropping pages or text. The image is qualified for
Linux amd64 only. Unsupported platform images must not inherit that claim.

`enterprise_parser_service.py` exposes only health and byte-only `/extract`, with
explicit owned admission, strict framing/MIME, bounded upload and a one-slot parser.
Duplicate credentials/content types, ambiguous framing, oversized requests and busy
admission are tested. An explicitly selected `private-ingress` mode relies on actual
authenticated hosting; arbitrary headers are not proof of that boundary.

`enterprise_parser_transport.py` is the application-side private HTTPS decoder.
Endpoint/admission are operator-owned, redirects and environment proxies are
disabled, response/schema/UTF-8 size and original SHA256 are checked, and a failure
returns no extracted body. Production source text remains untrusted model data.

## Reproduce and continue

Run the qualifier against an already-qualified owned local PDF parser image:

```sh
python3 scripts/qualify-enterprise-documents.py \
  --docker-host unix:///path/to/owned/docker.sock \
  --pdf-image atmem-qualification/invoice-parser:local \
  --out .local/fresh-document-qualification
npm run test:enterprise
```

The qualifier includes real Office->local HTTP parser->retrieval->citation tests,
revocation during parsing, edit during model generation and outage recovery with a
fresh download/parse. Microsoft HTTP and model output are explicitly scripted;
local RPC is loopback HTTP inside the isolated container, not production TLS.
All declared source/schema assets must exist. A source mutation during a run makes
the receipt unsuccessful even when its individual tests passed.

There is no extraction cache, ingestion worker, authorization cache or cached answer
fallback in this implementation. The current synchronous question path can exceed
the browser deadline for expensive documents. Next implement asynchronous bounded
extraction/immutable parser-versioned caching, preserving live caller authorization
before every cache use and release, encrypted regional content storage, deletion,
retention and recovery. Then complete cloud model/audit/company provisioning,
native four-provider application/Terraform/Spec Kit generation and actual live
project exports. Do not substitute this decoder increment for those deliverables.

Primary sources reviewed and raw response hashes retained with qualification:

- https://tika.apache.org/download.html
- https://tika.apache.org/3.3.3/gettingstarted.html
- https://tika.apache.org/security-model.html
- https://tika.apache.org/security.html
