# IBM structured AI application

The explicit ibm-structured-app module emits a Python 3.13 browser/API on Code Engine, a NEW owned App ID tenant and single-page PKCE registration, scoped WorkspaceUser role, disabled social/self-signup paths, dedicated trusted profile and exact Code Engine compute-resource link. Existing Code Engine project, private registry/pull secret, watsonx data-platform project and associated runtime instance are preserved. Independent blocks/connections retain their gaps.

User and workload identities are separate. The API verifies RS256 App ID signatures from its fixed public key endpoint, exact issuer, single client audience, tenant, authenticated Cloud Directory method and application process scope before and after inference. ID/anonymous/machine tokens do not grant user access. No custom user-attribute-to-scope mapping is created. Protect tenant administration; token scopes last until expiry, and immediate revocation, existing SSO, MFA or private networking are not implemented by this module. The browser keeps access tokens in memory, verifies OAuth state and S256 PKCE, clears private input/results on access loss, and offers local workspace clearing without claiming global identity-provider logout.

The fixed Code Engine compute-resource token is exchanged by the hash-pinned IBM SDK using the generated trusted profile. No application API key or client secret is emitted. The exact linked project/app is trusted; there is no account-wide compute rule. The runtime receives Writer only on the reviewed pm-20 runtime instance. This role includes broader instance operations and is not prediction-only. Data-platform project collaborator membership and associated-instance/model access are separate destination prerequisites; verify them instead of expanding IAM or introducing static credentials. The app becomes live before its compute link is created, then inference can work after account propagation and project authorization; do not create an app/link dependency cycle. Health is liveness, not model readiness.

One bounded regional Text Chat request uses the reviewed model/project, JSON-object output, no tools, no automatic retry or saved session. Invalid, duplicate, extra, truncated or action-bearing output fails closed. Independent schema checks and human review do not establish semantic model quality. A scoped, expiring destination-owner review of actual retention/processing terms is required before workload authentication or inference. It is operator-attested evidence, not a fabricated IBM privacy approval API. No app input/result persistence is implemented; identity/IAM/global processing and actual model geography still need review against residency requirements.

Use BUILD.md and Terraform 1.17.1+. Run terraform init -backend=false, terraform validate and terraform test; inspect the empty user allowlist and wrong-account/unapproved/mutable-image negative tests. Build, scan and locally test the exact Linux image, obtain authorization to publish, and supply its immutable registry digest. Account plan, current service/model availability, quota, costs, real App ID signup denial and role tokens, Code Engine token exchange, dataplatform model access, model quality and operations must be checked before deployment. Production state/backup/operating review remains gated. Scaling/token limits are not an invoice cap or SLA. Terraform state/variable files require protection; no export proves deployment.

References:
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles-authentication-file
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-inside-env-vars
- https://cloud.ibm.com/docs/appid?topic=appid-single-page
- https://cloud.ibm.com/docs/appid?topic=appid-access-control
- https://cloud.ibm.com/docs/appid?topic=appid-token-validation
- https://cloud.ibm.com/docs/apis/watsonx-ai
- https://cloud.ibm.com/docs/iam?topic=iam-iam-service-roles-actions
- https://registry.terraform.io/providers/IBM-Cloud/ibm/1.89.0/docs/resources/iam_trusted_profile_link
