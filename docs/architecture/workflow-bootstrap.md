# Owned approval-application assembly

`workflow_application.ApplicationProfile` is immutable nonsecret application
configuration. It connects typed HTTP intake, native staff verification, a durable
PostgreSQL queue and explicit processing/delivery stages. It neither provisions
resources nor invents business processors, identity enrollment or vendor mappings.

The exact profile fields are `format=approval-application-v1`, `provider`,
`componentId`, `environment`, `accountId`, `publicOrigin`, `operationKind`,
`identitySettings`, `payloadContract` and `destinationContract`.
Provider is explicitly aws/azure/gcp/ibm; environment is staging/production/
qualification. Component identity is retained completely, up to512 UTF-8 bytes.
The logical application account is a canonical UUID, independent of the cloud
account/project/subscription. Unknown fields, code/module paths, credentials and
implicit provider fallbacks are rejected. The whole profile is bounded to64000
UTF-8 bytes. `load_profile` reads an owned absolute path and rejects duplicate keys.

Identity settings are the existing native adapter's nonsecret fields: AWS regional
Cognito pool/client/origin/scope, Azure tenant/API/SPA clients, Google IAP project
number/region/service, or IBM App ID tenant/client/issuer/scope. These retain their
established issuer/audience/client/token/lifetime policies; moving their shared
implementation does not expand supported partitions, identity products or providers.
The selected native verifier validates the settings before API admission. Destination
infrastructure and effective identity/database permissions need separate qualification.

`create_native_api(profile, environment)` constructs the selected verifier and an
API-role database credential factory, then a producer-only typed API. Public identity
settings come from the profile. Supplied environment values for provider, account,
environment, namespace, origin or native identity must agree. API assembly never reads
a model or outbound destination secret. `create_native_worker(profile, environment,
processor, deliver)` selects the worker database role and trusted source callbacks;
it imports no API/JWT module. Source stages keep their original deadlines and reviewed
delivery/idempotency attributes. Their row account/kind is checked before invocation.
Callbacks are Python bootstrap inputs, never names/actions loaded from profile data.

The native task alias derives from the complete provider/account/component/environment
identity, with its full SHA256 available alongside the bounded native alias. Distinct
owners/environments do not normally share task names. Full declaration/destination
checks still reject mismatched work if an alias collides. Policy/identity/payload
changes retain the alias so old work remains visible and blocked for reconciliation.
They change `applicationContractSha256`, which joins the payload digest in persisted
destination identity and approval fingerprints. An account-change policy cannot
silently reinterpret previously reviewed draft work. A configured store also rejects
any other operation kind before insert, processing, result commit or approval.

Native API membership uses `membership_key(profile, complete_verified_subject)`:
a derived SHA256 identifier over provider, owned issuer realm and the entire native
subject. No subject characters are clipped; the native IdP remains authoritative.
An operator must enroll that key in the owned account after independently admitting
the native subject. Token role names are never enrollment. A different issuer/tenant
cannot inherit the same subject's membership; client/scope changes within the same
issuer preserve person identity while rebinding work/approval policy. Keep the
operator's native-subject mapping for administration/audit. There is no enrollment
HTTP endpoint or automatic role migration. Existing invoice membership identifiers
and namespaces retain their prior behavior through compatibility imports.

A normalized HTTPS adapter must use the reviewed endpoint/scope, allowed kind,
`profile.payload` and `application_contract_sha256=profile.sha256`; it checks the
whole binding before credentials/network access. Native integration mappings,
idempotency acceptance, unknown effects and authorized recovery remain separate.
The profile itself contains no replay acceptance, credential or deployment approval.

Current exports carry these reusable helpers and their local tests. Native credential
factories use the existing reviewed PostgreSQL transports and role choices. They do
not initialize schema, create memberships or migrate existing work. Generic selection
from the shared architecture model, resource/environment linkage, executable entrypoints,
domain implementations and full handoff/system evidence remain GE-006 work before
alpha.5. Apply the factory only where its declared persistence/approval/identity
contracts fit; preserve other requirements and existing systems as implementation work.
