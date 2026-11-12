# IBM invoice workflow (under qualification)

A new owned Code Engine project hosts the public App ID/PKCE staff API, a minimum-one
background queue worker and a separate private-TLS parser. Only worker/parser hold
the parser-only 256-bit admission token; it grants no cloud/document/SQL/action
permission. The parser has neither a compute resource token nor Code Engine API
service-account authority. API and worker use separate native trusted profiles,
SQL logins and secret references. Staff authentication is separate from live SQL
membership and reviewer authority; public self-registration is disabled.

The dedicated PostgreSQL 18 Classic instance uses private IBM service endpoints;
no unimplemented direct VPC/Gen2 route or public SQL fallback is asserted. Exact
regional service availability, private connectivity, CA verification and inherited
permissions require authorized destination checks. Documents are private, versioned
and stored regionally with a 90-day current / one-day noncurrent lifecycle. The
regional S3 API uses authenticated TLS. Cloud control-plane/log/backup behavior and
account policy need separate review; no exact erasure deadline is promised.

Sydney Container Registry uses au.icr.io, not au-syd.icr.io. The namespace is owned
by this package. Foundation creates resources with applications_enabled=false.
CODE_ENGINE_INPUTS.md specifies separately populated config/secret references.
Publish immutable reviewed images only when authorized, initialize SQL and staff
membership through the separate operator, then review application release. The
worker's instance-scoped watsonx Writer role is broader than prediction-only;
separate project collaborator admission and the scoped model policy review remain
required. An empty policy review blocks inference and never fabricates approval.

Native schemas/mocks and local images do not prove the real account, IBM private
network, model processing, restore or deployment. Full managed operator/scheduled
retention delivery, monitoring, state strategy, registry/Spec Kit admission and the
complete conversation/export checks remain qualification work. No cloud operation
is performed by generating this package. Preserve the external accounting system.

## Whole-project scope and state

Read invoice-contract.json, resource-schedule.json, OPERATING_JOBS.md and STATE.md.
Additional requested components/flows/configuration remain visible and block the
review gate until implemented. No diagram requirement is removed by this module.
Production uses its reviewed provider-specific protected state/locking backend; no
state store is deployed or silently borrowed from another cloud. Destination
state residency, access, locking and recovery acceptance precede account planning.
