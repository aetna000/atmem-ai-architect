# Azure invoice operating jobs checkpoint

Native Microsoft.App/jobs@2025-07-01 definitions now deliver initialize, maintain
and monitor in the owned private Container Apps environment. All jobs are Manual
before release; initialize remains Manual when daily/hourly schedules are enabled.
Replica completion/parallelism is one, native retries zero, replica timeout 900s.
The dedicated SQL Entra administrator identity is available only to main containers;
ACR pull identity lifecycle is None. No model/object/accounting authority, SQL
password, job-start permission or application grant is added to API/worker.

Native start accepts template overrides, so job start is treated as privileged
access to operator identity, never a chat/API/model capability. The runbook and
exact nonsecret Terraform start URL outputs give an authorized operator concrete
commands without guessing resource names. Bootstrap/membership/secret population
and actual operating-log acceptance precede application release.

Azure Monitor routing and both dedicated current log categories are emitted with
a regional 30-day workspace. Queries use ContainerAppConsoleLogs/SystemLogs, not
legacy _CL tables. Count-only missing-success/failure/platform warnings go to an
existing reviewed Action Group, whose policy/recipients/delivery are preserved
external operating inputs. Fresh-table alert validation is deferred only during
manual bootstrap; scheduling/application release require native query validation.
This flag/configuration is not proof any Azure query executed locally.

11 native schema/mock plans pass. The actual Linux image runs 12 checks on each
owned PG17/18 fixture: three exact native previews; actual Azure SDK fresh token
requests/full-TLS database settings and wrong-identity refusal using loopback fake
metadata; scripted six-column Entra mapping over real role creation; owned SQL
bootstrap/retry, monitoring/retention and runtime audit-deletion denial. Native
Entra mapping/authentication itself is not implemented by stock PostgreSQL and is
NOT claimed. Exact API startup/denial and five restricted queue cases also pass.
82 API/operator, 308 JS and 208 server checks and build pass (known chunk warning).
The generalized image qualifier still passes nine checks on the previously frozen
AWS image/package; see the prior operating-jobs checkpoint for those native inputs.

One harmless EOF blank line was removed from the shared configuration module while
sources were thawed; this Azure image/receipts bind the new exact bytes. Historical
AWS receipts still bind their original bytes and are not rewritten or promoted.

The exact Azure image scan retains 47 high findings, zero critical and no reported
fixes in cached metadata. Open findings are not security/production acceptance.
Primary documentation observations, exact generated package, immutable receipts,
raw logs and source snapshots are included; manifest.json binds their bytes. No
private fixture password/nonce/dump is present. No cloud operation was performed.

Next: Google/IBM native operating wrappers, then full state/Spec Kit/registry and
complete four-provider invoice conversations. Zero complete medium cases counted.
Remaining families, full 28-case and held-out acceptance remain unfinished.
