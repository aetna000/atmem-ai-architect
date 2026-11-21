# Azure public-only FAQ composition

The generated Python browser/API is intentionally anonymous. Its dedicated managed
identity can read only this private public-article container and invoke/read policy
on its generated regional model account. A separate existing Entra editor group
receives container-scoped data contributor access. No application HTTP endpoint
edits articles. No users/groups, existing resource group or ACR are recreated.
This is not a private enterprise knowledge assistant or existing-SSO integration.

Shared storage keys and anonymous blob access are disabled; the Azure provider
uses Entra for storage access. App Service basic publishing/debug/FTP are disabled;
the application uses managed identity for image pulls. Verify the existing registry
uses standard RBAC and accepts the ARM audience. No registry credential or model
key is exported. Public TLS endpoints use IAM/RBAC; private networking is not
implemented. Review inherited permissions and current tenant/subscription context.

See applications/*/BUILD.md for exact source/test/build and conditional editor CLI
steps. Protect Terraform state and variables. Seed only genuinely public articles
with the authorized editor before admitting traffic; a missing/inaccessible source
does not become an empty catalog or a cached answer. Blob versions and seven-day
soft deletion are recovery features, not an immediate erasure guarantee. Review
recovery and costs. Anonymous access plus concurrency/instance/output limits is
not an invoice cap; approve and test destination abuse controls and budget policy.

Choose a compatible regional Standard structured-output model/version and verify
actual quotas, prices and geography. Runtime requires approved ContentLogging=false
before inference and never writes that account-wide setting. Provider/platform
logging and identity/control-plane processing require separate review. No app
question/answer persistence or content-bearing application logs are implemented.
Real model answer/citation/abstention and latency tests remain required.

Use Terraform 1.17.1+, terraform init -backend=false, terraform validate and
terraform test. These mock checks do not prove real Azure IAM, managed identity,
storage conditionals or model quality. Obtain explicit authorization for registry
publication, cloud access, a real account plan and deployment. Production state,
backup and operating review remain gated; no export proves deployment.
