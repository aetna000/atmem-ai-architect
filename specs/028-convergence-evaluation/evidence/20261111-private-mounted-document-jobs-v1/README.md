# Mounted private document jobs — local evidence

Implemented a bounded file-only request/result mode for fresh parser jobs, with
exclusive result publication, exact byte/MIME/request binding and no routine text
in parser stdout. The common executor/cache forwards live source/company/job checks.

Final qualifications:
- Linux parser: 26 tests and 23 qualification steps; actual DOCX and scanned PDF
  each execute in a new restricted container with private readonly input mounts.
- PostgreSQL 17 and 18: 122 actual local SQL/API/queue/auth/cache/operator tests per
  version, including membership loss before a per-file launcher releases input.
- Separate native API/worker configurations for all four providers: 52 assembly
  checks; 8 actual mounted Linux extractions and 16 verified answer releases.
  Models/company/source HTTP are controlled fixtures, not live cloud accounts.
- Local job log driver disabled; cancellation is injected only after inspect
  observes the parser running; container and volume cleanup is independently checked.
- 79 policies and 347 JavaScript regressions pass.

Retain the first mounted fixture failure: chmod after chown correctly failed under
CHOWN-only capabilities. The repaired fixture changes permissions first; it does
not grant more privileges. Its reconstructed original source matches the recorded
SHA-256. The earlier passing assembly lacked an explicit Running observation for
its cancellation claim; preserve it and its two original files as weaker evidence.
The final assembly adds that actual state observation and reruns all four configs.

No provider-native parser launcher, complete export/case, cloud plan/deployment or
security acceptance is established. New exact parser security scanning was not run;
prior dependency findings remain unresolved. Native transport/IAM/scoped transfer,
key/recovery/retention and all-four complete exports remain before private case
qualification. Final repaired 28-project and held-out evaluation remains unfinished.
The local Docker fixture is not a production socket integration.
