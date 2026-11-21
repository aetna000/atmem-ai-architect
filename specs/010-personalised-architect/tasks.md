# Tasks

## Design work completed

- [x] Inspect existing AtMem adapter lifecycle, scoping, procedure context and dashboard constraints
- [x] Specify user/organisation/project/knowledge/evidence context ownership
- [x] Specify the turn contract and scoped AtMem dashboard inside AtMem AI Architect
- [x] Discover official cloud/IaC skill source candidates; distinguish candidates from installed skills
- [x] Define bounded baseline comparison and failure/isolation scenarios

## Implementation status (2026-11-05)

- [x] Select and pin a clean, tested AtMem package/runtime combination
- [x] Define trusted local user/workspace/project/agent identity and scope bindings
- [x] Implement eligible project events and verified supersession with durable idempotent replay
- [x] Retrieve governed context before each selected model transport; record observed delivery evidence
- [x] Show scoped memory status, facts, decisions/history and per-turn context evidence in AtMem AI Architect
- [x] Add correction, forget and policy preview through verified scoped APIs
- [x] Review and pin the first small skill subset and its licences, content hashes and capability contracts
- [x] Publish skill catalogue/procedure records into AtMem; load exact reviewed artifacts on selection
- [ ] Add the host tool broker and qualify each transport's actual tool-calling support
- [x] Test restart, changed decisions, multiple projects/users, conflicts, outages and disabled skills
- [ ] Run and report the cost-bounded project-only versus memory/skills comparison

Implementation is single-user localhost: trusted scope bindings are installation-local, not a multi-user authentication service. Dashboard access uses AtMem AI Architect's authenticated, scoped SDK routes; the upstream native operator dashboard is not embedded. Runtime tools are provider-neutral structured requests handled by the host; real transport qualification remains incomplete. Native Claude live verification on this date was blocked by its account session limit; browser/model responses were deterministic fixtures using real AtMem storage and HTTP routes. The controlled baseline/context comparison remains outstanding and no quality-improvement claim is made.

Selective capture excludes diagram drafts, comments, positions and routine chat. Only eligible accepted decisions, explicit profile values, non-derived user-authored must-have requirements and budget limits enter personal/project memory. Skills occupy a separate knowledge scope.
