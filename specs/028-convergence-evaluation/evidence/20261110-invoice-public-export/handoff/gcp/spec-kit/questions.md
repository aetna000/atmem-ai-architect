# Questions and assumptions to resolve

Snapshot b3d76c90-d37f-4688-87e4-0ae74d9ffd3c · design r1 · generated 2026-11-10T08:00:00.000Z

- [acceptance-invoice-approval] Agree a measurable acceptance check for Requirement: Only a reviewer can approve the current extraction revision before accounting delivery; ordinary uploaders cannot approve.
- [platform.cloud] Confirm cloud provider; diagram labels alone are not a selection.
- [data.country] Confirm the country and data-residency boundary, including sources, logs and model processing.
- [cloud.region] Engineering verification: choose and document a suitable proposed region within the accepted country, then verify service/model support, residency, quota and account policy before deployment. Escalate only a material business trade-off.
- [scope-boundary] No explicit scope boundary is recorded. Record included and excluded use cases before sizing or implementation.
- [scope-outcome] No structured application outcome is recorded. Confirm a concise outcome, intended users and exclusions; raw conversation fragments are not an implementation brief.

## Assumptions requiring verification

None recorded.

Also confirm target repository, runtime/toolchain, deployment account owner, access boundaries and release authorization. Ask questions conversationally, starting with those that block the next task.
