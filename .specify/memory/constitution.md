<!--
Sync Impact Report
- Version: 1.0.0 → 1.1.0 (Principle I: opt-out "Draw as we talk" live application of diagram proposals, with undo and decision log)
- Earlier: 0.0.0 → 1.0.0 (initial ratification from the AtMem AI Architect product summary and action plan)
- Principles added: I–VIII
- Sections added: Product Boundaries, Technical Constraints, Development Workflow, Governance
- Templates: plan-template.md "Constitution Check" is answered against Principles I–VIII; no template edits required
- Deferred: product and umbrella naming (see Open Decisions)
-->

# AtMem AI Architect Constitution

AtMem AI Architect is a locally installed, browser-based AI stack consultant. It guides individuals and
organisations from discovery to a reviewable deployment of an AI solution that fits their
existing systems. It focuses on the AI stack, not on taking over the customer's whole
infrastructure.

## Core Principles

### I. The user stays in control

The agent proposes; the user decides. The agent MUST NOT change the project on its own
authority: every change is a proposal with a visible diff. The user either applies each proposal,
or turns on "Draw as we talk", which applies the architect's diagram proposals as they arrive so the
design evolves with the conversation. Either way every applied change is recorded as a decision,
announced with its diff, and undoable, and the setting can be turned off at any time. Nothing is deployed, provisioned or sent to a cloud account without an
explicit, per-action user approval. Deployment plans MUST be reviewable before any execution.

### II. Honest outputs

Every recommendation, review finding, estimate and generated document MUST separate facts,
assumptions and open questions, and cite sources where a source exists. Cost figures are
estimates with stated inputs and assumptions, never bills or guarantees. The product MUST NOT
invent prices, citations, test results or deployment evidence. Local fixture runs are labelled as
simulations. A confidence score is never treated as proof.

### III. One project model; outputs are generated from it

The canvas, the agent, the review, the estimate and the deployment document all read and write
one structured, versioned project model (components, connections, requirements, decisions,
assumptions). Outputs MUST be regenerated from current project data rather than edited copies.
The project file MUST be exportable, re-importable and editable, and MUST round-trip without
loss of the user's content.

### IV. Local-first and least privilege

AtMem AI Architect runs on the user's machine. The browser talks only to a loopback sidecar. Credentials and
secrets MUST NOT be stored in project files, browser storage or memory events. Cloud and model
access is explicit opt-in, read-only before write, and scoped to the selected provider and
environment.

### V. Sketch broadly, go deep where validated

Users can sketch a broad range of AI workflows across providers from the start. Provider-specific
guidance, cost models and deployment are delivered for one provider first and extended only as
each is validated. Coverage MUST be labelled (sketch-only, guided, deployable); the product MUST
NOT imply complete coverage or validation it does not have.

### VI. Memory is reported, policy-driven and reversible

Project context and decisions persist through AtMem as a headless service. AtMem AI Architect MUST report
relevant changes as events; AtMem cannot discover what it was not told. Changed decisions are
superseded, not overwritten, and keep their history and reason. Time-sensitive statements keep
the date they were made. Deletion happens only under an explicit, applicable policy.
Ambiguous conflicts are flagged for review, not resolved silently.

### VII. A calm, canvas-centred interface

The architecture canvas is central. Information is grouped, and detail is exposed on demand:
high level first, then detail. No dense dashboards of lines and text. AtMem AI Architect has its own
interface and does not reuse the AtMem UI. Interfaces meet WCAG 2.2 AA contrast and work at
phone width without horizontal scrolling.

### VIII. Test-backed increments

Each feature ships with unit tests for its logic, contract tests for any sidecar boundary change,
and a browser smoke test covering its user journey. Behaviour changes need regression coverage.
A feature is done only when its acceptance scenarios pass locally.

## Product Boundaries

- **AtMem AI Architect**: the user-facing workspace and AI stack consultant (this repository).
- **AtMem**: headless memory and governance engine; retains requirements, context and decisions
  across sessions; remains independently available. Accessed through MCP, plugin or integration.
- **Adbot**: the internal agent framework. Its name need not appear in the customer journey.
- **Adflow**: configured agent-run tracing and run-cost visibility. It is separate from, and must
  never be presented as, the estimated cost of the customer's cloud architecture.

## Technical Constraints

- Frontend: React 19, React Flow 12, Vite; framework-free logic modules under `src/` with
  `node --test` coverage.
- Sidecar: Python 3.11+ FastAPI on 127.0.0.1 with strict pydantic contracts (`extra="forbid"`).
- Upstream code (OpenArchFlow, AWS GenAI Solutions Architect Agent, AWS Labs MCP) keeps its
  licence, provenance header and notice entry. New runtime dependencies update the notices.
- Project files carry an explicit format identifier and version, with migrations for every
  earlier version.

## Development Workflow

- Material features use Spec Kit: one numbered directory in `specs/` with `spec.md`, `plan.md`
  and `tasks.md`, created with `/speckit-specify`, `/speckit-plan` and `/speckit-tasks`.
- Unresolved product questions are marked `[NEEDS CLARIFICATION]` in specs and listed in
  `specs/README.md` under Open Decisions; implementation MUST NOT silently decide them.
- Checks before merge: `npm test`, `npm run test:server`, `npm run test:browser`,
  `npm run build`, `npm run notices` when dependencies change.

## Governance

This constitution supersedes other practice in this repository. Amendments are made by pull
request that states the change, the reason and any migration, and bumps the version (MAJOR for
removed or redefined principles, MINOR for added principles or sections, PATCH for wording).
Every plan's Constitution Check answers Principles I–VIII; any violation is justified in its
Complexity Tracking table.

**Version**: 1.1.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-05
