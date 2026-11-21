# 010 — AtMem-backed personal architect and specialist skills

**Status:** Proposed design, not implemented. **Date:** 2026-11-05.

AtMem AI Architect is the user's specialist AI architecture, cloud infrastructure and DevOps partner.
It uses AtMem to retrieve relevant user and project context, selects relevant reviewed
skills, uses available tools according to their permissions, and reports what informed its
advice. This extends 006 (memory) and 008 (runtime); it does not require a runtime rewrite
before the first AtMem integration.

## The experience

A user returns and says “let's continue the document assistant.” AtMem AI Architect recalls the
project's current requirements and decisions plus relevant confirmed user preferences.
It might say “We chose Azure because your team uses Microsoft 365; Australian hosting is
still required. Has either changed?” It asks about uncertainty instead of repeating
answered questions or silently treating old facts as current.

When the user asks about AWS alternatives, AtMem AI Architect selects comparison and AWS skills,
uses available documentation/pricing tools, shows tradeoffs against those constraints,
and proposes a diagram change. If the user chooses a new platform, the decision is
superseded with its reason. The next session retrieves the current choice and history.
If a pricing tool is unavailable, AtMem AI Architect reports that and keeps unpriced lines open.

The canvas and chat stay central. A **Memory** control opens the scoped AtMem dashboard
inside AtMem AI Architect. An expandable per-turn disclosure shows the facts, skills and tools
actually supplied or used; never an invented “thinking” trace.

## Context ownership

| Plane | Examples | Authority and use |
|---|---|---|
| User | Preferred explanation detail, role, skills, confirmed tool/IaC preferences | User-confirmed, dated; reusable across explicitly enabled projects for that user |
| Organisation | Approved cloud contracts, standards, residency and procurement constraints | Explicit workspace scope and authorised policy source; no inference of policy from personal preference |
| Project | Requirements, budgets, architecture choices, assumptions, open questions and revisions | Editable project remains canonical; AtMem keeps scoped contextual history |
| Specialist knowledge | Reviewed architecture, AI, cloud, security, FinOps, IaC, CI/CD and operations procedures | Versioned skill artifacts plus source-linked AtMem procedures/catalogue records |
| Operational evidence | Tool requests/results, plan hashes, tests, account checks and approvals | Observed execution evidence; not personal facts or permanent permission grants |

A budget or cloud decision is project-specific unless explicitly stated otherwise. A
user preference never overrides a current project requirement, applicable policy or
system-of-record evidence. Contradictions are retained and surfaced for confirmation.
Fresh external observations carry their source and time; estimates are never remembered
as provider quotations. A retrieved procedure is data until its exact reviewed artifact
is resolved by the skill loader.

## Turn contract

1. Resolve identity from trusted sidecar configuration/authentication: user, workspace,
   project, persistent agent, session and turn. Neither chat nor model selects another
   subject or workspace. Local mode starts with one configured OS-user profile.
2. Read the current project and permitted, bounded AtMem context. Record disposition:
   injected, withheld, unavailable or disabled. Respect AtMem's `inject` decision; never
   independently bypass it by searching the raw database.
3. Select candidate skills by request, journey stage, project constraints and capability
   availability. AtMem supplies catalogue/procedure candidates; a local registry checks
   exact version, digest, trust status and tool requirements before loading a skill.
   Load relevant sections on demand, not the entire worldwide catalogue.
4. Compose the architect request from role instructions, selected reviewed skills,
   current project, bounded governed context, recent chat and the actual tool menu.
   Memory cannot override role instructions, authorization or the project proposal contract.
5. The agent may request additional scoped context or an available tool. The sidecar
   validates scope, arguments and permissions, records request/result evidence and applies
   per-action approval for provisioning or other write operations. Tool access is not
   granted by a skill, memory, prior conversation or stored cloud preference.
6. Return advice or a reviewable proposal. Only accepted changes update the project.
   Emit the corresponding idempotent memory events with project/entity versions, source,
   actor, reason and timestamps. Record selected skill versions and actual tool outcomes.
7. Expose a concise “Context used” disclosure. Correlate the model response and tool
   evidence with this turn; do not equate successful retrieval with correct advice or learning.

## Skills must be represented in AtMem

For each enabled skill, AtMem holds a source-linked catalogue entry and reviewed procedure
content/references under a specialist-knowledge scope: skill ID, version, source repository,
commit, artifact digest, licence, purpose, triggers, provider, journey stages, required
capabilities, limitations, owner, review date and lifecycle status.

