# AtMem AI Architect specifications

Source: *AtMem AI Architect product summary and action plan* (2026-11-05). Principles: [constitution](../.specify/memory/constitution.md).

## User journey → features

| Journey step | Feature | Status |
|---|---|---|
| 1. Discovery | [001 Guided discovery](001-guided-discovery/spec.md) | **Release-1 slice built** — open, question-by-question onboarding driven by agent skills |
| 2. Design | [002 Project model and file](002-project-model/spec.md) | **Built** — tasks T001–T016 done; awaiting sign-off of OD-4 |
| 3. Review | [003 Architecture review](003-architecture-review/spec.md) | **Release-1 slice built** — 12 provider-neutral rules |
| 4. Estimate | [004 Cost estimate](004-cost-estimate/spec.md) | **Release-1 slice built** — no prices ship; sourced prices only |
| 5. Deploy | [007 Deployment plan](007-deployment-plan/spec.md) | Spec (plan export and Pulumi scaffold exist) |
| 6. Outputs and revisit | [005 Deployment document](005-deployment-document/spec.md) + 002 | **Release-1 slice built** (Markdown) |
| Memory | [006 AtMem project memory](006-atmem-memory/spec.md) | Spec |
| Agent runtime and tracing | [008 Adbot agent and Adflow traces](008-agent-runtime/spec.md) | Spec |

Delivery handoff and progressive estimates: [009 Consulting delivery](009-consulting-delivery/spec.md).

Personalised architect and skills design: [010 AtMem-backed architect](010-personalised-architect/spec.md).

Next integration priority: **006 + 010** — real AtMem context, scoped Memory dashboard, then reviewed specialist skills and tool routing. Runtime implementation is pending; external sources in 010 are discovery candidates only.

## Build order

1. **002** — one versioned project file: requirements, assumptions, open questions and decisions with history. Everything else reads it.
2. **003** and **004** — review and estimate write findings and assumptions into the project model.
3. **005** — the deployment document is generated from the project model only.
4. **001** — remap discovery to application, systems, cloud preference, data, requirements and budget, feeding 003/004 inputs.
5. **006** — AtMem events for decisions and requirements; supersession demo.
6. **007**, **008** — deployment path on one provider; Adbot runtime and Adflow traces.

Action plan items 1 (customer interviews) and 7 (user testing) are research tasks tracked in [research.md](research.md), not code.

## Open decisions

These block parts of the specs and are marked `[NEEDS CLARIFICATION]` where they apply.

| ID | Decision | Blocks |
|---|---|---|
| OD-1 | First target user and first supported provider (AWS, Azure/Foundry, Google, IBM, Databricks) | 003 provider rules, 004 price book, 007 |
| OD-2 | Representative deployment scenarios for testing | 007, research |
| OD-3 | Product and umbrella naming. UI now says **AtMem AI Architect** (working name) | Branding only |
| OD-4 | Project file format and versioning — **implemented as proposed in 002** (`atforma.project` 2.2.0, JSON, `.atforma.json`); confirm or change | 002 sign-off |
| OD-5 | Deployment permissions and how far release 1 automates execution | 007 |

Engineering handoff quality and repeated scenario checks: [011 Handoff quality](011-handoff-quality/spec.md). Implementation and validation results are recorded in [the review log](../docs/HANDOFF_QUALITY.md).

AWS scenario qualification: [012 AWS scenario validation](012-aws-scenario-validation/spec.md), with [live validation procedure](../docs/AWS_SCENARIO_VALIDATION.md).

Native generation: [013 S3 operator access](013-storage-access/spec.md) and [014 authenticated text statistics](014-text-statistics/spec.md).

Loadable AWS qualification archive: [021 Example library](021-aws-example-library/spec.md), with [examples and runbook](../examples/aws/README.md).

Local AWS simulation and hosted worker boundary: [022 Emulation](022-local-aws-emulation/spec.md), with [operator documentation](../docs/AWS_EMULATION.md).
