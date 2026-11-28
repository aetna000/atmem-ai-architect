# Engineering handoff review

28 November 2026 · Architect local candidate `0.2.8-handoff.1` · NextDNS-style DNS platform, design revision 1

The [branding update](../20261128-handoff-brand/README.md) records the current reader and the revised downloadable example.

## Recipient experience

Extract the team ZIP and open **index.html**. A team lead can review the scope and the next owner decision. An engineer can go directly to their work order. Operations can trace a failed lookup, rehearse a regional drain and see which capacity assumptions still need pricing. Everything required to read the website is inside the ZIP.

Open the delivered example in the local browser or import its editable source into Architect. [Handoff website](http://127.0.0.1:5286/) · [Installed Architect candidate](http://127.0.0.1:5185/) · [Importable design](../../../../examples/nextdns/project.json)

| What the team encountered | What the generator now delivers |
| --- | --- |
| Three prior engineering ZIPs contained 399, 491 and 870 entries, with 43, 33 and 43 top-level items respectively. Readers needed to choose between technical files and competing start guides. | One root document opens a seven-section reader. The DNS example has 25 reader files, including one nested engineering ZIP. Original project IDs, receipts and machine filenames stay available inside it. |
| Large legends made the drawing itself difficult to read. Sequence messages required the reader to match numbers against a second list. | The atlas opens on the context view where available. Drawings have separate expandable keys and an original-size control. Sequence sheets label messages on their arrows and distinguish returns and self-calls. Editable Draw.io pages accompany the drawings. |
| Authored Markdown, retained images and unavailable source figures could arrive separately. A filename alone gave the team little indication of what it could open. | Captured guides resolve relative paths, encoded spaces, reference-style images and image links. The browser decodes supported local images and rasterizes self-contained source SVGs. A missing, remote-dependent or corrupt picture receives a named entry with its document and recovery action. |
| A flat implementation task list mixed project-wide instructions with individual assignments. | The reader groups tasks by phase. Each component has a standalone work order with its inputs, outputs, responsibilities, dependencies, interfaces, recovery procedure and verification cases. Module exports include neighbouring interfaces and identify the assigned scope. |
| Captured code, proposed contracts and written acceptance cases could look equally ready to use. | Evidence identifies the design revision, outstanding findings and execution status. Captures retain their original engineering archive. A failed layout check remains visible even when a readable relationship sheet can be supplied. |

The earlier package counts came from read-only inventory. They establish navigation complexity. Missing-image behavior was independently reproduced with controlled source documents.

## Walk through the DNS design

| Reader section | What a receiving team can establish |
| --- | --- |
| Overview | The project contains eleven components and eleven directed interfaces. The one-hop map focuses on policy evaluation. The next decision names the product owner and the milestone for deciding allow/deny conflicts. |
| Diagrams | Nine sheets cover the system boundary, allowed and blocked queries, policy promotion and rollback, consent and retention, transport paths, regional failover, health signals and the complete board. Every interface has a direction, transport, input, output, authorization rule, failure behavior and verification method. |
| Scope and decisions | Ten linked requirements, four scope choices and three proposed architecture decisions make intended behavior reviewable. Commercial billing is deferred. DNS filtering covers domain questions. |
| Build plan | Start with a controlled zone and two contradictory tenant profiles. Prove filtering and cache isolation, connect the publisher, qualify privacy handling, then rehearse failover. Eleven work orders share 66 tasks grouped into eleven phases. Individual assignments preserve shared dependencies. |
| Operations and cost | Four proposed deployment units separate management, regional resolution, regional privacy storage and fleet monitoring. Runbooks cover signed revision rollback, optional history failures and regional recovery. Supplier rates and unmeasured quantities remain open. |
| Evidence and checks | Each requirement has a dedicated acceptance case with setup, input, action, expected result and evidence to collect. Cases include cached cross-tenant denial, policy publication failure, consent revocation, erasure retries, timing and regional drain. |
| Project files | The example includes two readable PDF names, one editable Draw.io file, standalone work orders and the complete engineering package. That package contains the editable Architect project, records, original paths and an offline qualification script. |

### Capacity and launch decisions

The example assumes a constant 500 queries per second for 30 days, yielding 1.296 billion queries. An 80% cache hit rate yields 259.2 million upstream lookups before retries. At 1% opt-in and 200 bytes per event, raw history ingestion is 2.592 GB per month before indexes, replication or backups. These are sizing assumptions. The worksheet shows quantities beside outstanding unit prices.

| Owner | Decision before launch | Current engineering action |
| --- | --- | --- |
| Product owner | Determine precedence for contradictory explicit allow and deny rules. | Maintain separate tenant fixtures and keep the conflicted case open. |
| Privacy owner | Approve regions, retention and backup erasure guarantees. | Keep history disabled until regional and deletion controls are agreed. |
| Service owner | Fund secondary-region capacity and set the latency and recovery objectives. | Measure warm and cold cache behavior, then prove the proposed region pair can absorb a drain. |

The architecture is an independent proposal. The product and privacy documentation establish public behavior. The CLI documentation establishes client-side forwarding capabilities. Platform topology, quantities and rollout procedures are example design choices. [NextDNS product](https://nextdns.io/) · [NextDNS privacy](https://nextdns.io/privacy) · [Pinned NextDNS CLI documentation](https://github.com/nextdns/nextdns/blob/469b3a1c1a8116df02b003504eb4a7cdd9500844/README.md)

The transport sheets link to the encrypted DNS standards. The DNSSEC standard supplies the validation reference for this review. [DNS over HTTPS](https://www.rfc-editor.org/rfc/rfc8484) · [DNS over TLS](https://www.rfc-editor.org/rfc/rfc7858) · [DNSSEC protocol modifications](https://www.rfc-editor.org/rfc/rfc4035)

## Independent checks

- Chrome opened the extracted site from disk with networking disabled. It followed 95 local links across twelve HTML pages, checked fragment targets, and decoded all nine diagram images. All seven sections fit widths of 320, 390, 768 and 1440 pixels. The offline reader made zero network requests and reported zero browser errors.
- A separate native-render audit measured text and node bounds, edge labels, connector strokes and reference retention. All nine drawings passed with 43 rendered node appearances and 40 relationships across the views. The negative control deliberately overlapped two nodes. The strict export rejected that drawing. The team export retained both nodes, recorded the failed native check and left the saved project intact.
- A freight survey transferred the same generator to another domain. An authored SVG produced a decodable 80×40 PNG. A corrupt image and a missing linked picture each produced a named finding. Other regressions exercised normalized pixel recovery, hostile markup, name collisions, Unicode, empty projects, scoped assignments, self-calls and return messages.
- The extracted engineering package contained 181 files. All 180 payload digests matched its manifest. Its own Python qualifier reconstructed eleven interfaces, ten case definitions, eight typed pages and three open owner decisions. The architecture board accounts for the ninth rendered sheet.
- The full JavaScript suite passed 788 tests. The production build completed. The file-import route and the local installed example provide separate entry points for checking the reader.
- A clean local installation served the example through its real backend. Preview took 5.56 seconds and download took 4.19 seconds in that run. The exported ZIP was 2,462,621 bytes. Background workers handled large compression jobs. These timings describe this machine and project.
- The installed check exposed a background project update that could silently dismiss a pending preview. The reader now keeps its explicitly requested snapshot open and labels newer changes. The team ZIP and all 25 extracted files were also compared byte-for-byte with the locally served website.

Inspect the delivered pictures and the machine-readable results. [Overview](overview.png) · [Service boundaries](service-boundaries.png) · [Allowed lookup sequence](lookup-sequence.png) · [Browser checks](browser-review.json) · [Native drawing checks](native-review.json) · [Package and snapshot qualification](qualification.json)

### Manual test card

1. Open **More → Open DNS handoff example** in the local candidate. In Delivery, choose **Preview handoff website**.
2. In **Diagrams**, open **Blocked lookup sequence**. Trace the denial and inspect the interface contract. Switch to original size to inspect a large drawing.
3. Open **Build plan → Policy publisher**. Find the signed-revision contract and its recovery case. Follow **Project build plan** back.
4. Download the team handoff. Extract it and open **index.html** while disconnected. In **Operations & cost**, compare the monthly query quantity with the outstanding price. In **Evidence & checks**, inspect the consent-revocation case.
5. For machine inputs, open **Project files → Engineering package**. Extract it and run `python3 qualification/check_handoff.py` from its root.

### Repeatable verification

Run from the Architect repository with installed dependencies and Playwright Chrome.

```sh
npm test
npm run build
node scripts/team-handoff-check.mjs .local/team-handoff-review
READABILITY_STRICT=1 EXPORT_EVIDENCE=.local/team-handoff-native node scripts/diagram-export-check.mjs http://127.0.0.1:5184 examples/nextdns/project.json
```

The last command needs a Vite development server at the specified address. Generated timestamps and per-project IDs can change ZIP digests between runs. The attached browser receipt identifies the delivered archive.

## Delivery boundary and rollback

The verified artifact is a design handoff. DNS service implementation, regional latency, failover capacity, provider pricing, real endpoint integration and production deployment still require execution evidence. External research links require connectivity when opened. The current offline and native rendering evidence covers Chrome on macOS.

The local candidate uses its own application data directory and port. To roll back the running preview, stop that instance with `atmemai stop --data-dir .local/team-handoff-candidate/home` from this repository. The existing stable installation uses its own directory. The original engineering download remains available in Delivery.
