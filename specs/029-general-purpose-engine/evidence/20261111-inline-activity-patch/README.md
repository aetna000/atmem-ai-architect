# Focused alpha.3.1 Design activity patch

Open http://127.0.0.1:5285/dist/index.html. Frozen source f5b88de, local tag
v0.2.0-alpha.3.1. This relative-base build uses the existing origin, local browser
project and live backend. The owner started native implementation work; the upgrade
guard refused a service restart, so the old dev-module cache remains at the root
URL until a later idle restart. No owner work was stopped, cloned or replayed.

The final follow-up fixes only the activity section shown in the owner's image:
old unassociated turns are one collapsed history (newest first), current progress
is a quiet line inside chat, public details expand on click, paired tool actions
are combined only when unambiguous. Exact model/effort and saved history remain.
atflow.css was inspected only. Wider Build layout/composer/scrolling edits were
removed after the owner's explicit scope correction. The earlier requested
Design-test-to-native-build action remains independently qualified.

Actual Claude Opus5.5 consultation: the first review inspected public synthetic
screens but could not find source filenames. The second received exact source
inline and corrected its event pairing/state/recovery assumptions. Reviews and
provenance are retained here; no private client content was sent to Claude. The
owner accepted only the narrow Design-card scope, not the wider recommendations.

Validation:480 JavaScript tests pass, no skips, and production/relative builds
pass.425 server tests pass on unchanged backend/skill source;150 such files match
alpha.3 exactly. Focused browser fixtures verify collapsed active polling, public
steps, history/no replay/model selection, mobile layout and explicit native test
handoff. Actual served built-page/read-only browser verifies seven historical
turns collapse into one disclosure, latest first, no large cards, zero inference
starts and no horizontal overflow. Source/build file hashes are in release-record.

The first live smoke checked DOM removal immediately after a native details toggle
and raced React's toggle event; corrected smoke waits for removal and passes. An
earlier fixture's900ms polling assertion raced the existing1s initial404 retry;
its failure is preserved on MEM0 and the corrected fixture observes actual next
polls. No production check was weakened or test result manufactured.

The earlier same-store idle upgrade retained both projects, seven historical turns
and49 public events. A live browser autosaved one file after reconnect; file byte
identity across that save is not claimed. Private snapshots/journals stay ignored.
Later native owner work is not a benchmark, a full-system acceptance or a UI test
fixture; leave it running. These UI checks do not generate or validate the website
application. Use Build and test for its actual implementation/local checks.

This is a patch to increment3; count remains3/10, complete originals1/28, owner
acceptance0 and quality unknown. Continue GE-005 region/ownership and the remaining
programme after this owner-priority fix. No cloud deployment authorized/performed.
