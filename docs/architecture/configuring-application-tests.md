# Configure application tests

Application tests run against the captured project package in a registered isolated container. They do not run arbitrary commands on the application host. A missing registration appears as **Not configured**.

The local operator registers these settings before starting Architect:

- `ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_ENDPOINT`: an explicit existing Docker Unix socket, such as the endpoint reported by `docker context inspect <chosen-context>`. No global Docker context change is needed.
- `ATMEM_ARCHITECT_ENGINEERING_VALIDATORS`: a JSON array of reviewed validators. Each entry pins `id`, `label`, cached immutable `image`, exact `platform`, `command`, bounded `timeoutSeconds` and optional file `applicability`. Use an image already prepared for the project's dependencies.

For Python tests with a disposable PostgreSQL17 fixture, a qualified SQL image uses `postgresql-local-v1` and the command vector `[/usr/local/bin/python3, -I, /opt/atmem/sql_validation.py, -m, unittest, discover, -s, tests, -v]` (each item is a JSON string). The image-owned fixture supplies an ephemeral database; do not point these tests at a real application database. See [runtime preparation](../../scripts/engine-evaluation/prepare-sql-validation-image.py) and [worker placement](validator-placement.md).

Restart only after generation/checks are idle, retain the same app data directory, refresh the browser and choose **Application tests → Run**. Results bind the exact captured package and registered runtime. Browser tests need their own qualified Chromium runtime/profile; a Python pass does not cover them.

For the current development candidate5306, the operator configuration is retained locally in `.local/candidate-home/operator-validators.json`; `.local/start-configured-candidate.py` restores that registration and the selected Terraform tools on restart. Those machine-specific paths and private check reports are intentionally outside version control. This is local candidate configuration, not a new npm release or a default registration on other machines.
