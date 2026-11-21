# Google invoice workflow (under qualification)

Cloud Run/IAP API, continuously allocated private worker, separate IAM-protected
parser, maintained private-IP Cloud SQL Auth Proxy, regional HA IAM-authenticated
PostgreSQL, versioned private regional documents and separately populated regional
secret. Existing project, staff identities and accounting system are preserved.

The API receives no model/action authority. Only the worker invokes the parser;
the parser has no emitted data/model grants or database/proxy sidecar. The proxy's
local TCP connection stays inside the workload, with upstream TLS and IAM checked
by the pinned maintained proxy. No Cloud SQL public IP or plaintext remote fallback.
Application and worker SQL users receive explicit restricted bootstrap grants; the
separate operator IAM user intentionally has administrative SQL authority.

Review organization-owned IAP setup, actual model geography/lifecycle, privacy
policy evidence, inherited IAM and regional quotas/costs. Missing scoped model-policy
review blocks inference. The application never self-approves or modifies project
logging/cache/abuse policies. Native private connectivity, token roles and managed
restore still require destination checks. OPERATING_JOBS.md supplies fixed private
bootstrap, daily/hourly jobs, scoped OAuth scheduling and count-only log alerts.
The operator waits for and explicitly terminates its job-only proxy sidecar.
See OPERATIONS.md and CLOUD_SQL_PROXY.md; whole-project acceptance remains pending.
Native operator scheduling/bootstrap and whole-export qualification are unfinished;
this compiler fixture is not a complete benchmark project or deployment evidence.

## Whole-project scope and state

Read invoice-contract.json, resource-schedule.json, OPERATING_JOBS.md and STATE.md.
Additional requested components/flows/configuration remain visible and block the
review gate until implemented. No diagram requirement is removed by this module.
Production uses its reviewed provider-specific protected state/locking backend; no
state store is deployed or silently borrowed from another cloud. Destination
state residency, access, locking and recovery acceptance precede account planning.
