I need to be upfront about one limit first. I found the brief (`request.txt`) and all three screenshots: `design-desktop.png`, `design-mobile.png` and `build-desktop.png`. I could not find the source files. My only tool here can't list a directory, and about 40 likely filenames all came back missing. So everything below is based on the screenshots and your brief. The change map uses component roles, not file paths. If you tell me the filenames, I'll tie it to the actual code.

---

## 1. The three main problems

**A. The activity has replaced the conversation.** In Design (desktop and mobile), the chat panel shows no request and no answer. It shows one bordered "Architect activity · turn 1" card that fills the whole panel. On mobile it scrolls inside the panel's own scroll, and the next thing below it is the composer. The card's title is half hidden under the sticky "Design context" strip. "Working" status appears in four separate places: the header chip, the card ("exact-model · high" / "Working"), "2 model attempts recorded", and the "Architecting… Cancel" footer. The same effort setting is labelled two ways ("Deep" in the header, "high" in the turn). Yes, this is still a pile of run cards, just moved into the chat.

**B. The event list is a raw log that reads backwards.** Newest-first inside a chat that reads top to bottom means "Evidence was unavailable" appears *above* "Looking up supporting evidence". The start and the result of one lookup are two separate rows. Every row has the same timestamp (11:31:41 PM), so the timestamps add nothing. Retry internals like "Model attempt 2 · pass 2" and "Correcting a response-format problem" are the most prominent text, and a nontechnical user will take them to mean something broke.

**C. Build is a form, not a session, and it works nothing like Design.** The composer sits at the top, history is hidden in a collapsed "Engineering progress (0)", and no conversation is visible. It says "Working · gpt-6.1-sol · high" while showing 0 progress, which contradicts itself. "Recover connection" and "Stop work" are always visible even when nothing has failed. Context and status are separate disclosure blocks.

## 2. Recommended design: one quiet activity row per turn

Every turn reads in chat order: **request → activity row → answer**. The activity row is a single, muted line with no card border. Steps appear only when you expand it.

```
 ┌ You ─────────────────────────────────────────┐
 │ Keep the catalogue but check integration…    │
 └──────────────────────────────────────────────┘
  ◌ Working · 0:42 · Looking up engineering sources   [Stop]  ▸
  (answer streams here when it arrives)
```

**Collapsed row, by state.** Each state has an icon and a text label, so colour is never the only signal.

| State | Collapsed row | Default |
|---|---|---|
| Active | spinner · "Working" · elapsed time · **latest step text** · `Stop` | collapsed (the latest step is already in the row) |
| Completed | ✓ "Worked for 1m 12s · 5 steps · exact-model · high" | collapsed, muted |
| Recovered | ✓ "Completed after a retry · 1m 30s · exact-model · high" | collapsed |
| Failed | ⚠ "Stopped: couldn't reach engineering sources" · `Retry` | **expanded**, failed step highlighted |
| Cancelled | ■ "Stopped by you after 0:31" | collapsed |
| Connection lost | ⚠ "Connection lost" · `Recover connection` | collapsed |

**Expanded steps:**
- **Order:** oldest at top, newest at bottom, so the turn reads in the same direction as the chat. I'm deliberately reversing your newest-first choice. The collapsed row already makes the latest progress easy to find, so the list doesn't need to.
- **One row per action:** a start/finish pair merges into one row that updates in place, e.g. "Looked up engineering sources — evidence unavailable".
- **Plain-language retries:** "Retried after a formatting problem (attempt 2)" is one quiet row, not a heading.
- **Timestamps:** show elapsed offsets (+0:04) only when they differ. Show the full time on hover or focus.
- **Content:** public model messages ("I will preserve the catalogue…") and observed tool results only. No prompts, no reasoning.
- **Tests:** shown only as observed, e.g. "Ran tests — 12 passed, 1 failed", or "Ran tests — result not reported". No progress percentages.
- **No nested scroll box:** the list sits inline in the chat. One level, with a 1px left rule.

**Model and effort:**
- Each turn shows the exact model and effort it *used*, with one shared formatter.
- The header chip becomes "Next reply: exact-model · Deep (high)" so the two contexts don't get mixed up.
- The separate "Architecting… Cancel" footer goes away; Stop lives on the active row.
- The quick replies (Not sure / Why? / Skip) are hidden while a turn is active.

