# Chunked validation — 2026-11-13

- Failure cause: 253,165-byte validation JSON exceeded the generic250,000-byte POST limit. Terraform had not started.
- Authenticated 128 KiB chunk transport preserves complete UTF-8 bytes and verifies total size/SHA-256. Bounds and durable-project limitations are in the plan.
- `npm test`: 587 passed, including Unicode/checksum/progress and interrupted-transfer client tests.
- `python -m unittest server.tests.test_request_uploads server.tests.test_terraform`: 11 passed, qualified developer Python. Covers route authentication, large envelopes, one-use, order/size/checksum/expiry/quota/cancellation and rejection of client executable files before validator invocation.
- Focused Chromium ProjectChecks regression and frontend build passed.
- Live candidate5306 restarted only with native session idle, preserving its data. It now uses the existing Terraform1.17.1 macOS arm64 binary and provider mirror from the qualified developer installation through local environment settings. No change to the published npm app or historical exports.
- Actual current saved design: full253,165-byte request uploaded at52%/100%, then independent generation consistency, provider initialization and Terraform schema validation all passed. This is validation of the saved-design Terraform draft, not the native application package, account plan or deployment. Private project and raw report remain local and are not included in source control.
