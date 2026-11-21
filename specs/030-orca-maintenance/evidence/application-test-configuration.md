# Current application-test configuration — 2026-11-13

The candidate had no ENGINEERING_VALIDATORS or validation worker endpoint. Registered its existing local Colima engine socket explicitly, without switching the global Docker context. Selected cached immutable SQL image sha256:bafc5723ac59b025d42337e4c965e6d7b89a07da3d18b49a9384cfa70274f8e2, exact linux/amd64 platform and postgresql-local-v1 isolation. No image pull, host mounts, external network, real database or cloud operation.

The Python runner invokes the image-owned disposable PostgreSQL17 fixture and unittest discovery in tests/. Catalog reported available. A real artifact-bound validation job completed with status passed:22 tests,15.873 seconds test time,19.563 seconds total execution; output was not truncated. Includes contract, HTTP, payments, recovery, process replacement and SQL transaction checks. Browser tests were not executed or registered.

Restarted the candidate only after native work was idle. Same app data directory preserved. Local operator JSON and restart launcher remain under ignored .local; private artifact/source/report not committed. See the [configuration guide](../../../docs/architecture/configuring-application-tests.md).
