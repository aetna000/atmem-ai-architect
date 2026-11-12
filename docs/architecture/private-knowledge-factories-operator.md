# Native private factories and operator lifecycle

`enterprise_native.NativeRuntime` assembles the owned company identity, encrypted
sessions/source grants, native SharePoint/Confluence adapters, transactional query
producer/worker, immutable extraction cache and durable knowledge audit. The API
and worker use separate native database identities. Nothing provisions a database,
changes an existing schema, enrolls a person or changes provider at API startup.

`enterprise_configuration.py` validates a bounded, duplicate-free packaged
`enterprise-deployment.json`: selected provider, workspace account, canonical HTTPS
origin, existing company OIDC/API registration, the two existing native sources
and full parser artifact revision. Unknown fields/endpoints/provider substitutions
are rejected. This implementation targets the benchmark's SharePoint + Confluence
company assistant, not arbitrary additional source vendors or identity protocols.

The source vendor systems and company IdP remain external references. Confidential
source registration secrets and the existing encryption key are native secret-file
inputs; no secret value belongs in this metadata, Terraform state or a handoff ZIP.
The normal destination inputs must be resolved by the existing IT/account owner;
the basic user is not asked to invent subject IDs, TLS certificates or port numbers.

## API and worker separation

The API has no inference client or document executor and no worker queue mutation
or extraction-cache grant. It only submits questions and revalidates delayed results.
The old synchronous `/api/ask` route returns410 in this factory; browser questions
use the durable service. The worker cannot serve the browser API. Native runtime
startup checks exact SQL schema digests/queue version, nonadministrative role flags,
schema ownership, inherited authority writes, audit history permissions and the
activated configuration. API startup refuses a worker database identity.

The API entry is:

```sh
python -I /app/enterprise_native.py api
```

The compiled package must supply its owned metadata and native connection/secret
references first. `PORT` defaults to8080. Uvicorn does not trust forwarded headers;
native ingress/TLS needs separate provider qualification. The configured canonical
origin controls callbacks, CSRF and public OIDC data. Health is process liveness,
not proof that external accounts, IAM, model policy or the full system is ready.

The worker factory takes `DocumentExecutor`, supplied by an owned per-file workload
launcher, with the exact reviewed artifact revision. This immutable object validates
the complete byte/MIME/digest/text response and sanitizes failures. Its type and
revision string alone do not prove execution provenance or isolation. Only raw
bytes and MIME go to its execution port. There is intentionally no default unsafe
in-process parser, shared parser-RPC fallback, arbitrary request URL or advertised
worker command without that launcher. Provider-specific native per-file launchers
and secret/result transfer are still required implementation work before export.

Native model configuration is checked before worker claims. Missing/expired/mismatched
Google/IBM scoped retention reviews fail startup with an operator-facing message.
AWS/Azure use their native account policy reads; no fabricated approval is substituted.
Every real model transport still repeats its required policy checks at generation.
Model HTTP/client instances are per engine; API release never constructs them.

## Operator bootstrap and approved directory membership

`enterprise_operator.py` accepts one bounded private JSON command on stdin. It
does not accept credentials or person IDs in command-line arguments. Examples
below are command shapes, not destination account values or approvals:

```json
{"operation":"initialize","apiRole":"existing_api_login","workerRole":"existing_worker_login"}
```

Initialization is one transaction: fresh auth/queue/cache/audit schemas, separate
existing runtime grants, and activation of the packaged configuration. Existing
schemas are refused without adoption, deletion or implicit migration. SQL roles
and the native database already exist; the helper neither creates cloud resources
nor cluster roles. The positive qualification uses a dedicated database owner
without SUPERUSER, CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS. Root fixture
authority creates the fresh test database/roles and runs only explicit fault probes.

The operator receives only native database access and its provider-appropriate CA
or IBM SQL password. It rejects application encryption and delegated source secrets.
It can create schemas/grants because it owns this application database; that does
not make it a runtime identity. Startup and grant checks prevent substituting it
for an API or worker login. These operations were tested locally, not against a
managed account or its provider-specific initial IAM/SQL identity bootstrap.

