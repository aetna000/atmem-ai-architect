# Feature Specification: AtMem project memory

**Feature Branch**: `006-atmem-memory`

**Created**: 2026-11-05

**Status**: Draft — expanded user-context, skills and dashboard design in [010](../010-personalised-architect/spec.md)

**Input**: Product summary — AtMem as a headless memory and governance engine; "AtMem AI Architect … must report relevant changes"; default policies for duplicates, contradictions and expiry; user-defined policies with preview and audit; lifecycle with supersession; example: a change in cloud region supersedes the earlier decision and retains history. Action 5 — "Prototype a decision-change event and reviewable policy, then test that retrieval returns the current decision and its history."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Decisions persist across sessions (Priority: P1)

When the user accepts, revises or supersedes a decision, or adds a requirement, AtMem AI Architect reports an event to AtMem. In a new session — or a new project file opened on another day — the agent recalls the current decision and its history for that project.

**Independent Test**: With a local AtMem, accept "region = eu-west-1", revise to "eu-central-1" with a reason, restart; ask the agent "which region and why?"; the answer cites the current decision and the superseded one.

**Acceptance Scenarios**:

1. **Given** a decision revision in AtMem AI Architect, **Then** an event `decision.revised` is sent with project id, subject, new and previous decision ids, reason and timestamp.
2. **Given** that event, **Then** AtMem's supersession policy marks the previous memory superseded and records the new one as current, keeping history.
3. **Given** a retrieval for the subject, **Then** AtMem returns exactly one current decision plus its ordered history.

---

### User Story 2 — Reviewable policies (Priority: P2)

The user sees the active memory policies for the project profile (duplicates, contradictions, expiry, supersession), can preview a policy against existing memories before enabling it, and can see a log of what ran and what changed.

**Acceptance Scenarios**:

1. **Given** a policy preview, **Then** the user sees which memories would change and how, and nothing changes until applied.
2. **Given** an ambiguous conflict (two regions for different environments), **Then** it is flagged for review, not superseded.

---

### User Story 3 — Time-sensitive statements (Priority: P3)

Statements like "budget is £5k per month" are stored with the date they were made and a review date; outputs show "as of" dates. Deletion happens only by explicit policy.

### Edge Cases

- AtMem unavailable: AtMem AI Architect works fully from the project file; events queue locally and replay in order when AtMem returns; the user sees "memory sync pending".
- Event rejected by AtMem: shown to the user with the reason; project data is not altered.
- Two AtMem AI Architect clients edit the same project: last writer conflicts are flagged, not merged silently.

## Requirements *(mandatory)*

- **FR-001**: AtMem AI Architect MUST emit events for: requirement added/changed/removed, assumption added/changed, open question answered, decision proposed/accepted/revised/superseded, discovery answer changed.
- **FR-002**: Events MUST carry project id, entity id, subject, payload, actor (user/agent), timestamp and design revision, and MUST NOT carry credentials.
- **FR-003**: AtMem AI Architect MUST connect through AtMem's MCP interface or SDK [NEEDS CLARIFICATION: transport — MCP stdio vs HTTP for the local sidecar].
- **FR-004**: The AtMem AI Architect profile MUST enable default policies: duplicate detection, contradiction flagging, explicit expiry, and decision supersession by subject.
- **FR-005**: Retrieval MUST return current decision and history; a confidence score MUST NOT be presented as proof.
- **FR-006**: The project file (002) remains the source of truth for the project; AtMem is the cross-session memory and governance layer.

### Key Entities

- **Memory event**, **Policy** (trigger, condition, action, enabled, preview), **Policy run log**, **Memory** (statement, madeAt, reviewAt, deleteAt?, status current/superseded, history).

## Success Criteria *(mandatory)*

- **SC-001**: The region-change scenario passes end to end against a local AtMem in CI.
- **SC-002**: 100% of decision revisions produce a supersession in AtMem with history retained.
- **SC-003**: Offline queue replays without loss after a 24-hour outage (simulated).

## Assumptions

- AtMem (`aetnamem/`) exposes memory write, retrieval and policy APIs usable from the sidecar; any missing API is specified in the AtMem repository first.
