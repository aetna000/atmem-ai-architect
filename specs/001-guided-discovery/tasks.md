# Tasks: Guided discovery

## Done (release-1 slice)

- [x] T001 Agent skills as data: `agent-skills/discovery/SKILL.md` (behaviour), `topics.json` (7 topics, order, prerequisites, beginner wording, why, if-unsure assumption, what each feeds)
- [x] T002 Workflow skills `agent-skills/workflows/workflows.json`: knowledge assistant, document processing, prediction/forecasting, agentic automation — detection, follow-up questions, first sketch per cloud
- [x] T003 Planner `src/discovery.mjs`: files each answer under the topic just asked; one question per turn; never re-asks; "not sure" → assumption + open question; extraction of usage, data size, budget, cloud, sensitivity; quality statements → measurable requirements; conflicting numbers kept with dates and flagged (FR-002–FR-006)
- [x] T004 Discover view: one open question, Send / Not sure / Why? / Skip, "What I understand so far" editable in the user's words, Sketch it (FR-004, FR-007)
- [x] T005 Connected model gets the same skills (`server/prompts.py`) and the planner's next question as read-only context
- [x] T006 Tests: `tests/journey.test.mjs`, server `SkillsTests`, browser smoke Discover section

## Remaining

- [ ] T007 Import-first start (US2): mark imported components existing and pre-fill current systems; Pulumi regions as assumptions to confirm
- [ ] T008 Unit and period follow-up when a number has no unit ("budget 5000")
- [ ] T009 Refine the question bank from research R2

## Live dictation correction (FR-008–FR-011)

- [x] T010 Record clarified one-way dictation, explicit posting and design-output requirements.
- [x] T011 Add local capture, bounded progressive transcription and cancellation fencing.
- [x] T012 Add authenticated in-memory audio routes and warmed local Whisper worker/setup.
- [x] T013 Verify real generated speech, controller/HTTP/UI regressions and existing checks; keep the baseline Outputs mobile failure distinct.
- [x] T014 Update evidence/limits and the running helper; physical microphone remains unverified.

- [x] T015 Highlight applied diagram changes and focus their area; test targeting, cue expiry, actual viewport zoom and reduced-motion rendering.
