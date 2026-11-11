# Provider-aware lowering

The first GE-005 mechanism carries exact container memory quantities from project
intent through provider configuration and independent artifact inspection. It
applies to any explicitly selected supplied-image container unit, including units
composed with an unrelated application workflow. It does not select a business
recipe or target provider from a project name, and it does not generate the image.

`config.containerMemoryBytes` is an exact safe integer. Legacy `memoryMb` means
MiB; both fields can coexist only when they agree. Every declared quantity remains
in project files and schedules. A provider mapping may choose compatible CPU as a
proposal but cannot round the quantity, change provider or claim performance.
Unsupported exact quantities and other constraints keep the missing-work gate.
AWS honors the existing CloudWatch finite retention field. Other provider logging
contracts and concurrent-request semantics are not inferred from different knobs.

Primary references, reviewed2026-11-11 (exact snapshots/hashes beside evidence):

- [AWS Fargate CPU/memory combinations](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html).
- [Azure Consumption CPU/memory allocation](https://learn.microsoft.com/en-us/azure/container-apps/containers#vcpu-and-memory-allocation-requirements).
- [Cloud Run memory/CPU and execution generations](https://docs.cloud.google.com/run/docs/configuring/services/memory-limits).
- [IBM Code Engine exact size combinations and decimal/binary units](https://cloud.ibm.com/docs/codeengine?topic=codeengine-mem-cpu-combo).

Provider source documentation is pinned to AWS6.72.0, Azure4.81.0, Google7.46.2
and IBM2.9.0; cached schemas/mock tests cover actual emitted fields separately.
Independent inspection parses actual native quantities, canonical ownership,
private ingress and explicit runtime identity; module metadata cannot disable it.
Separately authored native tests assert expected values rather than only asking
the lowering function to verify itself. This proves configuration behavior, not
application execution or cloud/account acceptance.

See `specs/029-general-purpose-engine/evidence/20261111-provider-lowering/README.md`
for executable evidence, exact supported scope and remaining region/network/
identity/lifecycle/state policy work before alpha.4.

Configured placement now follows the same explicit contract through standalone
and composed supplied-image units. A known canonical region becomes a validated
input bound to that unit's provider and native location; changing it requires
regeneration. An unknown region has no default destination. Unsupported identifiers
retain blocking scope. Existing invoice-region policy is reused without claiming
that identifier syntax proves service availability. Proposals remain proposals.

Azure reads the exact existing managed environment and checks location and ARM ID;
IBM reads the existing Code Engine project and checks region and account. These
are read-only references. Independent inspection rejects changed provider bindings,
removed guards and extra resources/queries outside the supplied-image footprint.
Parent review gates can defer child lookups; unit mock plans exercise resolved
fixtures without weakening those gates. This is not cloud observation or complete
IAM/lifecycle/state-policy acceptance. Pinned native sources and the old compiler
counterexample are in
`specs/029-general-purpose-engine/evidence/20261112-provider-placement/README.md`.
