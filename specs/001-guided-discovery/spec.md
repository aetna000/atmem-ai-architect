# Feature Specification: Guided discovery

**Feature Branch**: `001-guided-discovery`

**Created**: 2026-11-05

**Status**: Release-1 slice built — see tasks.md

**Input**: Journey step 1 — "The agent asks questions about the desired application, current systems, cloud preference, data, requirements and budget." Users "can describe their environment, import a design or begin from scratch." Action plan 2: map discovery questions and inputs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Describe the situation and be understood (Priority: P1)

A user describes what they want in their own words. The agent plays back what it heard, files it under the right discovery topic, and asks the most useful next question. The user always sees what is known and what is still missing.

**Why this priority**: Every design, review and estimate depends on these inputs.

**Independent Test**: Start an empty project, answer the agent in free text for five turns, and check that each answer is filed under a topic, played back, and the next question targets an unknown topic.

**Acceptance Scenarios**:

1. **Given** an empty project, **When** the user says "we get 20k support emails a month and want an assistant to draft replies", **Then** the agent plays it back, files the application and expected usage, and asks about an unknown topic.
2. **Given** all required topics answered, **When** the user asks what is missing, **Then** the agent says discovery is sufficient and offers to draft a design.
3. **Given** an answer that contradicts an earlier one (budget £5k/month, later £2k/month), **Then** the agent flags the conflict and asks which is current, keeping the date of each statement.

---

### User Story 2 — Start from what already exists (Priority: P1)

A user starts by importing a design (AtMem AI Architect file, OpenArchFlow JSON, Mermaid, SQL DDL, Pulumi stack export) or by marking current systems on the canvas. Imported components are marked *existing*, and discovery questions about them are pre-answered where the import provides the information.

**Independent Test**: Import a Mermaid diagram of an existing system; confirm the components are marked existing and "current systems" is filled.

**Acceptance Scenarios**:

1. **Given** an import, **When** it completes, **Then** imported components are marked existing and listed under current systems.
2. **Given** a Pulumi stack export, **Then** regions and providers found in it pre-fill cloud preference and data location as *assumptions to confirm*, not facts.

---

### User Story 3 — Qualify before investing (Priority: P2)

The user lists candidate use cases and marks each Pursue, Park or Rule out with a reason (strategic fit, risk, value). Only pursued use cases move to design. *(Built.)*

### Edge Cases

- The user skips a question: it stays open and is listed as an open question in outputs.
- The user gives a number without a unit or period ("budget 5000"): the agent asks for the unit and period before using it in an estimate.
- Sensitive data mentioned (health records, payment data): the data topic is flagged for the review (003).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Discovery MUST cover these topics: desired application (purpose, users, channels), current systems and integrations, cloud preference and existing accounts, data (sources, location, volume, sensitivity, residency), requirements (functional and non-functional), expected usage (users, requests, documents, tokens), budget (amount, currency, period) and timeline.
- **FR-002**: Each answer MUST be stored with the date it was given and its source (user, agent inference, import).
- **FR-003**: Inputs that feed calculations (usage, budget, data volume) MUST be stored as structured values with units, not only text, and MUST name which review rule (003) or cost driver (004) consumes them.
- **FR-004**: The agent MUST play back what it heard and ask at most two questions per turn.
- **FR-005**: Conflicting answers MUST be flagged for the user, keeping both with dates; neither is discarded automatically.
- **FR-006**: Unanswered required topics MUST appear as open questions (002) in every output.
- **FR-007**: The user MUST be able to begin from scratch, from a template, or from an import.

### Key Entities

- **Discovery topic**: one of the FR-001 topics, with completeness state.
- **Answer**: text plus optional structured value, unit, date, source.
- **Use case**: title, value, risk, fit, verdict, reason.

## Success Criteria *(mandatory)*

- **SC-001**: In user tests, 80% of participants reach a complete discovery in under 15 minutes.
- **SC-002**: 100% of calculation inputs used by 004 have a unit and a source.
- **SC-003**: No question is asked twice once answered (automated conversation test).

## Assumptions

- The discovery question bank is refined by research task R2; topic list above is the starting set.
- Offline (no model) discovery uses the deterministic listener; a connected model improves wording, not the stored structure.

## Live dictation correction — 7 November 2026

Owner clarification: one-way voice input, like the ChatGPT/Codex composer. The
user speaks, sees the transcript appear, then explicitly posts it. The model's
output belongs on the design and in text; replies must not be read aloud.

- **FR-008**: Starting dictation MUST capture microphone audio and update an editable
  composer progressively, without calling the architect or submitting a message.
- **FR-009**: Explicit Stop MUST finalise remaining words. Explicit Send during recording
  MUST finalise the current transcript and post once through the existing architect
  path, preserving proposal/undo/approval behaviour. The actual response updates the
  design; no speech playback or automatic conversational restart is permitted.
- **FR-010**: Use local transcription rather than the unreachable browser speech service.
  Show preparation, recording, finishing and actionable errors; cancellation, typed
  edits and project replacement MUST fence late results and release the microphone.
- **FR-011**: Disclose local audio processing before first activation. Raw audio MUST
  remain in memory, never in logs/project files/memory events. Bound clip size and
  decoding work; require existing loopback Host/Origin/session protections. Model
  setup is explicit, with no recording-time model download or paid service fallback.

Acceptance: progressive partial words stay in the composer; zero architect calls
before user Send; latest words are finalised and sent once; returned graph proposal
updates the canvas. Permission/device/helper errors preserve drafts. Raw audio
routes reject missing auth, foreign origins, invalid/oversized formats. Actual local
transcription is tested with generated speech; physical microphone quality remains
an operator check, not inferred from fixtures.

- **FR-012**: Applied architect diagram proposals draw attention to changed blocks and connections with two gentle pulses and a focused viewport. The cue expires without entering saved project data or undo history. Removed connections focus surviving endpoints. Reduced-motion preferences use a steady outline and instant focus.