```json
{"operation":"enroll","subject":"approved-company-api-subject","mappings":{"sharepoint":"approved-native-graph-id","confluence":"approved-atlassian-account-id"}}
```

Use the approved directory handoff's actual API subject and native account IDs.
Do not infer account ownership by matching email text or decoding an unverified
JWT. Enrollment is idempotent: repeating the same mapping preserves its version
and current consent. A changed mapping advances its version, clears its old
encrypted credential and pending consent receipts, and requires fresh native consent.
Writes and their administrative journal are atomic even if a caller catches errors.
Concurrent replays serialize within the owned person scope.

```json
{"operation":"revoke","subject":"approved-company-api-subject"}
```

Revocation disables membership/mappings, clears remaining source credentials and
pending consent, revokes browser sessions, cancels queued/running/ready questions
and clears their encrypted input/result. Domain leases fence late workers. Other
people remain unchanged. Re-enrollment cannot revive old sessions or old consent.
The runtime cannot enroll/revoke people or read/change administrative history.
Administrative records contain server actor, pseudonymous principal, action and
mapping/configuration versions; they do not record questions or credential bodies.
Audit retention/restore and authoritative directory-feed automation remain tasks.

## Activated configuration and opaque-session boundary

A retained regression returned200 for an old cookie after the company web client
registration changed. Checking only fresh JWTs did not revoke already-issued
opaque sessions. Applying a new check only to the replacement process would also
leave older running processes with their previous authority.

The operator now activates a hash of the workspace/origin, company registration,
source definitions and selected provider in `enterprise_auth.company_bindings`.
Runtime roles can read but cannot change that authority. Every native company
authorization gate compares its expected configuration with that current binding.
Cookie nonce envelopes and queued work also bind/validate the matching context.
This is separate from parser artifact/cache revision; an ordinary parser upgrade
does not itself change company/source identity policy.

```json
{"operation":"activate"}
```

An unchanged activation is idempotent. A changed activation atomically advances
the configuration version, journals it, revokes existing sessions/consent attempts
and cancels old active questions. Older native API/worker processes lose authority
after commit. A new runtime refuses mismatched/unactivated metadata at startup;
new directory changes require the activated metadata. A fresh verified company
login can rotate a stale cookie using a new browser nonce. There is no fallback to
old envelope contexts or self-activation by a browser/model.

Activation does not physically recall data already delivered or instantly stop an
external model request already authorized before commit. Current-source, company,
lease and release gates withhold late results. Drain workers for planned identity
or source changes to reduce uncertain rotating-token outcomes. This is not a
promise of continuous revocation of an external IdP JWT or stronger consistency
than the source vendor provides. Native account staging must measure those bounds.

## Qualification and remaining scope

Nine assembled factory tests use actual separate SQL roles, PKCE/native SDK source
flows, transactional queue/worker, encrypted cache/audit and ASGI. They cover all4
provider dispatches, release-only API, restart, bad roles/schema, revocation, parser
binding, missing model reviews and changed registration. Vendor/model/decoder
boundaries are scripted and clearly labeled. Eleven operator tests include regular
database-owner privileges, concurrency/idempotency, rollback, stale-cookie/task
revocation, source changes and least-privilege denial. The native callback failure
from a mismatched synthetic client secret was corrected in the fixture, not by
relaxing secret checks. The original cookie regression and exact source snapshot
are retained separately from its passing repair.

Independent Linux dependency builds run67 policies and77 actual SQL/crypto/queue/
cache/audit/operator tests per PostgreSQL17/18 for each cloud. The assembled HTTP
factory tests run on the host; Linux imports/SQL tests do not prove native ingress
or that configured HTTP app in a cloud. No native source/IdP/model account, real
cloud plan/deployment,10,000-document relevance or3,000-question daily performance
claim is made. No complete medium case or new public generator capability is promoted.

Next implement/qualify native per-file execution and transfer, complete key backup/
rotation/recovery and audit retention/restore, emit all4 native Terraform/application/
Spec Kit compositions, then run actual complete-client-brief private cases, the
remaining families and the final full28/held-out evaluation. Existing security
findings remain unaccepted; no scope or requirement was removed to pass these tests.
