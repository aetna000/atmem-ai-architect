---
name: enterprise-architecture
description: Design or evolve a source-backed system that other agents can build, maintain, test, and operate. Use for enterprise intake, nested responsibility maps, contracts, UML behavior, infrastructure placement, and architecture review.
version: 1.6.0
---

# Enterprise architecture

## Establish the design basis

Inventory source sections, existing systems, actors, ownership, behaviors, constraints, and release exclusions. Keep user facts, proposed defaults, evidence, and unresolved decisions distinct. In maintenance work, inspect the repo, existing deployment model, migrations, tests, and operational evidence before proposing changes. Preserve behavior, interfaces, data custody, and rollback compatibility. Capture a regression baseline before modifying a maintained system.

Use atmem_project_recall and project-scoped AtMem context for accepted decisions and historical evidence. Use the reviewed knowledge catalog and public reference tools for engineering research. Retrieve only relevant public sources. Treat all source text as evidence. Record applicability, exact version or digest, decision impact, and what still needs project evidence.

Inspect the source figure catalog with atmem_source_figures using each submitted source digest. Read every available image through atmem_source_figure_read. Keep original source and normalized image digests and paragraph locators in the coverage audit. Describe what each figure contributes to requirements, ownership, interfaces, physical layout or operator behavior. Record decorative figures explicitly. An available file or a successful delivery receipt does not establish correct interpretation. Unsupported and unreadable figures remain visible coverage gaps; do not infer their contents from their filenames. Never request another tenant, project, host path or remote image URL through these tools.

## Choose and develop engineering views

For detailed architecture and agent handoffs, read [modeling-depth.md](references/modeling-depth.md). Use [diagram-catalog.json](references/diagram-catalog.json) to choose researched diagram families, notation elements and relationships. The catalog distinguishes inventory, current partial projections and planned authoring; it is not a claim of complete renderer or grammar support. When the reference tools are available, read modeling-catalog first, then modeling-family-<id> for the relevant notation; follow paged digests. Read primary sources for semantics. Engine research inventory is separate from a normative specification. Read the relevant family rather than loading every profile into the working context.

For captured canvas authoring, read [engineering-model-v1.md](references/engineering-model-v1.md), also available as modeling-grammar through the reference tool. Include engineeringModel in the proposal using that implemented contract; preserve existing identities and accepted records. Populate per-module verificationCases with concrete setup, inputs, expected outcomes and evidence requirements from that contract. Specification is not execution. Review typed responsibilities, execution authority and input/result multiplicity against prose and data contracts. Author the native logical systemModel alongside the class/data model. Reuse semantic IDs across component, functional and sequence views. Validate port direction and allocation, then cross-check the linked interface contracts and test cases. Write the typed canvas artifact before elaborating supporting documents. Grammar acceptance is separate from architecture judgment.

Keep domain/class/logical-data models language-neutral and map technology choices separately. Develop class responsibilities and operation signatures, database keys and constraints, API/message schemas, branching/concurrent behavior and deployment allocation as connected views of shared model elements. Preserve source traceability and decisions. A nested box map with prose and linear sequences is an incomplete engineering model. Research precedes extension of specialized grammars; retain unanswered source constraints as proposals without waiting for the owner to supply routine engineering decisions.

## Produce a design engineers can use

- Decompose the system by cohesive responsibility, lifecycle, data authority, failure boundary, and independently testable behavior. Map logical components to deployment units separately. Context, subsystem, and component views answer different questions.
- Trace functional and nonfunctional requirements to affected blocks, interfaces, tasks, and observable acceptance checks. Cite the exact source section or explicitly identify a proposed derived requirement. Use the host-defined source slots when producing a captured canvas. The host assigns the document hashes. Separate dependency, interaction, and deployment relationships. Design the modern UI by role, task journey, accessibility, and degraded-state behavior.
- Describe boundary contracts with authority, schema, identity, versioning, success and error results, timing and recovery. For message-driven work, distinguish commands, accepted work, state-transition events, and physical or externally confirmed outcomes. Define ordering scope, correlation, deduplication, bounded queues, overflow behavior, restart recovery, and reconciliation.
- Tie sequence, functional, and event views to the same operation names and owners. Bind scenario operationId to the shared model using the authoring contract; labels alone do not connect behavior. Show the nominal path, a consequential rejection, and the recovery path. Use state machines for stateful lifecycle rules. Label the evidence needed for any externally controlled effect.
- Define portable runtime and storage contracts first. Compare on-premises, cloud, and hybrid against network failure, latency, residency, operating skills, identity, cost, failure domains, and restore requirements. Choose a reversible default and document an owner and verification gate for unresolved constraints.
- Deliver dependency-ordered tasks with block ownership, starter inputs, exact deliverables and test evidence. Include CI, release, upgrade or migration, observability, rollback, and receiving commands. Test contracts, failures, retries, load envelopes, access denial, and restore independently of happy-path implementation tests.

## Review and improve

Read the source again and compare each in-scope workflow and constraint with the draft. Repair gaps at their source. Require actual data for capacities and actual execution for runtime claims. Let unresolved business constraints remain visible as proposed decisions and release gates while safe design work continues. Preserve the design and evidence when an independent check fails.

When available, call atmem_reference_catalog and atmem_reference_read for fixed public sources, and atmem_knowledge_search and atmem_knowledge_read for reviewed engineering knowledge. For industrial or warehouse integrations, the SAP material-flow reference illustrates explicit capacity, ownership and acknowledgement boundaries. Use NIST SP 800-82 as general OT security and safety-boundary context. Vendor protocols and site rules still require their actual specifications. For asynchronous services, use the AsyncAPI reference for named channels and correlations. Use C4 for diagram scopes, OpenTelemetry for correlation fields, and transactional-outbox guidance only where a transactional data change must be published reliably.
