# Planned acceptance walkthrough

No maintenance command or endpoint is implemented yet. The steps below are the manual release test card, not runnable product claims. T004/T007 must add exact commands after implementing the runner; blocked prerequisites must remain visible.

1. Use frozen sanitized source fixtures from R0, never current customer bundles. Confirm hashes for Terraform, provider, recipe, shared module and baseline roots.
2. Start Architect locally with `npm run local` using the existing supported installation prerequisites. Once R1 exists, open Maintenance on a selected project, choose local fixture roots and a supported target.
3. Approve isolated computation within budget. Verify original files unchanged. Inspect baseline, failing version-only control and independently checked meaningful candidate patch. Confirm skipped checks do not appear passed.
4. Change an input or accepted decision. Confirm old evidence/authorization goes stale; regenerate and export/reimport without reusable credentials/permissions.
5. R2: select a module and two consumer fixtures. Inspect graph, exact overlay checks, proposed module-version publication step and consumer order. Missing consumer or dynamic ref blocks ready status.
6. R3: only after separate explicit authorization and disposable GitHub test repositories, review preview and approve exact publication. Interrupt a remote response; recovery shows the original PR, never duplicates it. Human commit halts refresh; revoked token prevents new writes.
7. R4: enable a bounded 30-snapshot schedule. Replay upstream/webhook events and restart workers. Confirm deduplication, budget accounting, held versions, private isolation, cancellation and retention deletion.
8. Download evidence manifest; independently rerun documented commands in a clean environment. No AWS credentials, state/import/apply or runtime-deployment claims are needed for baseline qualification.

Required regression commands before each implementation release: `npm test`, `npm run test:server`, `npm run test:browser`, `npm run build`; `npm run notices` when dependencies change. These have NOT been executed for this documentation-only planning work and do not qualify maintenance until its tests are implemented.