The immutable versioned artifact is the canonical skill implementation. AtMem indexes it,
retrieves relevant procedures and records use/outcomes; it is not an unversioned replacement
for files or a place to mix vendor guidance into personal memory. Skills cannot register
new tools or execute bundled scripts just because their text is retrieved. Changed artifacts
need a new reviewed version; deprecated versions remain available as historical evidence.

Initial coverage: requirements/discovery; AI/RAG/agents/ML design; cloud comparison;
AWS/Azure/Google Cloud; security and reliability; FinOps/ROM/detail; Terraform and Pulumi;
CI/CD, observability, incident/rollback planning; specification and handover. IBM and other
providers remain sketch/guidance coverage until their tools and deployment examples qualify.

Candidate sources are recorded in sources.json. They are discovery results, not installed,
activated, commercially cleared or benchmarked skill packs. Import a small task-relevant
subset with licence/provenance, review and scenario tests. Vendor guidance is selected only
after a provider choice or explicit comparison; vendor-neutral comparison remains an AtMem AI Architect skill.

## Scoped AtMem dashboard inside AtMem AI Architect

- **About you:** confirmed preferences, source, dates and where each is used; preview corrections,
  change project sharing and forget with the applicable policy.
- **This project:** current requirements/decisions, superseded history, assumptions, questions,
  conflicts, review dates and pending/rejected memory events.
- **Skills:** available, disabled, candidate and deprecated skills; exact version/source, scope,
  required tools and coverage. Installed skill and memory-index sync states are distinct.
- **Activity:** memory selected/withheld, context delivery at the observed boundary, selected skills,
  actual tool results, accepted project changes and approvals linked to the turn.
- Policy detail appears on demand: retention, supersession, duplicate/conflict handling and
  preview/apply receipts. Nothing is deleted by a model-written instruction.

Serve this view through the AtMem AI Architect sidecar with enforced scope on every request. The existing
AtMem loopback dashboard has no login and is an operator surface; do not expose an unfiltered
iframe or proxy it as a multi-user customer dashboard. Reuse supported AtMem read/report APIs
and components where their scope contract is verified. Missing APIs become explicit AtMem work.

## Failures and user control

AtMem outage: continue from the project, show “Memory unavailable — using this project only”,
and durably queue eligible project events for idempotent ordered replay. Rejected events stay
visible and do not roll back the user's project. Older queued revisions cannot replace newer
confirmed decisions. Conflicts require reconciliation. Opting out of memory stops capture and
recall for that conversation; opted-out content is never replayed later. Credentials are never
memory or project data. No default expiry is silently chosen for user or organisational data.

## Acceptance and evaluation

1. Restart: remember explanation preferences and the current project cloud/region choice,
   including a reason and ordered superseded history; do not repeat resolved questions.
2. Isolation: another project receives only explicitly reusable user preferences; another user
   or workspace receives none of the first user's facts, skills with restricted access, or traces.
3. Conflict: a remembered AWS preference cannot override a current Azure decision or residency
   requirement; the agent asks about ambiguous changes rather than silently changing the diagram.
4. Skills: AWS comparison selects the appropriate reviewed version; a deployment-only skill
   cannot run during read-only discovery; a missing tool is disclosed, never simulated as real.
5. Dashboard: show exactly the memories, procedure versions and tool evidence observed for a turn;
   correction/forget preview affects only authorised scope and preserves required receipts.
6. Recovery: replay after a simulated outage creates no duplicates, no out-of-order current
   decisions and no opted-out/credential content. Rejected writes remain inspectable.
7. Boundaries: native-client delivery is labelled at the observed CLI boundary; do not claim
   visibility into its hidden internal model prompt or unobserved subtool activity.
8. Small comparison: run a fixed, cost-bounded set with current project-only context versus
   AtMem plus selected skills. Measure correct current decisions, relevant constraints used,
   unnecessary repeat questions, hallucinated facts/prices, cross-project leakage, token cost
   and latency. Freeze models and cases. No “learned” or “better” claim without measured benefit.

## Decisions still needed before those implementation slices

- Pin an AtMem version and compatible runtime after testing a clean installed artifact.
  Local main is 2.3.8 and behind; the inspected 2.3.11b1 checkout contains ongoing changes.
- Confirm supported query/write/report APIs for separate user/project/knowledge scopes and the
  required decision supersession semantics. Do not assume recall implements arbitrary joins.
- Select retention/review defaults and whether a future organisation profile is owner-managed.
- Determine which connected/native-client transports can request tools reliably; qualify them
  individually while retaining a host-managed, model-provider-neutral context path.
