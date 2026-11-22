# Large consultations and direct drawing

Owner-directed local maintenance: retain full consultation context and make the
native drawing workspace usable without navigating specification forms.

1. Preserve all consultation records through preparation, validation, derivation,
   save/reload and consent-filtered memory sync. Separate model token windows from
   project record counts; never truncate records silently.
2. Keep controlled selection separate from expensive geometry work. Preserve it
   through zoom, pan, property inspection and native layout changes.
3. Provide visible rounded library tabs, a compact Tools control, labelled page controls,
   immediate layer feedback and editable connection contracts.
4. Place Properties in a collapsible left rail across drawing views. Show one selected name
   editor; unique React keys and an isolated selected-record root prevent orphan DOM.
   Keep the global drawing controls in one 44-pixel row. Collapse the entire row with
   a persistent, keyboard-accessible toggle; retain a small restore handle.
5. Double-click an element to enter its drawing interior. Breadcrumbs return to the
   overview; drawing inside does not open specification forms. New elements use free
   interior space while retaining existing geometry and intrinsic label dimensions.
6. Let any drawing vertex receive other elements. Highlight native drop targets;
   dragging inside/outside changes presentation containment atomically with geometry.
   A selected parent must not capture its child's drag.
7. Store presentation parent overrides separately from software ownership. Preserve
   component IDs, parentBlockId, requirements, specs, interface endpoints and sources.
   Saved layouts, editable exports and the Layers tree use actual display containment.
8. Support named visual groups through selection and a context menu; groups can be
   nested, renamed, moved and ungrouped. Retain empty groups and stable frame bounds.
   Snapshot undo/redo state before restoring it, preserving later consultation work.
9. Verify archive/clinic/workshop transfer and negative cycles/identity collisions,
   repeated selections, real native movement, save/reload, native exports and actual
   installed runtime behavior. Synthetic browser checks intercept APIs and use no model.
10. Install a versioned local candidate with private backups and exact previous CLI
    targets. Never restore a backup over concurrent owner saves.

Interfaces: drawingLayouts.pages stores geometry, groups stores named page membership,
and parents stores explicit display-parent overrides, including null for root placement.
These fields are validated and survive project serialization. They do not rewrite the
shared engineering model. Mermaid describes model records; it does not invent records
for visual frames. Sequence/stage views retain their chronological semantics.

This is a local maintenance candidate, not model training, public npm publication or
a deployment qualification. Keep private client files and evidence outside public source.


## Owner-reported unresponsive canvas, 2026-11-22

Profile the actual diagram locally, retaining private content only in local evidence.
Keep rendering work off the chat path: index nearby parallel routing lanes and painted
segments, batch numeric label placement, and bound automatic route repair. Run the
complete diagnostic pass and retain unresolved overlaps/crossings; do not manufacture
an export/readability pass. Preserve model records, geometry and connector identities.
Use synthetic dense-diagram latency and negative geometry cases, plus comparison with
baseline route and overlap diagnostics. Wasm is a last resort after measured algorithmic
improvements; browser geometry and remote model latency are separate measurements.


## Layout conflict recovery, 2026-11-22

Reset removes manual geometry and restores the original drawing; it cannot fix an
already-conflicting baseline. The warning must offer measured arrangement instead.
Try bounded alternative spacing/directions, check the rendered result, and commit an
improvement as one undoable presentation change. Keep records, contracts, hierarchy
and rotations; preserve ordered sequence/stage layouts. Reject out-of-bounds candidates.
Make individual conflicts focus their affected elements. Retain unresolved conflicts
and the verified-export gate; do not imply arrangement establishes architecture quality.


## Visible waiting feedback, 2026-11-22

Show a waiting icon for each user-facing asynchronous action, from application startup
through model/connection calls, imports/exports, source reading, saves, memory, checks,
generation, delivery and local layout work. Share one pending-work lifecycle, mark the
clicked control and active dialog, and retain an accessible global status when those
controls disappear or the toolbar is collapsed. Reflect owned long-running job state
and streaming work until it settles. Keep observation polling quiet. Complete, fail,
cancel and unmount must release their own indicator without clearing concurrent work.
Yield before expensive local work so the indicator can paint. Do not add a blocking
screen or claim progress/acceptance merely because a request has started.
