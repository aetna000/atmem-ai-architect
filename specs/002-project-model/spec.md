# Feature Specification: Project model and project file

**Feature Branch**: `002-project-model`

**Created**: 2026-11-05

**Status**: In progress

**Input**: Product summary — "Define a structured model for diagram components and connections, and keep the agent and canvas in sync." "Export an editable project file containing the diagram, requirements and decisions. Users can import it later, amend the project and regenerate the document from the updated project data." Open decision OD-4: project file format and versioning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Save a project and reopen it later (Priority: P1)

A user exports their project to a single file, closes AtMem AI Architect, and weeks later opens the file to carry on. Everything they made is back: the diagram, discovery answers, requirements, assumptions, open questions, decisions with their history, and options scores. Files from earlier AtMem AI Architect versions open too.

**Why this priority**: Every later output (review, estimate, deployment document) must be regenerable from saved project data. Without a durable file there is no "revisit".

**Independent Test**: Export a project, clear browser storage, import the file; compare every user-entered value with the original.

**Acceptance Scenarios**:

1. **Given** a project with components, connections, requirements, assumptions, open questions and decisions, **When** the user exports and re-imports it, **Then** all of them are identical and the design revision is preserved.
2. **Given** a file saved by the earlier workbench format (version 1), **When** the user imports it, **Then** it opens, is upgraded to the current format, and the user is told it was upgraded.
3. **Given** a file written by a newer AtMem AI Architect version, **When** the user imports it, **Then** import is refused with a message naming both versions, and the current project is unchanged.
4. **Given** a file containing fields this version does not know, **When** it is imported and exported again, **Then** those fields are kept under extensions, not dropped.

---

### User Story 2 — Requirements, assumptions and open questions as records (Priority: P1)

While designing, the user (or the agent, through a proposal) records requirements — functional and non-functional, with a measurable target where possible — plus assumptions and open questions. Each can point to the components it concerns. The agent reads these records alongside the diagram.

**Why this priority**: Review (003), estimate (004) and the deployment document (005) are generated from these records. Stated assumptions and open questions are a constitution requirement (Principle II).

**Independent Test**: Add a measurable non-functional requirement linked to a component, an assumption and an open question; reload; confirm they persist, appear when the linked component is opened, and are sent to the agent as read-only context.

**Acceptance Scenarios**:

1. **Given** a component, **When** the user adds a requirement "p95 latency ≤ 2 s" in category performance linked to it, **Then** the requirement shows its metric, target and unit, and the component detail lists it.
2. **Given** a removed component, **When** a requirement linked only to it remains, **Then** the requirement is kept and marked as having no linked component.
3. **Given** a live architect request, **When** it is sent, **Then** current requirements, assumptions, open questions and current decisions are included as read-only context, and the agent cannot change them except through a proposal.

---

### User Story 3 — Decisions keep their history (Priority: P2)

When a decision changes — say the cloud region moves from eu-west-1 to eu-central-1 — the user revises it with a reason. The new decision becomes current; the old one is marked superseded and kept, with who changed it, when and why.

**Why this priority**: Required for the AtMem supersession example (006) and for an honest audit trail in the deployment document.

**Independent Test**: Accept a decision on subject "cloud.region", revise it with a reason; check that the current decision is the new one and the history lists both in order.

**Acceptance Scenarios**:

1. **Given** an accepted decision on a subject, **When** the user revises it with a reason, **Then** a new accepted decision is created that references the old one, and the old one becomes superseded and references the new one.
2. **Given** a subject with three revisions, **When** the current decision is requested, **Then** exactly one current decision is returned, with its two predecessors in history order.
3. **Given** a revision without a reason, **When** the user tries to save it, **Then** saving is blocked until a reason is entered.

---

### User Story 4 — Agent and canvas share one model (Priority: P2)

The agent receives the diagram as structured data and returns proposals as complete candidate projects. Each proposal shows what changes and why before anything is applied.

**Why this priority**: Already largely in place; this story fixes the contract so later features can extend it safely.

