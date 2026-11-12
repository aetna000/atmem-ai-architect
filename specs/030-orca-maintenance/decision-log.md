# Decisions — 2026-11-13

- Use the existing Orca CLI handoff and plugin host API, not an embedded iframe that violates Orca’s network fence. Plugin work lives in its own Apache-2.0 public repository.
- Publish through a v0.1.0 Git tag and the `orca-plugin` topic. Orca’s community catalog is generated and must not be edited manually; listing is pending until its indexer observes the release.
- Iowa public Standard Storage pricing is available without credentials. Parse its explicitly selected region and first single-region table, retaining the hourly source and a disclosed 730-hour planning month; do not treat a region appearing in the dropdown as the selected price region.
- Reuse accepted cloud.region decisions for unresolved same-provider placement only. Repeated Lambda warnings become one direct Choose region action.
- Keep the released npm package unchanged while qualifying maintenance source. Its AtMem 2.3.10 pin was previously tested; the new candidate uses stable 2.3.14 and preserves old runtimes/data. Developer pip notices are excluded from the new inventory because the uv-managed distributed runtime contains six locked packages and no pip; their actual legal files are preserved.
- Star prompts follow a successful ZIP action, not startup or every visit. Store only a local snooze/link-open preference, not tracking or an assertion that the user starred the repository.

- Plugin 0.1.1 supersedes 0.1.0: real Stop testing showed Ctrl+C through the host API left the app running. Close only the created terminal through the CLI. Actual start, close and closed-port checks passed; the installed plugin was updated without additional capabilities.