**Auto-scroll:**
- Follow new content only if the user is within about 80px of the bottom.
- Otherwise show a floating "↓ Working · Looking up sources…" pill that jumps to the latest content.
- Expanding or collapsing a row must never move the scroll position.

## 3. Old history without request/reply links

- Old messages render as normal chat bubbles with **no** activity rows.
- Directly after the last old message, before the first tracked turn, add one collapsed block:
  `◷ Earlier activity · 23 steps — recorded before activity was linked to individual replies ▸`
- Expanded, it lists every event oldest to newest, grouped by day, with real timestamps. Nothing is dropped and nothing is attached to a specific answer. It is never split up or mixed in between messages by guessing.

## 4. Same pattern in Build and Design

Both use the same conversation component.

**Build becomes:**
- **Header line:** "Build outcome · Knowledge website", plus a "Return to Design" link and an "Architecture context · 0 need review" chip that opens the current context content.
- **Thread:** implementation requests → activity row → reply, exactly as in Design.
- **Composer:** pinned at the bottom, same as Design. Empty state: "No build requests yet. Describe what to implement."
- **Raw event list:** removed as a separate view. Events tied to a turn go into that turn's steps; untied events go into the "Earlier activity" block.
- **Recover connection / Stop work:** appear only on the row whose state needs them.

**Design keeps its canvas and side panel**, with these fixes:
- The header shrinks to one line: title, "Next reply" chip, and the Draw as we talk / Design context / Skill items as small chips.
- The sticky overlap is fixed.
- On mobile, the chat gets the full sheet height with a single scroll area.

## 5. React/CSS change map

- **`TurnActivity` (new, shared):** a `<button aria-expanded aria-controls>` summary row. Stop / Retry / Recover sit *beside* it, not nested inside. The steps list renders as `<ol>`.
- **`toPublicSteps(events)` (selector):** merges start/finish pairs by call id, turns retries into "Retried…" steps, sorts oldest first, and keeps only public messages and observed tool summaries. Stored history is untouched.
- **`deriveTurnStatus(events)`:** returns active / completed / recovered / failed / cancelled / disconnected, based only on observed events.
- **`formatModelEffort(model, effort)`:** one exact label, used everywhere.
- **`LegacyActivityBlock`:** placed at the old/tracked boundary.
- **`ConversationThread` (shared by both views):** messages plus a `TurnActivity` between each request and its reply, a `useStickToBottom` hook plus the jump pill, and one `aria-live="polite"` region that announces state changes only (started, finished, failed), not every step.
- **Design panel:**
  - delete the bordered turn card, the "N model attempts recorded" header and the "Architecting… Cancel" footer
  - make the context strip non-overlapping
  - hide quick replies while a turn is active
- **Build view:**
  - replace the form layout with header + `ConversationThread` + bottom composer
  - remove the "Engineering progress" list and the always-visible recovery buttons
  - turn the context block into a chip
- **CSS:**
  - `.turn-activity`: no border or background, 13px muted text, single-line ellipsis when collapsed
  - `.turn-steps`: one 1px left rule, wrapping text
  - status icon plus colour tokens, with `prefers-reduced-motion` stopping the spinner
  - below 480px, timestamps move under the step text instead of a right-hand column

## 6. Acceptance checklist

- [ ] Every tracked turn shows the request, then one activity row, then the answer, with no bordered card.
- [ ] While active, the collapsed row shows the elapsed time and the latest public step. Stop is on that row and nowhere else.
- [ ] Expanded steps are oldest first, a start/finish pair is one row, and there are no duplicate identical timestamps.
- [ ] Failed turns open expanded with a readable reason and Retry. Recovered turns say "Completed after a retry". No test result appears unless it was observed.
- [ ] The exact model and effort used appear on every turn with one label format. The header shows the next-reply selection.
- [ ] Old activity is in one "Earlier activity" block, complete and in order, and not attached to any answer.
- [ ] Build and Design render the same component. Build has no separate raw event list, and its composer is at the bottom.
- [ ] Mobile (390px): one scroll area, no nested scrolling, the row fits on one line, quick replies hidden while active.
- [ ] Keyboard: Tab reaches each row toggle and its action buttons, Enter/Space toggles, focus stays put, and the screen reader announces the expanded/collapsed state.
- [ ] Auto-scroll follows only when the user is at the bottom; otherwise the jump pill appears. Expanding a row never moves the scroll position.
- [ ] No prompts, reasoning or credentials appear in any step text (check against the fixtures).
