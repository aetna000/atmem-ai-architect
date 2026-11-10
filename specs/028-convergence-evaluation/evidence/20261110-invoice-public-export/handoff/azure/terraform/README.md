# Azure invoice workflow (under qualification)

Separate Container Apps API, worker and private authenticated parser; private
Entra-only PostgreSQL, versioned private objects, private regional model, native
secret references and explicit staff/SQL authority. The parser's ACR pull identity
uses lifecycle None; only the worker's exact app-only Parser.Invoke token is admitted.
Native cloud isolation/authentication still require authorized destination checks.

Foundation precedes native SQL identity/schema/membership bootstrap, accounting
secret population and exact image publication. Never put secrets in Terraform
variables or source. See OPERATIONS.md. Application images and direct staff role
assignments do not imply SQL reviewer membership. No existing users, accounting
system or external website are recreated. Review regional model/version availability,
modified monitoring approval, quotas, fixed costs, private operator connectivity,
state, monitoring and managed restore. OPERATING_JOBS.md supplies native manual
bootstrap and phased daily/hourly jobs, diagnostic routing and query alerts. Job
start authority is privileged and remains outside the product. Native operations
and whole-export qualification remain in progress; this is not a complete invoice case.

## Whole-project scope and state

Read invoice-contract.json, resource-schedule.json, OPERATING_JOBS.md and STATE.md.
Additional requested components/flows/configuration remain visible and block the
review gate until implemented. No diagram requirement is removed by this module.
Production uses its reviewed provider-specific protected state/locking backend; no
state store is deployed or silently borrowed from another cloud. Destination
state residency, access, locking and recovery acceptance precede account planning.
