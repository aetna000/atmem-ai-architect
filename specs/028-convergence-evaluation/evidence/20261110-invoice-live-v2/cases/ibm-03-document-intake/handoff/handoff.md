# Delivery handoff

Snapshot ff90ecad-37e2-46e9-b0bc-3c58f4493bf0 · design r4 · generated 2026-11-10T07:56:28.114Z

This is a reviewable design handoff, not deployment evidence.

## Readiness

Read spec-kit/readiness.md for prioritised decisions, task links and separate evidence stages. Schema checks cannot establish application deployment readiness.

## Work remaining

- Invoice uploaders and reviewers: no cost lines; add charges or an explicit zero-cost line with a reason.
- Invoice intake and approval: no cost lines; add charges or an explicit zero-cost line with a reason.
- Existing accounting API: no cost lines; add charges or an explicit zero-cost line with a reason.
- Preserve the selected placement and propose a canonical provider region within that accepted residency. Country names or expressions are not deployment-region identifiers; this is engineering work, not a request for the user to configure infrastructure.
- Discovery & specification: effort, rate, ordered day range and basis needed.
- Architecture & security: effort, rate, ordered day range and basis needed.
- Implementation & integration: effort, rate, ordered day range and basis needed.
- Testing & acceptance: effort, rate, ordered day range and basis needed.
- Deployment & handover: effort, rate, ordered day range and basis needed.

## Before deployment

- Confirm provider, region, data residency, account owner and environment.
- Complete the resource implementations, application code, IAM and data-flow integrations.
- Validate the estimate against every billable dimension and a current provider quote.
- Review least-privilege access, quotas, secrets handling and Terraform state storage.
- Run and review the infrastructure plan in the intended account.
- Agree acceptance tests, rollback and an explicit deployment approval.
- Capture results and handover ownership. No cloud operation has been performed by this export.
