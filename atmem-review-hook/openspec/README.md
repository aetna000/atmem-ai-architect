# AtMem-reviewed OpenSpec schema

Copy `schemas/atmem-reviewed/` into a project's `openspec/schemas/`. Select `schema: atmem-reviewed` in its existing `openspec/config.yaml`, preserving other project context and settings.

If no team policy exists, adapt the included `examples/architecture.md` as `openspec/architecture.md`; preserve existing policy.

Connect the local `atmem-architect` MCP server first; see the parent package README. Validate with `openspec schema validate atmem-reviewed`.

The review artifact depends on specs and design; tasks depends on the review. The reviewer receives explicitly supplied contents and returns evidence, not implementation changes. On FAIL, the agent archives an old current `review.md` and writes `review.blocked.md`. On a permitted WARN/PASS, it writes the current `review.md` with the raw result. Default WARN is allowed; strict policy requires warning failure.

The CLI checks artifact existence, not the truth or freshness of its contents. Prompt compliance is not guaranteed. Use `atmem-review-ci` against current files for the executable policy gate.

Local qualification uses OpenSpec 2.1.0 and actual fail/warn results; it does not prove all agents obey the instructions. No public schema submission or catalog listing is claimed.

For a manual command outside the schema, see `command/INSTALL.md`.
