# Working checkpoints and registered isolated browser runtime

343 server tests and 374 JavaScript tests pass, no skips; production build and actual
fixture-browser lifecycle checks pass. Real executor qualification: six standard
positive/negative probes, plus browser-positive/Node-skip/Node-zero/Node-failure.
The first browser run correctly withheld a pass but exposed zero-test categorization;
retain before-zero-status-fix. Final Node-zero is failed, skipped is incomplete.
No original project, release, quality percentage or deployed system is accepted.

## Reusable capability and interfaces

`atmem_check_working(validatorId)` resolves the current project/workspace/turn from
backend-owned identity, verifies original pinned inputs, copies an immutable working
checkpoint and starts/reuses a registered validator. It returns checkpoint kind,
run/digest and a scoped check ID with separately paged reports. It accepts no command,
image, daemon, host path or tenant selector. A later edit needs a new checkpoint/check.
Exact unchanged checkpoint bytes reuse the same input/check; each run is limited to
16 distinct snapshots and 128MB stored checkpoint bytes. Individual snapshot bounds
remain 64MB/2000 entries. This is local single-supervisor control, not hosted quotas.

Working checkpoints have a separate table and `in_progress` kind/status. Delivery
list/get/download still use the settled delivery store, and settled capture remains
mandatory. Check storage resolves both source types without turning working evidence
into delivery. Both collectors reject links/special files, preserve modes/pins, use
deterministic directory/file ZIP metadata, and recheck the observed tree for changes
before persistence. This detects observed races; it is not a filesystem-wide atomic
snapshot or a promise that later working files match the checked bytes.

Transfer/counterexamples cover plain modules and browser/service test code; unchanged
reuse versus later edits; foreign identity; modified/missing pins; unsafe links;
a late write to an already captured file; storage limits; and separation from delivery.
Existing durable call/check reservation, uncertainty, restart cleanup and no-replay
contracts are retained. Native invocation of this new working tool is still pending.

## Browser policy and provenance

The optional operator-only `ENGINEERING_ISOLATION_PROFILES` registers
`chromium-userns-v1` with a local policy path and exactly reviewed SHA-256
`e53c15d248f57bceec0a3a16fad1b4ab0d05a7bddb455f86a60e2dba5612cdf7`.
The pinned upstream revision, derivation and image/module hashes are retained in
../20261111-uncoached-product-run/browser-runtime-preparation/.
Use scripts/engine-evaluation/prepare-browser-policy.py to reproduce the reviewed
profile; no unconfined, arbitrary profile or runtime download is accepted.

A registered ValidationSpec chooses isolationProfile and only explicit image-local
ATMEM_PLAYWRIGHT_MODULE/PLAYWRIGHT_BROWSERS_PATH values. Browser profile allows bounded
user-namespace creation/chroot for Chromium's own sandbox; it adds no outer bounding
capability. Resources are 512MiB/128 PIDs/one CPU, bounded timeout/output and private
64MiB /tmp. Standard checks retain 256MiB/64 PIDs. Both retain nonroot/no-new-privileges,
read-only root/source, network-none, no host mount/socket/IPC/network, cached exact
platform/image selection and pull-never. Catalog reports configured availability and
runtime interfaces; unavailable entries are disabled in the UI. No command bodies or
oracle source are exposed by catalog metadata.

Actual positive oracle requests Chromium sandbox and executes a page/clear action,
then independently detects the browser fetch-receiver error class missed by Node.
It also verifies denied outer chroot, raw sockets, source writes, external network,
host paths and Docker socket. Tests may choose browser options, so the worker's outer
container guarantees and a particular test's Chromium sandbox request are separate
claims; do not infer browser-internal sandbox from a profile name alone. This remains
a qualified local development runtime, not hosted tenant isolation or cloud deployment.

Next: actual fresh native HTTP/browser/working-check transfer, then generic final
validation/repair ownership and coherent native-first intake. Whole journeys require
independent oracles in addition to generated tests; all 28 and ten release gates remain.


## Actual native working-check/HTTP/browser transfer (frozen source 838762a)

A fresh actual gpt-6.1-sol/high session builds the explicit local volunteer note
preview fixture through the product API: one accepted start, no steering, completed
turn, 15 captured files, no monitored source changes. This deliberately exercises
the offered tool interface and stable HTTP contract; it is not an uncoached
architecture, holdout, comparative win or original-matrix acceptance. The generic
runner's original boundary wording is retained but superseded by this explicit scope.

Seven successful native callbacks include catalog, reviewed knowledge search/full
read, two working snapshots/check starts and two report reads. Both working checks
run seven authored tests with real HTTP and sandboxed Chromium, no skips. The first
snapshot differs after evidence-document updates; the second checkpoint SHA matches
the final settled delivery SHA exactly:
24578c14f1e70f5488d3121252da6eb016dadfdbf949f012dbf197778acd201b.
A separate final delivery check repeats the seven tests on that archive. Working
checkpoints remain kind=in_progress evidence in their own table, while one delivery
is captured separately. Read-only native history and durable bindings are audited.

A separately authored oracle, not imported from generated tests, passes 20 assertions
on the unchanged final archive using its actual HTTP service and Chromium. It covers
exact/no-store output, malformed/wrong-type/missing/extra/blank/oversize rejection,
the documented 2000 UTF-16-unit boundary, content-type/method/unknown-action denial,
safe server failure and recovery, five parallel isolated values, safe browser text,
clear, empty input recovery, no browser persistence/reload state and delayed clear
with cancellation both effective and deliberately ignored. Preview-function timing/
failure and one cancellation transport are explicit fixtures. No emitted file is
repaired and no cloud/vendor identity/model integration is claimed.

The generic external driver also attempts Python validators against this Node-only
fixture. Their missing/zero suites correctly fail and remain in checks.json. They
are not silently converted into passes or used as Node application acceptance.
The native session chose the applicable Node validator. Applicability-aware generic
check scheduling is still needed; no broad all-checks/project-pass claim is made.

After this frozen native proof, a small follow-up adds an explicit scoped
atmem_check_recover tool for uncertain working checks, because working IDs are not
shown as delivery packages in the UI. It confirms cleanup only on the original
worker, retains the failed receipt and never reruns work. Ownership/idempotence/no-
replay regression passes; updated full suite:344, no skips. This new callback itself
is not included in the seven-callback proof and existing native tool registrations
are not rewritten on resume. Fresh sessions receive the new registry. Full-source
release qualification, generic final check/repair ownership and native-first intake
remain pending. No release or original project is accepted.
