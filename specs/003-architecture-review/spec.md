# Feature Specification: Architecture review

**Feature Branch**: `003-architecture-review`

**Created**: 2026-11-05

**Status**: Release-1 slice built — see tasks.md

**Input**: Journey step 3 — "AtMem AI Architect identifies gaps, limitations, opportunities and trade-offs. Design for security and controls, reliability, availability, scalability, performance and maintainability, with measurable requirements where possible, sources and clearly stated assumptions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — See what's missing, grouped by quality (Priority: P1)

The user opens Review and sees findings grouped by quality attribute: security and controls, reliability, availability, scalability, performance, maintainability. Each finding says what was checked, what was found, why it matters, and what to do, and links to the components involved. Clicking a finding opens the component on the canvas.

**Independent Test**: Load a template with a known gap (no guardrail on the GenAI path); open Review; the gap appears under security with the affected components and a proposed fix.

**Acceptance Scenarios**:

1. **Given** a GenAI component reachable from a data source without a policy/guardrail block, **Then** a security finding is raised linking both.
2. **Given** a single model endpoint with no stated availability target, **Then** an availability finding asks for a target and lists it as an open question.
3. **Given** a finding, **When** the user marks it accepted risk with a reason and owner, **Then** it stays visible as accepted, not hidden.

---

### User Story 2 — Turn findings into measurable requirements (Priority: P1)

From a finding, the user (or the agent via proposal) creates a measurable requirement — e.g. "availability ≥ 99.9% monthly" — linked to components. Review then checks the design against requirements and shows met, at risk or not met, with the reason.

**Acceptance Scenarios**:

1. **Given** a requirement "p95 latency ≤ 2 s" on a GenAI component and a stated token budget per request, **Then** review shows *at risk* with the assumption it used, or *unknown* if inputs are missing.
2. **Given** a requirement with no measure, **Then** review marks it *not measurable* and suggests a metric.

---

### User Story 3 — Sources and trade-offs (Priority: P2)

Each finding and trade-off cites its source: an AtMem AI Architect rule (ID and version), a provider document (title, URL, retrieved date), or the user. Trade-offs present at least two options with consequences. Provider-specific findings appear only for validated providers (Principle V).

**Acceptance Scenarios**:

1. **Given** a provider-specific recommendation, **Then** it shows a document source and retrieval date, or is labelled "general guidance — not provider-verified".
2. **Given** a finding from a connected model, **Then** it is labelled agent-generated and cannot be marked met without user confirmation.

### Edge Cases

- Design with zero components: review shows only discovery gaps.
- Imported reference blocks without behaviour: reviewed structurally; runtime findings marked "cannot assess".
- Conflicting requirements (cost ceiling vs availability target): raised as a trade-off finding.

## Requirements *(mandatory)*

- **FR-001**: Review MUST run deterministic rules locally without a model, and MAY add model findings when a model is connected.
- **FR-002**: Every finding MUST have: id, rule id and version (or "agent"), quality attribute, severity (blocker, major, minor, info), statement, rationale, affected component IDs, recommended action, source, status (open, resolved, accepted risk), and owner/reason when accepted.
- **FR-003**: Rules MUST cover at least: missing guardrail on GenAI output path; confidential data without stated residency; single point of failure for user-facing components; missing monitoring for models; no human review for automated actions; unowned decisions; requirements without measures; missing availability, latency and cost targets.
- **FR-004**: Review MUST evaluate measurable requirements against stated inputs and report met / at risk / not met / unknown, showing the inputs and assumptions used.
- **FR-005**: Findings MUST be re-computed from current project data on every change; accepted-risk status persists by rule id + components.
- **FR-006**: Provider-specific checks MUST be gated by provider coverage level [NEEDS CLARIFICATION: first validated provider — OD-1].

### Key Entities

- **Finding**, **Rule** (id, version, attribute, check), **Trade-off** (options, consequences, chosen).

## Success Criteria *(mandatory)*

- **SC-001**: On a reference set of 10 designs with seeded gaps, deterministic rules find ≥ 90% with zero false blockers.
- **SC-002**: 100% of findings show a source.
- **SC-003**: Review updates within 200 ms of a design change for 200-component designs.

## Assumptions

- Rules are versioned in the repository and shipped with the app; no remote rule download in release 1.
