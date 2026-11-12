# Five-stage journey and contrast review — 2026-11-12

Owner-approved flow: Board → Requirements → Choices → Review → Delivery. Remove
separate Design/Implementation workspaces and the eight-section dropdown. Keep useful
engineering/session functions inside Review. This UI work does not resume the paused
native/original28 programme.

Implemented behaviour:
- Visible five-stage navigation. Visits never acknowledge checkpoints or invoke models.
  Working-draft completion colours invalidate when their source requirements change.
- Prominent labelled Projects folder, rename pencil on hover/focus, labelled Start over
  in the menu. Components/layers live on the Board. Expanded navigation reserves canvas
  space and is absent in block detail, protecting its Back/Inputs controls.
- Start from blank chat, Word DOCX/PDF/text/Markdown/images/draw.io, or saved Architect
  project JSON. Dedicated requirement uploads submit to the currently selected Architect;
  missing setup keeps files/draft for connection. Existing attachment limits apply.
  Draw.io plain/compressed pages retain graph identifiers/edges; DTD/entity and bounded
  expansion failures are explicit. Scanned PDF OCR/legacy .doc are not newly implemented.
- Open a saved project or create a new identity from its design. Copy retains requirements,
  geometry, decisions and conversation, but not live execution identities or queued sends.
  Original file/object is unchanged. Copy provenance is retained.
- Choices contains cloud plus country/region. Review contains risks/tradeoffs, cost presets,
  generation and artifact-bound local checks, plus configuration-specific Terraform checks.
  It preserves exact model/effort and durable start/steer/recovery. No extra check-report
  or original-archive downloads compete with Delivery.
- Delivery browses documents/code/PDF and offers one combined project package. Existing
  digest/save/race safeguards remain. Missing implementation routes to Review; a known
  unsaved-project response is a next-step state rather than an opaque retry error. Other
  service errors remain errors. Without engineering, the one package is explicitly design-only.
- JSON keys/values and Terraform tokens have readable light/dark highlighting. React
  escapes every token. Requirements retain a coherent light paper palette inside dark mode.
  Corrected disabled controls/send icon, placeholders, cost-row text, provider badges,
  AtMem fields and Projects button. Existing token definitions and atflow.css were not edited.

Validation:
-571 JavaScript tests, zero skips, including five-stage grouping/checkpoint invalidation and
  immutable copy/no queued replay; production build passes.
-8 attachment tests, including plain/compressed draw.io, external entities and expansion denial.
-Desktop1440/mobile390 whole-app fixtures: navigation sends no model requests, upload reaches
  exact selected model/effort, copy preserves source, JSON highlighting, no sidebar/detail
  overlap, reserved canvas width, no premature package and no browser errors.
-Engineering browser fixture: save failure, exact selection, single start, steering, retained
  draft, reload/recovery/no replay, stale/failed/skipped/zero-test check states, recheck.
-20 rendered view/theme contrast samples,1578 text/control checks: no failures against4.5:1
  normal text/controls and3:1 large text. Disabled controls and placeholders included.
  Specific code, Projects and AtMem checks also pass at both desktop/mobile widths.
-Live5298 preview uses preserved data/settings. Own idle/completed diagnostic preview was
  gracefully restarted with no API/voice keys configured; project bytes and saved session
  identities/status matched before/after.5296 remains available. Final live-load log records
  root/module/canvas errors and blocked writes. Bulk screenshots/logs/restore copies are
  under .local/external-artifacts/five-stage-journey and contrast-review on MEM0.

Limits: browser service/model fixtures are not native generation or cloud acceptance.
The earlier independently qualified native diagnostic is retained; no new native inference,
account plan, deployment, original28 count or release promotion. Automated pricing coverage
still excludes many service charges; presets do not invent prices. Contrast sampling covers
rendered states and is not a claim of full accessibility conformance.

Manual test: open localhost5298, rename via the title, use Projects, expand/collapse the Board
sidebar, open a block and return. Visit all five tabs. Upload a small Markdown/draw.io file
from Requirements after selecting a model; inspect the question and proposed design. In
Choices review location. In Review inspect costs/risks and explicitly generate only when
wanted. In Delivery inspect JSON/PDF and the captured package state. Repeat with dark mode.
Rollback: restore runtime files from the previous Git commit and restart only this preview
with its preserved settings/home. MEM0 before-five-stages retains previous files; do not
remove project data, sessions, artefacts or replace a completed native run.
