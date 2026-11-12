# Source-validated change plan

## Corrections to the previous review

1. **There is no call ID to pair events.** Architecture events carry only `sequence, kind, text, at, details{attempt, round, tool, success, skillIds, recordCount}`. Drop "merge by call id".
   - Pair a `tool_started` with the next `tool_finished` or `tool_cached` only when it has the same `details.tool` and no other `tool_started` for that tool comes in between.
   - In every other case, render the rows separately.
2. **Use the real states, not invented ones.** The source has `running, response_ready, failed, cancelled, recovery_required, details_unavailable`, with fallback to `turn.clientStatus`.
   - Remove "Recovered" and "Disconnected".
   - `recovery_required` means "outcome unknown after service restart". It does not mean "completed after retry".
   - A retry exists only when `response_repair` is present or `details.attempt > 1`. A higher `details.round` is a pass, not a retry.
3. **No Retry button on architecture turns.** `recordArchitectureTurn` refuses replays. A retry must be a new send through the normal composer.
4. **Elapsed time and step counts are not stored on the turn.**
   - Finished turns: show elapsed only as last `at` minus first `at` after events have loaded.
   - Active turns: show "started 11:31 PM", not a client-side counter. Clock skew between client and server would make a counter fake.
   - Collapsed, never-loaded turns: show only `model · effort · status`.
5. **Build cannot have one row per request.** `steer` adds requests to the same `runId`. Group activity per run.
   - Place the group after the run's starting request.
   - Show steering messages inside it as "Update sent during this run".
   - Never attribute events that fall between steers to a particular steer.

## Changes

**`ArchitectureActivity.jsx`**
- Remove `toReversed()`, the "N model attempts" line, the bordered card title and the "turn N" heading.
- Keep `<details>`, but move Stop out of `<summary>` into a sibling button. Nested interactive content inside a summary breaks keyboard use.
- Polling is currently gated on `open`, so collapsing an active row stops updates. Change the gate to `open || active`.
- Keep lazy loading for inactive turns. Up to 1,000 turns must not all poll on mount.
- Add an `onStop` prop. Pass it only to the newest `submitted` turn. A stale `submitted` turn would otherwise also look active.
- Map these kinds explicitly: `tool_cached` → "Used saved result", `response_repair` → "Fixed a reply-format problem", and handle `pass_started`, `context_*` and `model_checked`.
- A 404 should render as "Details not recorded for this turn", not as an error.

**`architecture-activity.mjs`**
- Add pure helpers `toSteps(events)` (conservative pairing, oldest first) and `turnSummary(turn, events | null)`.
- Do not touch the validators, `merge`, or the stored shape.

**`chat-render.jsx`**
- Remove the "Architecting… Cancel" footer only when an active turn row exists. When `architectureActivityEnabled` is false, or before the turn is recorded, the footer is the only Stop control.
- Wire Stop to `agentAbort.current?.abort()`. This aborts the client request. Don't claim it cancels the work server-side unless that is confirmed.
- Group consecutive unassociated turns into one labelled "Earlier activity, not linked to a reply" block. Keep the turn order and slots from `architectureConversation`.
- Keep the existing `chatScroll.viewport` and `chatScroll.content` handling rather than adding a new stick-to-bottom hook.

**`EngineeringPanel.jsx`**
- Replace the `Engineering progress` `<details>` with run groups built from `events` grouped by `runId`.
- Events without a `runId` go into an "Earlier activity" group.
- `engineeringConversation` entries probably lack `runId` and `sequence`. Verify this in `engineering-client.mjs` before interleaving.
- Move the form below the thread. Keep every gate: `exactSelection`, `hasDesign`, `uncertain`, `contextBusy`, the 80,000-character limit, the localStorage draft, and auto-submit of `buildRequest`.

**CSS**
- Delete the border and background on `.conversation-activity`.
- Delete the nested scroll areas: `.architecture-turns` (max-height), `.engineering-panel details`, and `.engineering-entry pre` / `.engineering-message`.

## Critical caveats

- **Legacy activity shows up inside a request/reply pair.** Unassociated turns take the slot of the next associated turn. That slot is `maxRequestIndex+1`, which sits between that turn's request and its reply, so the legacy turns visually attach to it.
  - Keep the slot. Queued intake means you can't safely move them before the request.
  - Make the block visually distinct: a full-width divider style, not indented like that reply's activity.
  - Don't show "23 steps" until it is loaded. Show "N earlier turns".
- **A generic CSS rule will add a nested scroll.** If activity rows inside `.engineering-panel` use `<details>`, the `max-height:16rem; overflow:auto` rule will clamp them. Scope a reset for those rows, as `details.architecture-work` already does.
- **Tests: report only what was recorded.**
  - Render `finalization_*` text verbatim under "Recorded verification update".
  - Keep "Checks are not independently verified."
  - Never parse that text into pass or fail counts.
  - Engineering events show no `at` field, so show no elapsed time there.
- **Model and effort.**
  - Architecture turn rows show `turn.model` and `turn.effort`.
  - Build runs show `job.model` and `job.effort`. That is session-level and was fixed at `create`.
  - Never label past work with `connection.*`, which is the next selection.
  - The "Deep" label mapping isn't in this source. Reuse it from the header, don't redefine it.
- **"Recover connection" can't simply be hidden.** It is the only way out of `uncertain` (the `starting` state) and out of entries with "Delivery uncertain". Show it inline in those states and keep it in an overflow menu otherwise.
- **Saved histories.**
  - Build restores only `sessions.at(-1)`. Earlier sessions exist but aren't shown, so say so rather than presenting the history as complete.
  - Keep the `activity-error` alert path, which renders messages even when the activity history is invalid.
  - Keep keys of the form `project.id:turn.id`.
- **Announcements are too noisy.** `role="log" aria-live` on the Build conversation reads out whole `<pre>` replies. Announce state changes only.
- **Expanding a row grows content asynchronously** because of the lazy fetch. Anchor the scroll so expanding never moves the view.
- **Quick replies and the "Next reply" chip are not in this source.** Their placement is unverified.
