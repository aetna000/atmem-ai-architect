# 011 — Engineering handoff quality

Requested 2026-11-07: improve AtMem Architect across projects through repeated generate/review/test runs, rather than correcting one exported bundle.

## Outcome
A recipient can distinguish agreed design, unresolved choices, implemented infrastructure and unverified behavior; identify the next actionable task; and follow an executable path from local implementation to authorized staging and release.

## Acceptance
- Explicit service selections outrank descriptive labels; ambiguous labels never generate resources.
- Generic OpenSearch does not silently select Serverless.
- Accepted design decisions remain available without promoting their proposed service/region wording into confirmed deployment choices.
- Country and deployment region are independent decisions.
- Every export includes a deterministic readiness assessment, component-specific engineering work, traceability gaps and evidence boundaries.
- Local infrastructure checks precede staging approval; live integration tests depend on authorized staging, not the reverse.
- The architect receives the same priority gaps as the exported handoff.
- Regression scenarios cover AWS, Azure, GCP, IBM, existing systems, shared responsibilities, ambiguous services, incomplete requirements and cyclic diagrams.
- No claim of full Terraform coverage, live deployment, service availability or cost without evidence.

## Boundaries
No cloud operations, customer-specific infrastructure decisions, migrations, or live paid model calls. Full provider-native application generation remains separate implementation work; this feature makes that boundary and required work precise.
