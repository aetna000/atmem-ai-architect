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
