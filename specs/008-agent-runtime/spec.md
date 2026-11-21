# Feature Specification: Adbot agent runtime and Adflow traces

**Feature Branch**: `008-agent-runtime`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Product roles — "Adbot: the agent framework used internally by AtMem AI Architect." "Adflow: configured agent-run tracing and cost visibility. This is separate from the estimated cost of the customer's cloud architecture." Action 5 — "use the Adbot framework for the agent and Adflow for run traces where configured."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The architect runs on Adbot (Priority: P1)

The sidecar's architect uses the Adbot framework for conversation state, tool calls (read project, propose change, run review, run estimate) and model access, replacing the composed Strands agent. The user-facing behaviour and proposal contract are unchanged.

**Acceptance Scenarios**:

1. **Given** the existing sidecar contract tests, **Then** they pass unchanged with Adbot behind them.
2. **Given** a tool call, **Then** the agent can read the project and propose changes but cannot write the project directly.

---

### User Story 2 — See what the agent did and what it cost (Priority: P2)

When Adflow is configured, each architect run is traced (prompts, tool calls, model, tokens, run cost, latency). The user can open the trace from the chat message. Run cost is labelled "agent run cost" and never appears in the architecture estimate.

**Acceptance Scenarios**:

1. **Given** Adflow configured, **Then** each chat turn has a trace link.
2. **Given** Adflow not configured, **Then** nothing is sent anywhere and the UI shows no trace links.
3. **Given** traces, **Then** project content in them follows Adflow's redaction rules and never includes credentials.

## Requirements *(mandatory)*

- **FR-001**: The Adbot name need not appear in the customer journey.
- **FR-002**: Tracing MUST be opt-in and local-first (Adflow running on the user's machine by default).
- **FR-003**: Agent run cost MUST be visually and textually separate from cloud cost estimates (004).

## Success Criteria *(mandatory)*

- **SC-001**: All existing sidecar tests pass on the Adbot runtime.
- **SC-002**: With tracing enabled, 100% of architect turns produce a trace; with it disabled, zero network calls to a tracer.

## Assumptions

- Adbot corresponds to `atbot/` and Adflow to `atflow/` (AtFlows) in this workspace; naming per OD-3.
