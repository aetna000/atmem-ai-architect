# IBM invoice native composition review

Reviewed 2026-11-10. No cloud account was accessed. Provider 2.9.0 public schemas
and documentation are pinned to revision
`18d6bc184c3c8bd00f276db7087f161520cdf276` in the retained source receipt.

The invoice adapter selects PostgreSQL 18 Classic private service endpoints.
Current provider documentation distinguishes its `standard` plan from Gen2's VPC
`standard-gen2` plan. The latter requires an explicit VPE/network route and has
provider-version-specific limitations; Code Engine is not assumed to have direct
VPC connectivity. This choice does not migrate or replace an existing database.
Actual private reachability, configuration schema, native CA and database access
remain destination checks. SQL passwords are separate operator-managed credentials;
trusted profiles do not magically become PostgreSQL login identities.

The API, worker and parser are separate workloads. API/worker trusted profiles are
distinct; the parser has neither a compute resource token nor Code Engine API
service-account authority. Private visibility alone is insufficient caller
identity: the worker/parser receive a separate 256-bit parser-only admission secret
outside Terraform. The API does not receive it. The parser removes it from its
environment; native tools receive a fixed minimal environment. This does not claim
an OS sandbox or protect against hypothetical platform permission inheritance.

Code Engine's documented CE_APP/CE_SUBDOMAIN/CE_DOMAIN/CE_REGION values construct
the API origin, matched to the emitted service name/region. Host/Forwarded request
headers do not select trusted origins. App ID redirects depend on the created API
endpoint; the API configuration does not depend on its own computed Terraform URL.

A shared generator defect derived registry domains by appending `.icr.io` to the
Code Engine region. IBM's documented Sydney domain is `au.icr.io`. The shared map,
structured application and public FAQ compilers are repaired and have native
resolved-image regression checks. Unsupported regional mappings cannot silently
fall back to the global registry. The provider-hosted image backup geography is a
separate fact requiring review; no artifact-residency guarantee is inferred.

Primary references:
- https://cloud.ibm.com/docs/Registry?topic=Registry-registry_overview
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-inside-env-vars
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-application-workloads
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-app-scale
- https://cloud.ibm.com/docs/cloud-databases?topic=cloud-databases-service-endpoints
- https://cloud.ibm.com/docs/databases-for-postgresql-gen2?topic=databases-for-postgresql-gen2-migrating-postgresql-gen1-to-gen2
- https://github.com/IBM-Cloud/terraform-provider-ibm/tree/18d6bc184c3c8bd00f276db7087f161520cdf276

Local schema/mock-plan, exact Linux image, synthetic secret/config-map and SQL/RPC
checks are not cloud identity/network/model or full-project acceptance. Native
operator/scheduled maintenance, monitoring, state and complete registry/Spec Kit
integration remain unfinished; no medium invoice benchmark is counted yet.
