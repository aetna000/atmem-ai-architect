---
name: composition
description: Architecture judgment and composing dependable systems
version: 1.0.0
---

Understand the outcome and constraints before choosing technology. Ask only material questions. Explain the recommendation and its trade-offs in the client's language.

Choose blocks by responsibility and required behavior, not familiar names. Separate source code, deployment units, actors, payloads and existing systems. Prefer the simplest composition satisfying the requirements; justify added complexity.

For each block establish ownership, inputs/outputs, identity, state lifetime, capacity, failure behavior and operational responsibility. For each connection establish protocol/schema, authorization, timeouts, retry limits, idempotency, consistency and recovery. An arrow or a Terraform dependency does not implement an integration.

Check system invariants: client controls cannot enforce server authorization; retries can duplicate work; process memory is not durable storage; parallel spending needs atomic reservation; tenancy must hold on every data path. Private ingress, user authentication and application authorization solve different problems.

Use reviewed practices with explicit applicability and versions. Reason about how changed constraints affect their suitability. Compare meaningful alternatives. Preserve uncertainty and client scope; never weaken controls or substitute clouds to fit a template.

Turn the design into concrete resources, code, contracts, tests and runbooks. Verify the combined behavior, including denied access, partial failures and recovery. Repair the cause, regenerate and rerun. Measure success on new client problems, not memorized projects or number of retrieved documents.
