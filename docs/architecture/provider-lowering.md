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
