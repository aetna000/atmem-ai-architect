# Provider lowering and ownership parity

This describes the current supplied-image contract, combined with root ownership
inspection. It is not whole-application, effective-permission or availability proof.
Concrete resource/query inventories and native mock receipts are in
`specs/029-general-purpose-engine/evidence/20261112-lifecycle-ownership/provider-parity.json`.

| Contract | AWS | Azure | Google Cloud | IBM |
|---|---|---|---|---|
| Supplied image | ECS Fargate | Container Apps Consumption | Cloud Run | Code Engine |
| Exact memory | Native MiB/CPU combinations | Native GiB/CPU combinations | MiB and execution-generation constraints | Native decimal GB/CPU combinations |
| Configured region | Locked input/provider | Locked input plus existing environment location | Locked provider and service location | Locked provider plus existing project region |
| Existing prerequisites | Read-only explicit subnet/group IDs and VPC membership | Read-only managed environment, exact ARM ID/subscription | Existing project input | Read-only project region/account |
| Runtime identity | Separate empty application task role; scoped ECS execution trust/policy | System-assigned identity; no generated application grants | Dedicated service account; no generated application grants | No application service account |
| Private footprint | No public task IP | Internal ingress | Internal-only ingress | Local managed domain |
| Lifecycle | Managed supplied-image resources prevent destruction while configured | Same | Same plus native service deletion protection | Same |
| Reference/state metadata | Preserved externally, no managed addresses/adoption | Same | Same | Same |
| Existing source/create | Explicit supplied-image contract; separate deployment identity | Same | Same | Same |
| Root state choice | Explicit backend/owner/environment/residency contract independent of application target; acceptance stays unverified | Same | Same | Same |

Reference and observed Pulumi metadata remain distinct from native state adoption.
An implementation marker cannot override a reference. Raw inputs/outputs/credentials
are discarded; full supported URNs/types survive project persistence/export. Scope
changes invalidate context review rather than modifying old evidence. Unreviewed
state import/move/removal operations and forged inventory claims are rejected.

VPC membership/internal ingress do not prove routes, firewall/egress, effective IAM,
inherited rights or application access. Private registry credentials, application
contracts and regional service/model availability require their own implementation
and tests. Destruction protection can be removed by changing/removing configuration;
it is not backup or state custody. The local HTTP/SQLite state probe is not native
S3/Azure/GCS, TLS or project-backend acceptance.

The historical AWS China ARN counterexample is repaired for supplied-image units:
native aws_partition metadata supplies trust ARN partitions, and native guards
check region families and repository scope across commercial, China and GovCloud.
See `specs/029-general-purpose-engine/evidence/20261112-aws-partitions/README.md`.
The invoice adapter remains commercial-only and preserves other requested
partitions as explicit implementation blockers, including independent protection
against suppressed planner gaps. This is ARN/configuration behavior under local
mocks, not regional service availability or whole-application support. Other
partitions and future combinations need their own contract/evidence. All28
originals and unfamiliar complete local systems remain required.
