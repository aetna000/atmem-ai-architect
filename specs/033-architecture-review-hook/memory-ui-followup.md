# Memory and UI integration boundary

Owner request: exercise the real Codex workflow, explain reuse of AtMem memory,
and establish how the Architect UI will show correct review results.

## Native implementation update

The initial audit below describes the previous standalone state. The owner
clarified that Architect is the product: see spec.md's native IDE requirements.

Implemented locally since that audit:

- Exact project policy/review snapshots in the real AtMem SDK, with approval
  actor, revision digest, complete source episode and scoped lookup identity.
- Native Review controls, simple region/budget/privacy fields, advanced rules,
  progress/actions, findings and stale-response/design invalidation.
- Native Code it control and backend policy/design acceptance check. New workers
  receive an immutable generated Spec Kit/Terraform/rules baseline before coding.
- Same rules exported with the handoff; public engineering activity and
  captured-file/test stages remain in the existing UI.
- Project-scoped engineering status and exact policy/review snapshots available
  to AtMem-backed chat. Activity is not reclassified as successful test evidence.
- Actual browser/backend/AtMem pass -> fail -> pass, reload and mobile tests;
  actual live Codex Spec Kit hook fail/pass qualification.

Captured implementation archives now receive the same static rule review, excluding
pinned handoff inputs. Current canonical task IDs, source revisions and file hashes
bind implementation receipts; orphan output files and unknown task IDs are rejected.
Spec changes invalidate dependent mappings. Backend validation results are remembered
with artifact and validator contract hashes.

Remaining: organization-wide policy authorization, full task/test semantic acceptance,
live native Code it end-to-end qualification, worktree conflict reconciliation and
scale qualification. Native budget checks remain unverified; the real pricing
qualification is a separate synthetic case. Local policy revisions alone do not
establish these capabilities.

## Initial audit (historical)

PR #13 provides a standalone reviewer, MCP transport, CLI/CI and workflow
extensions. It does not expose the new reviewer in Architect's browser UI.
The existing review panels are different checks; their status is not evidence
that the new policy gate ran.

`server/memory_service.py` stores project/user context through the AtMem SDK.
`server/memory_context.py` labels retrieved context as context only.
`src/MemoryPanel.jsx` exposes memory browsing and preferences. These do not
currently define an approved organization policy or connect it to this reviewer.

The current file is a transport for structured rule contents. `review_plan`
accepts those contents in its request; the core does not require a disk file.
That permits a memory-backed adapter without replacing the deterministic engine.

## Initial proposed memory-backed contract (historical checklist)

- Store policies with explicit organization/project scope, policy ID, revision,
  status, approver and effective dates. Enforce authorization in the backend.
- An authorized owner approves a structured rule set. Remembered preferences,
  model suggestions and approximate search results do not grant approval.
- Resolve the applicable approved policy by exact identity and scope. Reject
  ambiguity and inaccessible, superseded, incomplete or unavailable snapshots.
- Pass the complete immutable policy snapshot to the existing reviewer.
- Bind the report to policy revision/content hash and project/design/plan hash.
  Preserve the exact evaluated snapshot for audit and reproducible CI.
- Keep `architecture.md` as an export/local workflow option. Define precedence
  explicitly when both memory and a repository policy are configured.
- A rule change or project change invalidates the current review. Never present
  an earlier passing result as approval of a different input.

## Initial proposed browser acceptance criteria (historical checklist)

1. Show the selected policy name/revision and a clear Run review action.
2. Show immediate pending/running state, prevent duplicate submissions and
   display actionable failures. Never silently reuse an earlier report.
3. Show the backend's PASS/WARN/FAIL and original evidence. Missing pricing,
   missing policy and unsupported checks remain explicit unknowns.
4. A browser test changes a private database to public: actual backend review
   returns FAIL, the evidence names the affected resource, and task generation
   stays blocked. Fix it and rerun: the applicable test policy passes.
5. Edit the policy or project while a review is running. An old response must
   be marked stale and must not unlock task generation for the newer input.
6. Show the same verdict and input binding through UI, MCP and fresh CI for
   identical inputs. UI screenshots alone do not qualify correctness.
7. Test approved/draft/superseded rules, unauthorized edits, cross-tenant reads,
   offline memory, failed requests, duplicate clicks and stale results.
8. Check keyboard/focus behavior, mobile layout, concise status copy and pointer
   feedback with actual browser automation and visual inspection.

The native integration above supersedes this historical audit. See evidence/native-integration.json
for executed checks and the remaining qualification boundaries.
