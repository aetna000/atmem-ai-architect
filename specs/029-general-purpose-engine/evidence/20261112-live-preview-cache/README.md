# Actual preview cache, dark controls and title width — 2026-11-12

Owner screenshots exposed continued disabled Looks good/button contrast and a white,
overlapping Components panel after the earlier source audit. The earlier whole-page
live check only established that the preview loaded; matching source files on disk did
not establish that Vite served current transformed modules. Correct that evidence boundary.

Root cause: frozen preview is under .local/external-artifacts, and Vite's absolute-path
ignore glob **/.local/** excluded the whole workspace from change observation. Cached
main.jsx/CSS stayed old although ?raw and filesystem reads saw current fixes. Proven
before restart: default served main lacked has-component-sidebar and served CSS lacked
.app button:disabled, while raw and disk contained them. This is a preview delivery defect,
not a request for the owner to keep refreshing or redo project work.

Fix: ignore generated directories relative to the actual workspace root. Parent .local
segments no longer exclude source. Preserve generated .local/.venv/examples exclusions.
Restarted only the idle own5298 preview with identical operator settings/home, no configured
API/voice keys; saved project digests and completed session identities/status match before
and after.5296 remains unchanged. Live same-URL served main/CSS now contain the current
sidebar/disabled contrast fixes. Subsequent CSS edit (title width) became visible through
the same transformed URL without a second restart.

Expanded the audit to the actual http://localhost:5298 assets, using an isolated browser
fixture backend so no owner writes, model inference or cloud calls occur. Include expanded
component sidebar, block-detail Looks good and other controls, hover/focus review actions,
all five stages/costs/infrastructure and AtMem/Connections/Projects dialogs in both themes.
28 sampled states/1777 text and control checks pass; disabled controls and placeholders
included; no browser errors. Sidebar is absent in block detail. Dark Components text is
visible on its matching surface. Contrast sampling is not full accessibility conformance.

Project name now measures466px at1440 viewport,136px at390 viewport without document
horizontal overflow. Hover/focus pencil remains. Name/requirements/session contents were
not edited by this check.

Validation:572 JavaScript tests,zero skips; production build. A real Vite regression launches
a copied preview config under a .local parent, warms the transformed CSS URL, changes its
source and confirms the same URL returns the new transform. Unit coverage also checks
normal/.local/external roots and retained generated-directory exclusions. Full earlier UI,
upload/parser and native diagnostic evidence remains separately bounded. No new native
run, original28 acceptance, deployment, voice qualification or automatic pricing expansion.

Manual check: open5298, expand Components in dark mode, open a component and inspect the
Back/Inputs controls and Looks good button. Inspect disabled send and other buttons, then
hover the wider project name. A future frozen-preview update must verify served modules
and actual-address browser state, not only source hashes or root200.

Rollback: restore previous vite.config.mjs and stylesheet from Git; use the preserved
private before-cache-fix files/settings on MEM0. Do not delete project/session data. The
old watch configuration reproduces stale source transforms in nested previews.
