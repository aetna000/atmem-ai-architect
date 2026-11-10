# Delivery handoff

Snapshot 91157f76-97f3-4e19-9831-2d7d16d83f3e · design r1 · generated 2026-11-10T08:00:00.000Z

This is a reviewable design handoff, not deployment evidence.

## Readiness

Read spec-kit/readiness.md for prioritised decisions, task links and separate evidence stages. Schema checks cannot establish application deployment readiness.

## Work remaining

- Staff browser: no cost lines; add charges or an explicit zero-cost line with a reason.
- Invoice intake and review: no cost lines; add charges or an explicit zero-cost line with a reason.
- Existing accounting service: no cost lines; add charges or an explicit zero-cost line with a reason.
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
