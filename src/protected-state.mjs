const definitions={
 s3:{type:'s3',settings:{encrypt:true,use_lockfile:true},example:'bucket = "REVIEWED_PROTECTED_STATE_BUCKET"\nkey = "REVIEWED_PROJECT/production.tfstate"\nregion = "REVIEWED_STATE_REGION"\n',guide:'Use a separate private, encrypted, versioned S3 state bucket under the accepted custody/residency boundary. Terraform 1.17 uses native S3 lock files (use_lockfile=true), not an invented DynamoDB dependency. Restrict ListBucket to the project prefix and GetObject/PutObject to its state key; the corresponding .tflock also needs DeleteObject. Do not grant state DeleteObject merely for locking. Use the standard authorized AWS credential chain, never backend access_key/secret_key values.',source:'https://developer.hashicorp.com/terraform/language/backend/s3'},
 azurerm:{type:'azurerm',settings:{use_azuread_auth:true},example:'storage_account_name = "REVIEWED_PRIVATE_STATE_ACCOUNT"\ncontainer_name = "REVIEWED_STATE_CONTAINER"\nkey = "REVIEWED_PROJECT/production.tfstate"\ntenant_id = "REVIEWED_DIRECTORY_TENANT_UUID"\nsubscription_id = "REVIEWED_STATE_SUBSCRIPTION_UUID"\n',guide:'Use a separate reviewed private Azure Blob state container with versioning/recovery and the accepted residency. Native Blob leases implement state locking. use_azuread_auth=true uses Entra data-plane authentication; grant only reviewed container-scoped state access. Configure the approved Azure CLI, managed identity or workload federation through its documented environment chain; do not export storage account keys, SAS tokens or client secrets into backend.hcl. Verify the exact state subscription/tenant and effective inherited rights independently.',source:'https://developer.hashicorp.com/terraform/language/backend/azurerm'},
 gcs:{type:'gcs',settings:{},example:'bucket = "REVIEWED_PRIVATE_VERSIONED_STATE_BUCKET"\nprefix = "REVIEWED_PROJECT/production"\n',guide:'Use a separately bootstrapped private, versioned GCS state bucket under the reviewed project/custody/residency boundary. Terraform supports native state locking. Give the authorized state operator scoped object access, preserving unrelated bucket IAM; use the reviewed Google credential/workload-identity chain, never an embedded service-account key. Review encryption/key ownership, inherited grants, version recovery and the exact project/bucket/prefix. The state bucket is not the invoice originals bucket.',source:'https://developer.hashicorp.com/terraform/language/backend/gcs'},
 http:{type:'http',settings:{},example:'address = "https://REVIEWED_PRIVATE_STATE_SERVICE/EXACT_PROJECT_PRODUCTION_STATE"\nlock_address = "https://REVIEWED_PRIVATE_STATE_SERVICE/EXACT_PROJECT_PRODUCTION_STATE/lock"\nunlock_address = "https://REVIEWED_PRIVATE_STATE_SERVICE/EXACT_PROJECT_PRODUCTION_STATE/lock"\nlock_method = "POST"\nunlock_method = "DELETE"\nretry_wait_min = 5\n',guide:'Use the existing reviewed private platform state service implementing Terraform HTTP state and lock/unlock semantics, not a generic object URL or an unverified S3-compatible IBM COS lock assumption. The example selects POST/DELETE locking; verify the actual platform protocol and owner-safe lock behavior before use. Keep the service in the accepted custody/residency boundary. Configure TF_HTTP_USERNAME/TF_HTTP_PASSWORD or reviewed mutual-TLS environment credentials, never credentials in backend.hcl. No state platform is deployed by this module.',source:'https://developer.hashicorp.com/terraform/language/backend/http'}
};

export const PROTECTED_BACKENDS=Object.freeze(Object.keys(definitions));
export function protectedState(backendType,{title='Terraform state and environment ownership',environment='production'}={}){
 const definition=definitions[backendType];if(!definition)throw Error('Choose an explicit supported state backend; no target-provider fallback.');
 if(!['staging','production','qualification'].includes(environment))throw Error('Use an explicit supported state environment.');
 return {backend:{[definition.type]:structuredClone(definition.settings)},files:{'backend.hcl.example':definition.example.replaceAll('production',environment).replaceAll('PRODUCTION',environment.toUpperCase()),'STATE.md':'# '+title+'\n\nSelected backend contract: '+definition.type+'.\n\n'+definition.guide.replace('invoice originals bucket','application data bucket')+'\n\n'+COMMON+'\nReference: '+definition.source+'\n'}};
}

const COMMON=`Staging/qualification default to local state only for isolated local validation.
Production declares the provider-specific protected backend with no account names,
endpoints or credentials embedded. The existing state store is a separate platform
prerequisite, not an application resource. If the destination repository
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
`;
