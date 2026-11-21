# Implementation Plan: Project model and project file

**Branch**: `002-project-model` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-project-model/spec.md`

## Summary

Introduce a versioned project file (`atforma.project` 2.0.0) as the single durable form of a project, with a migration from the version 1 workbench shape, round-trip preservation of unknown fields, credential refusal, and first-class requirements, assumptions, open questions and decisions with supersession history. The in-browser model gains the new record arrays; the file nests them under explicit sections. The sidecar contract gains a read-only `context` for the architect.

## Technical Context

**Language/Version**: JavaScript (ES2023 modules), Python 3.11+

**Primary Dependencies**: React 19, React Flow 12 (UI only); pydantic 2 (sidecar contract). No new dependencies.

**Storage**: Browser localStorage (autosave, internal shape) and user-held `.atforma.json` files.

**Testing**: `node --test` (model, migration, round-trip, decisions), `unittest` (sidecar contract), Playwright smoke (export → clear → import journey).

**Target Platform**: Local browser + loopback sidecar.

**Project Type**: Web application (Vite SPA + FastAPI sidecar).

**Performance Goals**: Import/export of a 200-component project in < 200 ms in the browser.

**Constraints**: File ≤ 2 MB; ≤ 200 components; ≤ 600 connections; no credentials.

**Scale/Scope**: One project per file.

## Constitution Check

| Principle | Answer |
|---|---|
| I. User in control | Revisions and proposals remain user actions; nothing auto-applies. |
| II. Honest outputs | Assumptions and open questions become records the document must print. |
| III. One model | This feature *is* the model; file is canonical, outputs regenerate from it. |
| IV. Local-first | File stays local; credential patterns refused on import and export. |
| V. Sketch broadly | Model stays provider-neutral; coverage labels deferred to 003. |
| VI. Memory | Supersession with reason and history prepares 006 events. |
| VII. Calm UI | One new Design sub-view (Requirements); detail on demand in block detail. |
| VIII. Tests | Unit + contract + browser smoke listed in tasks. |

No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-project-model/
├── spec.md
├── plan.md
├── data-model.md
├── contracts/project-file.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── project-file.mjs      # NEW: serialise / parse / migrate / credential scan
├── records.mjs           # NEW: requirements, assumptions, questions, decision revision + history
├── engagement.mjs        # cleanEngagement extended for new records; keepEngagement keeps them
├── EngagementViews.jsx   # RequirementsView; DecisionsView gains Revise + history
├── main.jsx              # file open/save use project-file.mjs; Requirements sub-view; block detail lists linked records
└── local-agent.mjs       # sends read-only context
server/
├── contracts.py          # ChatRequest.context (read-only records)
└── architect.py          # context included in the model prompt
tests/
├── project-file.test.mjs # NEW
└── records.test.mjs      # NEW
scripts/smoke.mjs         # export → clear → import, revise decision
```

**Structure Decision**: Keep the existing single Vite app + sidecar. New logic lives in framework-free modules so it is testable with `node --test` and reusable by a future AtMem adapter (006).

## Complexity Tracking

None.
