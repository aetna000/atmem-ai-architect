# UI follow-up validation

- `npm run build` passed; the existing bundle-size advisory remains.
- `npm test`: 585 passed. No engine coverage, numeric calculation or acceptance checks were weakened.
- `node scripts/checklist-smoke.mjs`: an available estimate with an excluded component shows Estimated without a warning icon; pending feedback and pointer/wait cursors still work.
- `node scripts/delivery-navigation-smoke.mjs`: actual Chromium, 20 synthetic storage components, navigation measured at 89 ms. Entering/re-entering Delivery made zero PDF font requests. Explicit export loaded the font once and produced real PDF/PNG/SVG bytes.
- The same browser case verified the implementation ZIP flow: captured source preserved, design-documents PDFs/diagrams included, and prefixed PDF preview works in the explorer. These are real frontend/archive paths with synthetic backend fixtures, not cloud or model tests.
- `node scripts/project-checks-smoke.mjs`: application Run is disabled with “Generate project files first.” tooltip before generation. Terraform Run starts only Terraform; after synthetic files/validators appear, Application Run starts only application validation.
- The isolated managed local candidate at http://127.0.0.1:5306 serves the rebuilt frontend. Existing server jobs/data are retained; refresh the page to load the updated UI.

Price exclusions remain in source data and exports. A normal Estimated label means an estimate is available, not full cost coverage or project acceptance. Mixed currencies still require correction.
