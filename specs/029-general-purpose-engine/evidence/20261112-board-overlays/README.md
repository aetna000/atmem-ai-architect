# Dismissible onboarding and usable component picker

Owner screenshot: on an empty Board, the welcome card covered the component picker.
Neither surface offered a visible close action. Picker z-index6 was below welcome10
and component sidebar15. This is an independent empty-board interaction, not another
contrast or engine-generation issue.

Fix: welcome has an explicit close button; remember dismissal by project ID in bounded
browser UI preferences (latest64 IDs), separate from project/requirements/AtMem memory.
Hide it while the picker is open. Start chatting also dismisses it. Picker has an explicit
close button, keeps Escape, and sits above other Board overlays with viewport bounds.
Interacting with its filters/search no longer collapses the component sidebar. Selecting
a block closes the picker normally. No project content is deleted by dismissing a card.

Checks: production build passes. Source and actual http://localhost:5298 assets each pass
four browser cases (1440/390 × light/dark): picker receives pointer hits above sidebar,
welcome absent while selecting, filters remain usable, close and Escape work, welcome
dismissal survives reload, empty project remains empty, and PostgreSQL can be selected
and added. Browser API/model responses are mocked; zero inference requests, browser
errors or owner writes. Actual-address run establishes served UI behaviour after the
previous frozen-preview-cache incident. Earlier fixture attempts corrected an accessible
name expectation and a concurrent build/HMR interruption; stable runs pass.

Manual check: on an empty Board open Components → Add component; search/filter and
close with X or Escape. Dismiss the welcome card and reload. Reopen the picker and
add a component; it should be visible and usable above the Board controls.

Latest5298 frontend was hot-updated through the fixed workspace-relative watcher;
backend/settings/project sessions were not restarted or edited.5296 remains unchanged.
No CSS token/atflow.css edits, native inference, pricing/cloud/voice qualification,
original28 promotion or resumption of the paused programme. Bulk screenshots are on
MEM0 in .local/external-artifacts/board-overlay and live-board-overlay.
