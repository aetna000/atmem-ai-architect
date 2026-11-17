# Decisions

- Owner chose the supplied review-hook direction on a separate branch from main; preserve infrastructure-upgrades work and the original scaffold folder.
- Implement a separately installable Python package in the existing repository. Do not create the placeholder atmem-ai repositories or publish tags/packages/catalog posts.
- Keep runtime review stateless. Reusing Architect generation/session memory would introduce writes and unnecessary tool privileges; reuse its evidence/contract discipline and pinned common dependencies instead.
- Core predicates are generic where explicit: exact attribute rules transfer to an Azure PostgreSQL case. AWS-specific ingress/provider/country/category adapters retain named limits and unknowns.
- Infracost now has a separate CLI repository. Checksum-verified infracost/cli v2.19.1 help confirms scan/JSON/currency flags; versioned source defines its output structure. The legacy v0.2 JSON shape is distinct. No live pricing calls or usable pricing credentials have been exercised.
- Cost and OpenRouter semantic egress are explicit startup flags, disabled by default. Missing, partial, malformed or mismatching cost results cannot become zero-priced budget passes. Model findings require exact known-source citations and cannot clear deterministic findings or operational uncertainty.
- Do not transform unverified ADR consistency, uptime percentages, data classification or backup/log topology into a clean pass. The supplied demo correctly transitions FAIL to WARN with remaining unknowns.
- Add optional reviewer.input_sha256 to the output schema, preserving prior sample compatibility. CI reruns against current explicitly selected file contents rather than trusting a prior result JSON.
- OpenSpec current review reports must be archived after a failed re-review; simply adding review.blocked.md while keeping an old review.md leaves tasks unlocked. Qualification tests that report-only operation explicitly.
- Spec Kit/OpenSpec agent instructions are not an unbypassable security boundary. Local tests qualify registration and artifact dependencies, not model/agent obedience.
- Use proposed review-hook-v0.1.0 tag namespace for later owner-approved publication; Architect v* tags can invoke its npm publisher. No tag has been created.
