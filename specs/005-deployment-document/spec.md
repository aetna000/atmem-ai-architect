# Feature Specification: Deployment document

**Feature Branch**: `005-deployment-document`

**Created**: 2026-11-05

**Status**: Release-1 slice built — see tasks.md

**Input**: Journey step 6 — "Generate a deployment document covering architecture, data flows, security controls, non-functional requirements, cost assumptions and deployment steps, clearly marking assumptions and open questions." "Regenerate the document from the updated project data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — One click, a complete document (Priority: P1)

The user generates a deployment document from the current project. It is readable by technical and non-technical stakeholders: a plain-language summary first, detail after.

**Independent Test**: Generate from a template; every section is present; every assumption and open question in the project appears in the document.

**Acceptance Scenarios**:

1. **Given** a project, **When** the document is generated, **Then** it contains: summary; scope and use cases; architecture (layers, components, diagram); data flows (each connection with data carried and classification); security controls; non-functional requirements with targets and review status; cost estimate with inputs and assumptions; decisions with owners and history; deployment steps; assumptions; open questions.
2. **Given** an unresolved blocker finding (003), **Then** the summary states the document is *not ready for deployment* and lists blockers.

---

### User Story 2 — Amend and regenerate (Priority: P1)

The user reopens a saved project file (002), changes a requirement and a decision, and regenerates. The document reflects the changes and states the revision and generation date; superseded decisions appear in history, not as current.

---

### User Story 3 — Export formats (Priority: P2)

Export as Markdown (with Mermaid diagram), Word (.docx) and PDF. The document is always generated, never hand-edited inside AtMem AI Architect; edits go into project data.

### Edge Cases

- Empty sections print "None recorded" rather than being dropped.
- Very large designs: data-flow table paginates; diagram per layer.

## Requirements *(mandatory)*

- **FR-001**: The document MUST be generated solely from project data (Principle III).
- **FR-002**: Each statement MUST be marked as fact (from project data), assumption, or open question; agent-generated text is labelled.
- **FR-003**: The document MUST print the project file format version, design revision, generation time and AtMem AI Architect version.
- **FR-004**: Deployment steps MUST come from the deployment plan (007) and never include credentials.
- **FR-005**: Markdown export MUST be available in release 1; Word and PDF MAY follow.

## Success Criteria *(mandatory)*

- **SC-001**: 100% of assumptions, open questions and current decisions in the project appear in the document (automated check).
- **SC-002**: Regeneration after an edit takes under 1 second for 200-component projects.
- **SC-003**: In user tests, non-technical reviewers can state the recommendation and top risks after reading the summary alone.

## Assumptions

- The client pack (`src/pack.mjs`) is replaced by this document once 003 and 004 land.
