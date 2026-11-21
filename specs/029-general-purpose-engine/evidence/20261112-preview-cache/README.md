# Restore live preview module consistency

Owner reported5285 not working. Root HTML/main/API/session all returned200, but an actual read-only root browser observation found a blank root and missing EarlierArchitectureActivity export. Frozen files already contained that export; Vite served an older cached module because .local is excluded from its watcher. Prior component fixtures and a separate fresh Vite suite did not verify the existing preview's complete module graph. This was an activation verification gap.

Cache-bust the live main imports for ArchitectureActivity.jsx/architecture-activity.mjs, the activity module's matching helper import, and the root main URL. No new activity behavior, CSS, layout, backend restart or project write. Restarting this frontend child alone would cause scripts/local.mjs to terminate its backend sibling; that route was deliberately avoided.

The new reusable read-only preview-load check verifies the actual complete page and canvas, not only status200 or isolated components. It allows read-only GET and model-catalog POST requests; blocks all other API mutations. Real5285 browser now reports no page/network/HTTP errors, canvas1, root text717, zero blocked writes. This is page availability, not application implementation or full-system acceptance. No inference or owner project mutation.

Reproduce: `node scripts/engine-evaluation/check-preview-load.mjs http://localhost:5285`. Refresh the browser to load the new entry URL. Rollback: restore three files from `.local/external-artifacts/preview-module-cache/v1/before` (restores the previously broken cached-import graph unless cache is independently cleared). Existing backend PID59742 remains running. No backend/data rollback.

Future frozen frontend activation must include this whole-page check as well as affected behavior checks. Prior missing-export observation retained in before-v1.json. No new release or original-case qualification.
