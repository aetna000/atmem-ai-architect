# Four-cloud AI workload qualification

The product target is a consultant that helps a junior developer progress from a plain-language AI use case through a complete architecture, tested implementation and an explicitly approved deployment. Private storage is a foundation, never a substitute for the requested application.

## Coverage and acceptance

The executable scenario registry is `src/ai-qualification-scenarios.mjs`: ten workload families × AWS, Azure, Google Cloud and IBM = forty prompt/acceptance cases. It includes IoT, logs/traces, permission-aware RAG, chatbots, version control, predictive maintenance, customer support, call-center/CRM, cloud operations and cybersecurity. Each defines five behavioral acceptance checks and a focused discovery question. Service names alone never establish coverage.

Every case must progress through independently recorded stages:

1. Real prompt in the UI; preserve full response, proposals, diagram, requirements, decisions and model/provider identity. Evaluate connected ingestion → application/model → output paths and existing-system preservation.
2. Native Terraform and runtime generation for every required component/edge. Unimplemented components remain visible. Required scope cannot become a note or disappear to obtain a green result.
3. Real provider schema validation and mock plans, with negative gates. Mock identity results are not IAM evidence.
4. Generated runtime tests against stateful APIs. Test normal behavior, malformed/missing/duplicate/stale input, permissions, model outage, injection, retry, recovery and cleanup where applicable. Model fixture checks and real model quality evaluations are separate.
5. Mentor response: summarize demonstrated progress, explain the most material next issue, propose a supported correction, or ask one focused decision question. Applied changes are visible and undoable. Automatically retest at most two corrections; never silently loop forever.
6. Exported bundle and report hashes match the exact tested artifact. Any change invalidates that evidence. Record time, environment, backend/version, limitations, errors and cleanup.
7. Separately authorized real-account plan, cost reconciliation, deployment, acceptance tests and teardown. Production qualification additionally requires identity/network policy, remote state/locking, recovery, monitoring, ownership and operational review.

## No false completeness

The forty scenarios are a qualification backlog until their individual evidence exists. S3 compatibility is not an IBM control-plane emulator. Azure/GCP storage API emulation does not validate managed AI services. A threshold-based sensor fixture is not evidence of a trained predictive model. Deterministic generated answers are not model quality. No aggregate confidence score may hide an unimplemented critical path.

Website hosting retains browser/API/worker separation. Public multi-tenant execution additionally requires authenticated tenant scoping, jobs, quotas, OS-level network isolation, CPU/memory limits and secret isolation; local subprocess tests cannot qualify that deployment.
