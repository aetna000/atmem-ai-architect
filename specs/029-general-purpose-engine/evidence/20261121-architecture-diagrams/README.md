# Shared diagram authoring and verification

The drawing engine supports 28 diagram types from a shared semantic model.
Private client documents, review screenshots and handoff packages are maintained
in restricted storage and are not shipped as public examples.

The public regression uses a synthetic clinic referral composition to exercise
Board plus all 28 notations. This tests rendering transfer, not clinical expertise.

## Rendering and interaction contracts

- Compact titles and measured wrapping; complete properties stay in inspectors.
- Numbered connections bind to stable IDs, endpoints and full descriptions.
- Obstacle routing, separate lanes, group bounds and native glyph checks.
- Editable drag, resize and rotation with persisted page-specific presentation data.
- Blank-canvas drag, Space-drag and middle-mouse panning; wheel/pinch zoom.
- SVG and editable XML share verified waypoints and numeric-label positions.
- Hidden canvases defer checking; unreadable exports report affected records.

## Reproduce

```sh
npm test
npm run build
READABILITY_STRICT=1 node scripts/diagram-readability-check.mjs URL project.json
READABILITY_STRICT=1 node scripts/diagram-export-check.mjs SOURCE_URL project.json
node scripts/drawing-interaction-check.mjs URL project.json
```

Browser checks stub writes and jobs. The source export server must disable HMR.
Routing has a 150,000-coordinate-cell budget and bounded perimeter correction.
Large views require element focus or panning; Fit provides an overview.

Checks establish rendered geometry and scoped mouse interaction behavior. They
do not establish architecture completeness, mobile manipulation, physical Safari
behavior or deployment qualification. Owner acceptance remains separate.

Manual card: select and drag a shape, resize and rotate it, pan the canvas, open
Details & connections, save/reopen, then reset the page layout. Requirements and
contracts remain independent of presentation edits. Roll back using a prior
installed package; preserve local project storage and private evidence.
