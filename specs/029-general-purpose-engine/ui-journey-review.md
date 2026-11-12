# Owner workflow review — 2026-11-12

Scope: the owner's localhost:5288 experience, including Design/Build, navigation,
local checks, memory and delivery. This is a review and implementation contract;
the complete journey repair has not shipped. Preserve the existing visual styling.

Evidence: read-only real browser check on5288 found one React Flow canvas and no
page errors, failed requests, HTTP failures or blocked writes. GETs of its served
main, EngineeringPanel and EmulationPanel confirm the legacy Build outcome,
mentoring, automatic-retest, question and JSON-report controls. Source tracing
below explains behavior; no model request, local test run, download or owner
project mutation was performed during this review. Owner-reported inert clicks
are not claimed as independently reproduced. Uncommitted5285/source clarity fixes
must not be represented as present in frozen5288.

## Findings and required changes

| Priority | Finding and code evidence | Required behavior |
|---|---|---|
| P0 | Navigation has multiple competing authorities: journey stage, mode, designView and separate Build workspace (`main.jsx`, `journey.mjs`). The current step comes from saved checkpoints, while a click can change only the displayed view. | One navigation state owns displayed destination, current step and next action. Completed/revisitable stages remain reachable; future stages show their prerequisite and a way forward. |
| P0 | Sketch & document opens Requirements; Board has no equivalent named journey destination. Options and Design choices split alternatives from accepted decisions. | Board is the persistent design workspace. Requirements and one Choices panel belong to it. Choices shows alternatives, tradeoffs, accepted decisions and unresolved choices together. A user may begin with a constraint/choice or a requirement; neither input order is mandatory. |
| P0 | Country/region is a chat prompt on the Board, not a discoverable destination. Later Review/Costs/Delivery destinations can be immediately redirected by availableModes. | Expose cloud, country/region, infrastructure, review, cost and delivery in a consistent design checklist. Selecting a destination opens its named content. Never silently bounce to another view. Record decisions in structured project state with a visible next action. |
| P0 | Separate numbering/text arrays and state transitions permit the step label and selected content to disagree (`main.jsx` journey-map versus `journey.mjs`). | Define stage identity, label, order, destination, availability and completion once. The menu, heading and next action all consume that definition. Verify the reported cloud/region number mismatch with a fixture; source review establishes the competing-state risk, not its exact reproduction. |
| P0 | Build outcome renders before a job/artifact exists; Build this design opens a second workspace containing context records, a second instruction form and engineering controls (`EngineeringPanel.jsx`). | A single Implement and check action starts authorized work or opens one clearly stated setup step. Show queued/running/blocked/finished status in the project conversation. Outcome is reserved for an actual captured artifact and its checks. Keep optional instructions and technical mappings in details. |
| P0 | Local emulation/compiler output and native engineering artifacts use separate paths. A missing compiler implementation can coexist with native engineering work. Merely renaming the play control cannot reconcile them. | Select an explicit current artifact, show its design revision, run its applicable checks, and attach results to that same artifact. If implementation is missing, offer Implement and check as the primary action. Do not run a known-impossible test. |
| P1 | The BrainCircuit action means different things in the journey and test panel; the latter toggles mentoring, not operational monitoring (`main.jsx`, `EmulationPanel.jsx`). | All consequential actions have visible text. Separate design assistance from actual configured runtime monitoring. Remove the mentoring toggle from the main path; explain optional automatic assistance in settings. |
| P1 | Auto-retest is an unexplained two-round control. Stop waiting only aborts the browser request; it does not stop the server worker (`useEmulation.jsx`). | Explain any retry behavior where results appear. Keep the bounded limit internal or in optional settings. Label waiting cancellation accurately and show that server work may continue. |
| P1 | Question/correction buttons dispatch largely similar assistance. For non-model guidance, repeated identical assistant text is deduplicated (`discussEmulation`); a repeated click can appear inert. | Use one Ask Architect about this result action that opens/focuses the conversation with the actual finding. Provide visible response/busy/error feedback and a way to type the user's own question. |
| P1 | Report download emits JSON, while Outputs emits a Spec Kit/design/Terraform bundle and Build emits a separate native ZIP (`EmulationPanel.jsx`, `OutputsView.jsx`, `EngineeringPanel.jsx`). | One primary Download handoff package action previews contents and exact provenance. Include requirements, design decisions, Spec Kit tasks/plan, implementation/infrastructure when supplied, checks, limitations and run instructions. Retain raw JSON under Technical details as Download check report (JSON). Do not claim native files and compiler files are already one coherent artifact. |
| P1 | Outputs embeds EmulationPanel without onBuild, so the implementation next step can degrade to a repair-task download even when engineering is available elsewhere. | The same missing-implementation state offers the same implementation action from Board, checks and delivery. |
| P1 | AtMem exists in the menu but is difficult to discover. Shared expertise preload and personal/project memory are different capabilities. | Keep visible AtMem access and explicit on/off/unavailable feedback. Expose relevant memory provenance in the conversation. Ship versioned, reviewed expertise separately from private session/project memory; do not claim the full preload is implemented. |
| P2 | Stale journey prompts still say native IaC covers S3 only; legacy review text points to particular templates (`journey.mjs`, `main.jsx`). | Derive capability explanations from current engine/artifact evidence. Remove obsolete hardcoded support claims without loosening missing-work gates. |

## Intended journey

1. **Design** — Board and conversation, with Requirements and Choices alongside
   the design. An explicit checklist covers scope, existing systems/ownership,
   cloud, country/region, infrastructure/connections, risks and cost assumptions.
   Users may revisit these without losing their place or creating model work just
   to navigate. Unknowns remain visible; required business choices stay questions.
2. **Implement and check** — one primary next action and one progress stream.
   Generate the package, run applicable local checks on its captured artifact,
   explain failures, and show the targeted repair action. A passing local check
   is not cloud deployment or operating monitoring. Keep regional/provider and
   review safeguards; visibility of future steps does not mark them completed.
3. **Delivery** — show what was produced, which requirements are covered, what
   passed, and what remains. Offer one plainly named ZIP and a preview of its
   requirements, Spec Kit, implementation/infrastructure, evidence and runbook.
   Design-only output remains downloadable with an explicit incomplete status.

## Implementation order and acceptance

First reconcile navigation definitions and artifact/check identity, then simplify
the controls and delivery surface. Preserve existing models, ownership, projects,
drafts and sessions. No CSS redesign, cloud access or automatic run merely from
opening a page. Keep current narrow clarity fixes; do not multiply competing labels.

Acceptance requires browser fixtures for fresh design, preselected cloud/region,
revisiting earlier decisions, incomplete requirements, missing implementation,
waiting for model setup, running work, failed/stale checks, captured artifact and
download. Desktop/mobile must show matching stage/destination/number and a clear
next step. Confirm clicks have a visible result and opening navigation sends no
model request. Independently unpack the offered ZIP, match its artifact receipt,
requirements and check results, and follow its run instructions. Static rendering
and mock browser fixtures alone cannot establish the complete native journey.
