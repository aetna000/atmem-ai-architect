# Architecture harness qualification — revision 2

This snapshot supersedes the preceding generator-qualification snapshot for the
source hashes recorded in `receipt.json`. Historical evidence is retained unchanged.
File hashes identify exact source and evidence; source changes invalidate these results
for the changed files. UTC wall-clock timestamps are recorded without rewriting them
to match the logical task date.

- JavaScript tests and build: local generator/UI regressions; bundle-size advisory remains.
- Server tests: real local test suite including AtMem integration and stateful emulation.
- Four-cloud fixtures: real provider initialization/schema checks and 16 provider-mock
  tests. No credentials, account plan, apply or supplied-image runtime validation.
- Validation API: independent generation consistency, schema, core TFLint and mock checks
  for the exact GCP files in validation-files.json. TFLint has no provider plugins here.
- Export browser: API result replayed in an isolated browser; verifies downloaded ZIP
  receipt against every actual file. All other API responses are fixtures.
- Emulation browser: fixture model, real local emulator API, real generated runtime;
  12 checks including exact ZIP/report hashes and stale evidence invalidation.
- Reasoning observations: three real model calls with AtMem context. Not independently
  scored and not evidence of superiority or application implementation. Responses
  appended questions despite instructions requesting none. A discovered security-skill
  selection gap was fixed afterwards and tested locally; observations predate that fix.

Existing code can now explicitly target a new private container deployment while an
existing deployment remains a reference. Unsupported connections/application behavior
remain explicit work. This evidence does not complete the broader generator roadmap.
No cloud deployment or training occurred.
