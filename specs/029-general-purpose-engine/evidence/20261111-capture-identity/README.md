# Repeated package capture preserves check visibility

Actual native repair's captured screenshot revealed a product issue: a manual
capture of identical checked bytes created a second artifact ID. Its panel then
showed no checks, because automatic receipts remained attached to the first ID.
The initial evidence and both original artifact identities remain preserved.

Delivery capture now reuses an existing ID only when the owned session/run and
complete manifest metadata except ID are identical, including pins, exclusions,
model/effort, status, modes/content digests and archive SHA. It verifies exact stored
archive bytes before reuse. Changed pins, source bytes or run produce a distinct
receipt; stored corruption fails rather than inheriting old evidence. Working
checkpoints retain their existing separate policy. No evidence crosses projects,
turns or a different capture contract, and no validator/model work is replayed.

369 server tests pass, no skips. Integration tests show a passed job remains listed
after recapture with exactly one worker execution, and distinct/changed/corrupt
counterexamples preserve their boundaries. Six actual isolated-runtime probes
exercise recapture/check visibility for rainfall Python and museum HTTP/Chromium,
failed assertion, zero-test suite, skipped test and no-applicable case. Reports and
source/policy hashes are in runtime/; lifecycle/model are explicit fixtures.
No new native generation or complete architecture acceptance is inferred here.

Manual test: complete native work with an automatic check; capture the unchanged
package again and inspect the same check report, reload and repeat. Change the
implementation in a subsequent turn and verify it needs its own package/check.
Rollback to abc0e9f with separate app data to restore the prior capture behavior;
retain journals/artifacts, including duplicate historical IDs. No version/release
or original-project acceptance is created by this fix.
