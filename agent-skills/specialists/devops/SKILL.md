---
name: devops
description: Infrastructure and DevOps handoff
version: 1.1.0
---

Prepare a reviewable plan, IaC sketch, CI/CD checks, secrets handling, observability, acceptance tests, rollback and ownership. Existing systems require integration planning. Every wire needs implementation. Access does not equal permission to deploy; the current broker has no write/deploy tools. Report implementation and validation gaps.


Use a bounded qualification loop before deployment: capture the original prompt, diagram, artifact identity and failed checks; fix the owning product layer; rerun the same scenario and regressions. Preserve round-by-round evidence, including unchanged failures. Stop retrying a model for a missing native implementation: identify the code change needed. A successful export is not deployment readiness. Require functional, denial, failure/recovery, update and cleanup evidence for an end-to-end claim.
