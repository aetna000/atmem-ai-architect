# Google invoice operating jobs checkpoint

Native GA Cloud Run jobs now deliver fixed initialize, daily maintain and hourly
monitor commands through the separate ops SQL identity and private VPC path. One
task/parallelism one, zero native retries and 960-second task limit bound execution.
The pinned maintained proxy adds startup/quit endpoints only on loopback, private
IP, lazy refresh and graceful termination. Operator work waits up to 30 seconds on
/startup; it always POSTs /quitquitquit after work or invalid metadata. Failed proxy
shutdown cannot emit an ok receipt. Cold SQL connection transport failures retry
at most three times with fresh credentials; authentication/schema failures do not.

Two actual immutable images sharing a network-disabled namespace verify proxy
startup and zero-exit shutdown after successful work and the real CLI's invalid
metadata failure path. Only the proxy credential is fake. Successful SQL work is
substituted solely for this lifecycle isolation, not represented as Cloud SQL proof.
Separate exact-image checks on PG17/18 exercise actual bounded metadata HTTP against
an explicit loopback transport, native-profile precreated IAM marker admission over
real SQL, owned bootstrap/retry, retention/monitoring and runtime audit denials.
Stock PostgreSQL/root fixtures do not establish managed Cloud SQL IAM privileges.

The separate Scheduler caller has invoker scope only on maintain/monitor, no SQL,
bootstrap or override grant. OAuth uses exact owned RunJob endpoints and bounded
retries; schedules remain paused until the operating phase. Application release
requires operating flags. The emitted Python CLI helper reads nonsecret Terraform
outputs, validates the destination/names and previews before explicit --execute.
It uses gcloud --wait without shell interpolation, overrides or exposed tokens.
Five actual helper/fake-CLI process tests exercise preview, fixed execution arguments
and malicious/duplicate input refusal. No real account CLI execution occurred.

Project/region-owned count-only log metrics cover failed/attention/backlog work and
platform/Scheduler ERROR logs. A two-hour monitor heartbeat requires an actual
initial sample after policy installation/modification; it is not armed by a metric
that never existed. Hourly SQL checks detect retention overdue after two days;
no unsupported 48-hour absence condition is emitted. Existing notification channel
and organization log placement/retention are preserved reviewed inputs. Native
first-sample, missing-run, failure/notification tests precede application release.

10 native mock plans/schema validation, 12 operator image checks each PG17/18,
2 proxy lifecycle cases, 5 emitted-runner cases, 5 restricted delivery-image queue
cases, 87 API/operator, 309 JS, 208 server checks and build pass. Known build chunk
warning remains. Exact image still has 47 high findings, zero critical or reported
fixes in cached metadata; not production/security acceptance. The pinned proxy's
prior scoped binary-applicability review remains unchanged, not blanket approval.

Primary observations, exact package, image/source hashes, raw logs, selected native
schema and source snapshots are preserved; manifest.json binds bytes. Fake CLI
executables are not distributed here; their reproducible source is in the qualifier.
No private fixture password/nonce/dump or cloud operation is present. Historical
AWS/Azure image receipts retain their own original source bytes; shared-job changes
require fresh exact-image admission for future combined exports.

Next: IBM native operating wrapper, then complete state/Spec Kit/registry and four
medium invoice business conversations/exports. Zero complete medium cases counted.
Remaining families, full 28-case and held-out acceptance are unfinished.
