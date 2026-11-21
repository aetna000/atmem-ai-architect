# Plan — make AtMem part of every eligible architect turn

**Status:** Proposed. No runtime integration or external skill installation yet.

## Existing evidence and constraints

AtMem's framework-neutral `AtMemTurnLifecycle`/`AtMemAdapterIdentity` expose begin,
context_for_model, model_input/model_output, tool_requested/tool_completed and end.
ControlPlaneManager and existing framework adapter documentation describe governed capture,
preparation and exposure confirmation. AtMem AI Architect currently passes project-derived context and
has no AtMem boundary. Start by wrapping that boundary; replacing all model clients or adopting
a different agent framework is not a prerequisite.

Keep CLI and direct SDK delivery claims separate. A native CLI may change or summarise its
internal prompt: record exactly what AtMem AI Architect passed to that client, not unobserved internals.
Use existing AtMem contracts where verified; do not invent method names for supersession,
scoped knowledge queries or dashboard projection before inspecting and testing those APIs.

The AtMem checkout and prerelease worktree are both dirty. Design against their documented
contracts, then qualify one clean version independently; do not edit, reset or install those
working trees into AtMem AI Architect as an implicit dependency upgrade. Do not alter the user's existing
memory database for integration tests. Use temporary test stores and configured app scopes.

## Delivery slices

1. **Memory foundation (006):** pin compatible AtMem; configure trusted local identity; capture
   eligible events; retrieve bounded user/project context before requests; preserve governed
   withholding; implement durable ordered/idempotent replay and an honest availability status.
2. **Visible memory:** scoped dashboard inside AtMem AI Architect, initially inspecting facts, decisions,
   history, pending sync and turn evidence. Add correction/forget/policy preview using verified
   AtMem APIs and explicit user actions. Do not expose the entire operator dashboard.
3. **Specialist skills:** versioned skill manifest, reviewed artifacts and tool-capability contracts;
   publish indexed metadata/procedures into AtMem; select by stage/request/constraints; record
   loaded versions and why. First compare two small use cases before importing more material.
4. **Tools:** model-provider-neutral host tool broker: scoped context lookup, project read/proposal,
   deterministic review/estimate and document export first; current documentation/pricing and
   read-only inventory next; validated plan/approval/apply only after provider-specific testing.
5. **Evaluate:** returning user, revised region/cloud, conflicting old preference, second project,
   different user, memory outage, disabled skill and unavailable pricing tool. Native baseline
   versus memory/skills on fixed scenarios; record correctness, cost and latency.

## Constitution check (I–VIII)

I: proposals/explicit actions; tool broker enforces approvals. II: source/time/evidence attached;
no learned-improvement claim. III: project canonical, memory contextual; exports derive from the
project. IV: local-first, trusted identity, no credentials in memory. V: broad sketching, explicitly
qualified tool/provider coverage. VI: scoped dated facts, supersession, preview and policy-based
removal. VII: one Memory drawer with details on demand. VIII: isolated real-AtMem contract tests,
small baseline comparison and browser journeys per slice.

## Source evidence inspected

- ../006-atmem-memory/spec.md and ../008-agent-runtime/spec.md
- /Users/javadtaghia/gitlab/aetnamem/docs/framework-adapters.md
- /Users/javadtaghia/gitlab/aetnamem/docs/saas-integration.md (identity and dashboard boundaries)
- /Users/javadtaghia/gitlab/atmem-release-2.3.11b1/atmem/adapters/base.py
- /Users/javadtaghia/gitlab/atmem-release-2.3.11b1/atmem/context_engine/pools.py
- AtMem AI Architect server/architect.py, server/contracts.py, server/local_providers.py and src/local-agent.mjs

These are inspection paths, not portable runtime dependency paths or proof of release availability.
