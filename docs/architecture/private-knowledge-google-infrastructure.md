# Google private-document substrate compiler

`googleDocumentJobTerraform` in `src/enterprise-google-infrastructure.mjs` emits
the native parser substrate from the owned project, source-component address,
selected canonical region and environment. This is a compiler building block,
not a registered complete private-assistant export. Existing worker identity,
sources, company sign-in, website and unrelated IAM memberships are preserved.

The module supplies native Terraform, official Google/google-beta 7.46.2 locks,
destination examples, a scope boundary, operating notes and eleven executable
provider mock plans. No published image, source registration, cost or account
approval is invented. Image/configuration output remains null during foundation;
reviewed immutable parser/transfer artifacts and a qualified parser revision are
required to enable that output. Format checks do not establish artifact provenance.

## Resource and runtime connections

- Enable compute, Batch, IAM, storage, Artifact Registry and DNS APIs without
  disabling them on destroy. Materialize the native Batch service identity and its
  service-agent role; do not attach that role to the application worker.
- Create a separate transfer VM identity with Batch state reporting, repository
  read access and bucket-bound get/create only. The existing question worker gets
  four explicit project-scoped Batch control permissions, actAs on this VM identity
  only and bucket-bound get/create/delete. No model, source, SQL, secret-manager,
  generic administrator or project-wide actAs grant is emitted. Existing inherited
  privileges still require destination inspection.
- Create a nonpublic regional temporary bucket with uniform access, no versioning,
  no soft deletion and no force-destroy. Ordinary controller cleanup deletes its
  objects. Prefix-scoped age-one-day lifecycle is an asynchronous fallback request,
  not a maximum retention guarantee. Durable crash reconciliation is still required.
- Create an isolated custom subnet with Private Google Access and no default
  internet route, NAT or peering. Private `googleapis.com`/`pkg.dev` DNS routes APIs
  and image pulls through the private API VIP; explicit routes/HTTPS allow rules
  cover that VIP and the documented direct-connectivity range. Deny remaining
  egress and ingress. Native VM requests separately disable public IPs and block
  parser-container networking. Mock plans do not demonstrate real connectivity.
- Emit the exact ten-field `enterprise-google-document-job-v1` configuration only
  after its full substrate dependency graph. The existing runtime parser consumes
  actual positive mock-plan output, produces a Batch request and passes independent
  validation against the pinned official discovery schema.

The runtime controller configuration is now immutable. Its factory binding checks
selected provider, project, region and the existing SQL/worker service-account
identity before secret materialization or remote work. A caller cannot accidentally
route an AWS worker through Google or process a Google question in another target.
Other owned legacy execution ports retain their existing contract; this hook does
not establish isolation or provenance for arbitrary callbacks.

## Reproduced defect and repair

A synthetic imported component ID containing `${file("literal-evaluation-probe.txt")}`
and a `%{if ...}` directive was initially evaluated by Terraform in review metadata.
The fixture file contained an authored marker, never client data. All eleven
provider tests passed, but an independent plan-provenance check correctly failed:
schema/mock success alone did not preserve the source identity.

The emitter now escapes literal `${` and `%{` sequences in that data field while
retaining the original ID in its non-Terraform boundary record. It also verifies
that the resource address is the complete canonical UTF-8 encoding of that ID.
Unresolved/injected region expressions and another component's address are refused.
Real native plans verify byte-for-byte source-ID preservation after Terraform
interprets the JSON; this is stronger evidence than checking the escaped source.
Both the original failing plan/source snapshot and the repaired plans are retained.

The first networking test also exposed a set/list comparison in the test itself.
The repair compares exact sets without changing the emitted firewall or DNS rules.

## Verification and remaining work

Run these local, credential-free qualifications into fresh `.local` directories:

```sh
node scripts/qualify-enterprise-google-infrastructure.mjs .local/NEW
.local/durable-runtime/bin/python -I scripts/verify-google-document-configuration.py .local/NEW
node scripts/qualify-enterprise-google-infrastructure.mjs .local/NEW-LITERAL --literal-probe
.local/durable-runtime/bin/python -I scripts/verify-google-document-configuration.py .local/NEW-LITERAL
```

The independent verifier selects the actual positive plan, checks all eleven
native tests ran, binds its output to the runtime's reviewed fixture target and
validates the resulting request against the official schema. Expected-failure
plans are not treated as usable runtime configurations. Separate SQL factory tests
exercise a queued answer through the real Google controller with scripted native
HTTP; real DOCX/PDF transfer/parser execution remains separately qualified in Linux.

Complete the application/worker and artifact-build wiring, durable orphan
reconciliation, actual retention/VM termination, key/audit recovery, account IAM/
DNS/network checks when authorized and the remaining AWS/Azure/IBM launchers.
Complete private-project exports and the medium/hard/final-28/held-out evaluations.
Security remains unaccepted. No cloud plan, apply or deployment was performed.

Primary references reviewed 2026-11-11:
[Batch roles](https://docs.cloud.google.com/iam/docs/roles-permissions/batch),
[Batch prerequisites](https://docs.cloud.google.com/batch/docs/get-started),
[Private Google Access](https://docs.cloud.google.com/vpc/docs/configure-private-google-access),
[Artifact Registry private access](https://docs.cloud.google.com/artifact-registry/docs/securing-with-vpc-sc),
[soft-delete behavior](https://docs.cloud.google.com/storage/docs/soft-delete).
These establish documented mechanisms; the exact pinned provider schemas and local
plans are retained as separate evidence from native-account operation.
