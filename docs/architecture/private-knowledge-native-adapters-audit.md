# Private model, secret and durable audit integration

The private coordinator now has a fixed native model operation, native-secret file
adapter and SQL audit writer. These extend the generated-runtime implementation;
they do not yet constitute a configured application or complete cloud export.

## Fixed model operation across four providers

`enterprise_models.native_generator` chooses the provider from owned deployment
configuration. It reuses the reviewed Bedrock Converse, Azure OpenAI, regional
Vertex and Watsonx chat implementations already used by structured operations.
Question/source content cannot change the operation schema, instruction, endpoint,
credential source, tools or model selection. The private payload is limited to
64 KB and a bounded set of owned article fields; duplicate IDs and extra fields
are rejected. Existing provider retention/logging checks run before inference.
The private coordinator independently checks exact supporting quotes/citations
and current source access after the native response. No provider schema mode
substitutes for that validation.

Construct a generator per engine/job so mutable HTTP sessions are not shared
between concurrent jobs. Native exceptions are sanitized before returning to the
queue; bounded domain retries remain the only retry owner. The API role must
eventually use a release-only factory without inference permissions. The production
API/worker factories and native per-file parsing jobs remain unfinished.

Seven new policy tests exercise all four real native serializers with scripted
HTTP: exact private schema/citations, revocation before context, unavailable policy,
tool responses, forged citations, attempted operation replacement and unknown
provider selection. These are neither live cloud-account calls nor model-quality
evaluation. Actual workload identity/token exchange still needs its own evidence.

## Explicit native dependency closures

`build-enterprise-runtime-lock.py --provider all` emits the core and four provider
closures from pinned, already reviewed metadata. AWS has 37 packages, Azure 36,
Google 33 and IBM 35. Native SDK imports resolve from the exact Linux installation.
IBM's SDK requires python-dateutil >=3.0.0; forcing the old shared 2.9 pin correctly
failed. IBM now explicitly selects reviewed 3.0.0, which the queue permits; the
other targets retain reviewed 2.9.0.post0. This is not an ignored dependency conflict.

The host policy command now uses the existing CPython3.13 qualification environment
(`npm run test:enterprise`), matching the runtime ABI. The initial CPython3.14
server environment could not load the qualification directory's CPython3.13
pydantic binary; that failure is retained. No package is downgraded or replaced
to hide it. Clean Linux checks run against target CPython3.13.18 and exact locks.

## Native platform secret injections

`enterprise_secrets.SecretFiles` accepts owned native mounted files or native
platform secret injections for the encryption key, confidential source registrations
and provider-appropriate SQL password/CA. It never creates a replacement key or
fetches arbitrary cloud secrets. Direct injections become owner-only temporary
files (directory0700/files0600), are removed from the actual process environment
after successful setup, and are cleaned on normal close/exit. Existing platform
mounts are read, never replaced/deleted. Reads are bounded and failures sanitized.
OS/process memory, crash residue and storage backup erasure are not promised.

API and worker both need the existing encrypted credential key and source
registrations. Static developer cloud keys, general model API keys, parser admission
tokens and outbound-action credentials are rejected. Non-IBM workloads cannot
silently receive a SQL password instead of their reviewed native database identity.
Required missing/unreadable/invalid files fail startup; conflicting raw/file inputs
are not resolved by choosing one. All replicas must use the same pinned encryption
key version. Coordinated re-encryption, recovery and rollback remain operator work;
there is no unsupported hot key rotation claim. OAuth secret readers reread their
owned mounts; that alone does not establish safe concurrent vendor rotation.

Eight tests cover all4/api+worker injections, restrictive permissions under umask0,
external mounts, live bounded reads, key/conflict/static-authority denial, process
environment cleanup and partial-write cleanup. The original cleanup fault injected
failure into every OS open, including directory cleanup; the corrected injection
fails the second secret creation while exercising real cleanup of the first key.

## Durable knowledge audit and release fences

`enterprise_audit` is a separate fresh owned schema. The runtime receives INSERT
and identity-sequence USAGE, with no history SELECT/UPDATE/DELETE/TRUNCATE or schema
ownership. Grant validation rejects inherited administrative, history-changing and
authority-table write privileges. No existing database is migrated or adopted.
Administrative tamper resistance, native log export and retention/restore operations
are not established by these application-role permissions.

Only exact answer/release outcomes and bounded source/document counts are admitted.
Account, pseudonymous principal, trace and optional question/attempt come from the
server-owned binding, never the model event dictionary. Questions, titles, source/
document IDs, snippets, answers and credentials are not audit fields. Question
events must match an existing owned request/principal and a real current/past
attempt. Unknown, other-principal and future attempts cannot fabricate that link.
Withheld events remain recordable after membership/session/consent withdrawal;
recording denial is not an authorization grant. Queue/auth lifecycle events remain
separate, including failures before the knowledge engine can be constructed.

`EnterpriseAnswers` can require this owned writer, replacing the engine's audit
callback with its exact job/release context. Generation cannot become ready if
audit persistence fails. A saved answer cannot be released if its new release audit
fails; after recovery it must revalidate current source access before release.
The browser/queued fixture uses durable audit; the future production factory must
always supply it. The synchronous compatibility factory remains separately owned.

Nine native SQL tests verify persistence, metadata/privacy, append-only application
privileges, revocation logging, query binding, sanitization and grant rejection.
Three queued API tests verify correlated generation/release and actual audit grant
withdrawal/recovery. Browser checks inspect durable question/attempt-bound audit
counts after real queued answers. Source, IdP and model HTTP remains scripted.

The generic unavailable copy now says the workspace could not finish the answer
and suggests retrying. It no longer incorrectly blames a company source when the
actual failure was model, audit or another workspace dependency. No internal SQL,
revision, artifact ID or stack trace is shown to the basic user.

Next assemble native production API/worker factories and operator membership/source
mapping/bootstrap/recovery, qualify provider-specific per-file parser isolation,
wire all4 Terraform/application/Spec Kit exports, then run the actual private cases,
remaining families and full28/held-out evaluation. Dependency/fixture checks do not
promote a whole case or security acceptance.
