# Native application building blocks — review for convergence work

Reviewed primary documentation while the frozen 28-case baseline runs. These notes
are source review, not provider-account or deployed-system evidence. They inform
compiler design; they do not authorize cloud activity or copy a reference application
into a user project.

- AWS Bedrock supports schema-constrained output through the Converse outputConfig
  textFormat field for supported models. Model capability must be checked, and the
  application still needs input/output bounds, validation and failure handling.
  https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
  https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html
- Azure Container Apps has federated application authentication, distinct from a
  workload managed identity. Entra app registration and authentication settings are
  concrete dependencies. Avoid selecting an implicit flow merely because an example
  permits it; use the documented secure flow suitable for the application.
  https://learn.microsoft.com/en-us/azure/container-apps/authentication
  https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra
  https://learn.microsoft.com/en-us/azure/container-apps/managed-identity
- Cloud Run distinguishes internal-user and end-user authentication. End-user ID
  tokens must be verified by the application; an IAM-private service alone is not
  a complete browser sign-in flow. Its Identity Platform tutorial includes a real
  application/backend/database composition worth learning from, not copying blindly.
  https://docs.cloud.google.com/run/docs/authenticating/end-users
  https://docs.cloud.google.com/run/docs/tutorials/identity-platform
- Google Identity Platform configuration is project-wide and initialization has
  lifecycle restrictions. A compiler must preserve existing configuration rather
  than casually recreate it, and document state handling for sensitive attributes.
  https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/identity_platform_config
- IBM Code Engine supports workload trusted profiles with a mounted compute-resource
  token; this is service access, not an end-user login or tenant authorization system.
  https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles
  https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles-authentication-file
- IBM App ID exposes OIDC discovery. An April 2026 IBM notice concerns new IdP
  integrations for IBM Cloud platform federation through IAM. That notice is not
  sufficient evidence to declare every App ID application-authentication use removed.
  Verify the exact service, integration and lifecycle scope before changing advice.
  https://cloud.ibm.com/docs/appid?topic=appid-discovery
  https://cloud.ibm.com/docs/overview/whats-new?topic=overview-whatsnew

## Compiler direction

Compose reusable contracts for authenticated input, schema-validated generation,
retrieval/authorization, durable jobs, approved actions, tenant state, credit ledger
and operational recovery. Keep application semantics independent from provider
adapters while implementing each provider's real resources and access boundaries.
Do not add seven benchmark-specific templates and call that general expertise.

The baseline already shows a critical distinction: two-turn design convergence can
still produce an incomplete package. Interaction speed must not compensate for
missing runtime code, integration or verification.

## Policy findings added during the first repair cycle

Model-service lifecycle is part of the application contract. Application non-retention
and a no-training promise do not establish provider non-retention. The new AWS typed
operation verifies regional account mode `none` and disabled text invocation logging
before inference. Reads fail closed; it never changes existing account policy.
Sources: [Bedrock retention](https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html),
[invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html).
This is local implementation evidence, not observation of a customer's account.

Azure modified abuse monitoring requires eligibility/approval; the documented management
signal is a `ContentLogging` capability with string value `false`. Absence is not an
exemption. [Primary policy and verification procedure](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy).
For Google, check feature/account controls including durable cache, abuse monitoring,
grounding and interaction state; regional and global endpoints differ.
[Primary lifecycle reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention).
These reviewed summaries have source-byte hashes and retrieval timestamps in the
engineering knowledge records. No Azure/GCP account controls were read or changed.

## Next provider slice: Azure

The reviewed AzureAD 3.10.0 provider separates application registration, redirect URIs,
scopes, app roles and API access into resources. This permits an application callback
URL to depend on hosting without making its client ID depend on that callback. Verify
the full provider schemas and dependency graph before admitting a new compiler adapter.
[Registration](https://raw.githubusercontent.com/hashicorp/terraform-provider-azuread/v3.10.0/docs/resources/application_registration.md),
[redirect URIs](https://raw.githubusercontent.com/hashicorp/terraform-provider-azuread/v3.10.0/docs/resources/application_redirect_uris.md),
[scopes](https://raw.githubusercontent.com/hashicorp/terraform-provider-azuread/v3.10.0/docs/resources/application_permission_scope.md).

App Service authentication is a platform boundary; its injected identity headers must
not become a portable authentication substitute on a directly exposed container.
Application authorization remains separate. Consider direct bearer verification as
well as platform protection. [Primary App Service identity boundary](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-user-identities).
An Azure connected application adapter is still implementation work at this checkpoint.
