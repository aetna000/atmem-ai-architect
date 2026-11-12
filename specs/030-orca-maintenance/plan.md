# Orca integration and post-release maintenance

Owner requests, 2026-11-13: install/test Orca and publish its Architect plugin; fix credential-blocked Iowa storage pricing, repeated AWS placement warnings and slow/unexplained checklist navigation; update AtMem; add a GitHub-star invitation.

## Dependencies and acceptance

1. Preserve original 0.2.0 artifacts. Install official Orca and test an actual saved-project handoff, isolated from model/cloud actions.
2. Develop and qualify the separate `aetna000/atmem-ai-architect-orca` plugin. User explicitly approved its worker and five capabilities in this session. Publish an immutable Git tag/topic; distinguish publication from catalog indexing.
3. Extend the provider pricing contract with an explicitly selected Iowa Standard Storage public-table parser. Verify exact region, table, unit, source hash, 730-hour planning conversion and decimal-GB/GiB conversion. Retain source exclusions, manual prices and fail-closed behavior elsewhere.
4. Reuse accepted placement through the existing prefill mechanism. Deduplicate unresolved AWS region errors; route a working Choose region action to Choices. Do not replace explicit per-node placement or existing systems.
5. Show immediate pending navigation before rendering destination work; prevent duplicate clicks, focus the actual visible destination, and give pointer/wait cursors. Explain unpriced components or exclusions beside the cost checklist row.
6. Update the isolated memory pin/lock to PyPI stable AtMem 2.3.14 and its required AtFlows 0.1.8. Derive guards from the requirements pin, report the actual worker version, regenerate legal notices, and verify real memory operations and a synthetic 2.3.10 database upgrade.
7. Offer a concise, dismissible GitHub-star dialog after successful ZIP creation. Later/Escape/close snooze for 30 days; following the link suppresses future invitations without claiming a star was given. No automatic GitHub action.
8. Build, run regression and live UI checks, retain evidence, launch an isolated local candidate, and create a PR. This maintenance PR is not an npm publication.

## Limits

Public storage scraping currently verifies Iowa only; no other region is substituted. Full cost coverage still depends on service and usage inputs. Real-model generation, cloud deployment and Windows/Linux Orca plugin execution are not qualified here. Existing user data/runtimes and historical evidence remain intact.

## Owner follow-up: normal estimate state and responsive navigation

An available estimate is a normal Estimated state, with neutral exclusions. Numeric totals, missing charge details and complete-coverage semantics remain in the worksheet and exports; a mixed-currency result cannot become an estimate.

Delivery was generating PDF/diagram exports on entry and recompressing captured source for previews. Prepare lightweight source documents first, defer visual generation to preview/download, and only build the complete ZIP on explicit export. Preserve the same full PDFs/PNG/SVG in downloads and Orca handoffs; guard against a design changing during preparation. Remove the unconditional frame delay from checklist clicks.

Replace the combined Run checks action with Terraform validation / Run and Application tests / Run. Keep application tests disabled before files exist, with a hover/focus prerequisite. Each action starts only its named check family. Terraform validation can run independently of application generation.
