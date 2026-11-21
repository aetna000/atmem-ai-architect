# Decision log

- 2026-11-07: User requested all remaining six AWS scenarios and a complete archived prompt/results runbook with loadable examples.
- User required a commit, push and milestone tag before further product changes. Checkpoint 96e369d and milestone/aws-qualification-foundation-2026-11-07 were pushed first; its known failing JavaScript assertion is disclosed in commit/tag text.
- Archive the latest complete selected exports separately from the earlier live-tested storage revision. Do not transfer live success to a different artifact.
- Preserve all initial/refinement prompts and responses, including the failed connector run and corrected rerun. Publish sanitized evidence and SHA-256 hashes, excluding secrets, state and private account plans.
- Read-only plans for all six remaining scenarios passed in Sydney. Account preflight blocks every deployment because actual Lambda quota remains 10. Retain positive per-function concurrency bounds; do not bypass the gate.
- Use the previously checked regional Nova Micro candidate with 256 output tokens for account plans. No model inference performed. Live multi-user testing will require distinct scoped test identities; read-only principal bindings do not establish isolation.
- Browser import test initially encountered the normal first-launch connection dialog. Configure the isolated test's mock connection before opening the menu; the corrected run passed all seven imports. No production code change was needed for that test setup.
