# Invoice state and environment ownership

Recommended production backend: azurerm.

Use a separate reviewed private Azure Blob state container with versioning/recovery and the accepted residency. Native Blob leases implement state locking. use_azuread_auth=true uses Entra data-plane authentication; grant only reviewed container-scoped state access. Configure the approved Azure CLI, managed identity or workload federation through its documented environment chain; do not export storage account keys, SAS tokens or client secrets into backend.hcl. Verify the exact state subscription/tenant and effective inherited rights independently.

Staging/qualification default to local state only for isolated local validation.
Production declares the provider-specific protected backend with no account names,
endpoints or credentials embedded. The existing state store is a separate platform
prerequisite, not an invoice application resource. If the destination repository
already has another reviewed backend, preserve it through an explicit state/owner
decision and validate compatibility before any authorized migration.

Keep backend.hcl private and excluded from source. Do not put authentication values
in configuration or command arguments: Terraform can retain backend arguments in
its local metadata and saved plans. State can contain provider-computed identity
credentials even when runtime SQL/accounting secret payloads are supplied outside
Terraform. Restrict readers, protect backups/plans, and review retention/key policy.
Never disable TLS verification or use -lock=false to bypass an unavailable lock.

Local-only checks: terraform init -backend=false, terraform validate, terraform test.
Before authorized production planning, verify the existing protected state store
on an isolated approved state: concurrent clients must conflict on one lock, an
unrelated identity must not unlock it, and version recovery must preserve the
expected digest. Record actual service version, access, custody and recovery proof.
Then run terraform init -backend-config=backend.hcl through the approved credential
chain. Platform/account access, store creation and migrations require authorization.

Each deployment environment has a distinct physical resource-name seed. Use separate
staging/production state paths and reviewed immutable image/account/policy inputs;
never point production at staging state. Keep a verified private state backup before
an authorized migration and inspect exact lineage. Do not -reconfigure/-migrate-state
over a mismatched lineage. No external accounting service or actor is imported or
recreated. Resource deletion protections do not prove backup, restore or availability.

Reference: https://developer.hashicorp.com/terraform/language/backend/azurerm
