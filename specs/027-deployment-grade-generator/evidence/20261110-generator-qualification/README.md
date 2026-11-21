# Generator qualification evidence — 2026-11-10

`receipt.json` records source-file and evidence hashes, tool versions and boundaries.
The worktree hashes identify tested changes that were not yet committed when captured.

- `qualification.json` and `terraform-fixtures/`: fresh generated AWS/Azure/GCP/IBM container configurations, real provider schema validation and generated mock-plan logs. No apply.
- `*-tests.log`, `*-server.log`, `*-build.log`: exact unit, integration and build output.
- `architect-generator-delivery-browser.log`: browser delivery/export regression; model/session/prices are fixtures.
- `architect-export-receipt-verified.json`: real local API validation result whose file digests match `architect-receipt-files.json` exactly.
- `*-tflint.json`: independent core lint results for the preceding four-cloud container fixture run; these are not the later fresh-fixture receipts.

These checks do not establish a deployed system or completion of the full implementation roadmap. No cloud deployment was performed.