**Independent Test**: Send a request through the mocked sidecar; verify the request contains the structured project and context, and that an applied proposal leaves requirements, decisions and discovery data intact.

**Acceptance Scenarios**:

1. **Given** a proposal that changes only the diagram, **When** it is applied, **Then** requirements, assumptions, open questions, decisions and discovery answers are unchanged and a decision recording the change is added.
2. **Given** a proposal based on an older revision, **When** the user tries to apply it, **Then** it is refused and the user is asked to request a new proposal.

### Edge Cases

- A file over 2 MB, with over 200 components or over 600 connections is refused.
- Duplicate IDs, connections to missing components, or unknown component kinds are refused with the offending item named.
- A value that looks like a credential (cloud access keys, API keys, private keys, password fields) blocks export and import, naming the field. Nothing is silently stripped.
- Requirements and decisions referencing missing components keep the reference and are flagged.
- Invalid measurable targets (non-numeric target for a numeric operator) are refused at entry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project file MUST identify itself with format `atforma.project` and a semantic `formatVersion`; this feature defines `2.0.0`.
- **FR-002**: The project file MUST contain meta (id, name, created, updated, design revision, generator), design (components, connections), discovery, requirements, assumptions, open questions, decisions, options and extensions.
- **FR-003**: Import MUST migrate every earlier supported format (the version 1 workbench format) and report that a migration happened.
- **FR-004**: Import MUST refuse a higher major version and accept a higher minor version, keeping unknown fields under extensions.
- **FR-005**: Export followed by import MUST reproduce every user-entered value (round-trip without loss).
- **FR-006**: Requirements MUST record kind (functional, non-functional), category (security, reliability, availability, scalability, performance, maintainability, cost, compliance, other), statement, priority (must, should, could), status (open, met, at risk, not met), source (user, agent, import), linked component IDs and an optional measure (metric, operator, target, unit).
- **FR-007**: Assumptions MUST record statement, source, owner, and linked components. Open questions MUST record question, owner, status (open, answered) and answer.
- **FR-008**: Decisions MUST record subject, title, status (proposed, accepted, superseded), owner, context, options, decision, consequences, date, design revision, and the IDs of the decision they supersede or are superseded by, with the reason for change.
- **FR-009**: Revising a decision MUST create a new record and mark the previous one superseded; previous records are never edited in place after supersession, except to add the superseded-by link.
- **FR-010**: The system MUST return, for any subject, the single current decision and its full history.
- **FR-011**: Export and import MUST refuse content that matches credential patterns, naming the field path.
- **FR-012**: The architect request MUST include current requirements, assumptions, open questions and current decisions as read-only context.
- **FR-013**: Applying a proposal or loading a template MUST replace only the design, never the discovery data, requirements, assumptions, open questions, options or decisions.

### Key Entities

- **Project**: the unit a user saves and reopens; owns everything below.
- **Component / Connection**: the diagram (kind, provider, label, description, configuration, origin existing/proposed, prototype scope, success measures).
- **Requirement**: what the solution must achieve, optionally measurable, linked to components.
- **Assumption / Open question**: what is believed without evidence, and what still needs an answer.
- **Decision**: a choice on a subject, with lifecycle and history.
- **Discovery data**: brief, use cases, options scores, scale gate (from 001 and the current workbench).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of user-entered fields survive export → import in the automated round-trip test across all templates.
- **SC-002**: Every version 1 project saved by the current workbench opens without manual edits.
- **SC-003**: For any decision subject, current decision and history are returned correctly in 100% of test cases, including three-step revision chains.
- **SC-004**: No exported test file contains a value matching the credential patterns.

## Assumptions

- JSON is the file format (human-readable, diff-friendly); the file extension is `.atforma.json` (resolves OD-4 provisionally).
- One project per file; no multi-project workspaces in release 1.
- Browser local storage remains the autosave location; the file is the durable, portable copy.
- AtMem synchronisation of decisions and requirements is specified in 006 and is not required for this feature.
