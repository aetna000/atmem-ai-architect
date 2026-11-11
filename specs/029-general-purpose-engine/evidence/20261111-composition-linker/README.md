# GE-004 composition foundation — not an alpha.3 release

The previous goal turn delivered the owner-requested Design/activity patch. This
turn progresses the original generic-engine goal with a reusable capability
partitioner, explicit adapter registry and Terraform package linker. The default
public compiler is deliberately not switched until independent module admission,
implementation maps and all Spec Kit paths/DAGs are integrated. The original mixed
composition diagnostic remains unchanged and still describes the default export.

## Implemented invariant and interfaces

`planCapabilityComposition(project, contracts, planProject)` discovers only
explicit implementation contracts, partitions stable owned unit identities and
retains all whole-graph rows/interfaces, external ownership and unknown scope. It
knows no business domain, provider/service spelling or evaluation project identity.
Existing neighbors remain external references; proposed neighboring units cannot
be absorbed. Duplicate/ambiguous ownership is rejected or explicitly blocked.
Each unit retains original requirements/needs. Missing browser/accounting contracts,
unsupported limits and unknown inter-unit interfaces remain blocking gaps.

`DELIVERY_CAPABILITIES` registers the existing invoice-workflow domain policy and
supplied-image container-service adapter explicitly. The invoice policy is not
renamed as a generic application mechanism. `compileCapabilityComposition` checks
current plan identities/gaps and compiles one current mixed graph into module
packages. These pure JavaScript mechanisms perform no filesystem/account/harness
actions and preserve future browser/backend SaaS portability.

`composeTerraformUnits` preserves generated child resource/data/source/test bodies,
provides stable injective module/input identities, relocates provider configuration
and input validations to root variables and passes each explicit root provider
alias. Quoted literals, escaped interpolation, nested templates and object members
are distinguished when rewriting variable traversals. Inputs/files are not clipped
or overwritten; duplicate IDs, unsafe paths, nested/unreviewed Terraform structures
and incompatible reviewed provider locks fail explicitly. Root approval defaults
false; each original unit review gate remains. Unknown required interfaces still
block the root even after review. A child cannot select state for another unit;
production remains blocked pending whole-composition state/operations acceptance.

The linker exposed container IBM1.89 versus invoice IBM2.9. The container adapter
now uses the already reviewed pinned2.9 provider lock, leaving other compiler locks
unchanged. Its actual cached2.9 schema and all four footprint mock tests pass.
No provider fallback or incompatible-version selection is hidden.

## Validation

- `npm test`:429 pass,0 failed/skipped; `js-tests.log`.
- `npm run build`:pass; existing chunk advisory; `build.log`.
- `validation-summary.json`:14 independently initialized/schema-validated packages
  and61 mock-provider plan checks, all passing. Each command/stdout/receipt is
  retained in `v3-*` directories. Use only v3 for these denominators; earlier v1/v2
  receipts remain historical diagnostics and are not counted again.
- Four single-graph invoice+unfamiliar scientific-image compositions pass cached
  native provider schemas. Unknown scope, reorder/rename/Unicode identities,
  separate same-kind units and explicit externally owned services have component
  regression checks. Child source/resource bodies and tests are retained.
- Four standalone footprints each pass4 mock checks; invoice children pass9 AWS,
  11 Azure,10 Google and12 IBM checks after provider relocation.
- A five-unit composition spanning all four clouds, including repeated AWS units,
  passes a combined mock plan and a denied-unapproved plan. Adding an unknown
  required business interface produces the expected blocked-root mock plan.
- Source identities are recorded in `code-sha256.json`. Current backend source is
  unchanged; no new server test or model-inference qualification is claimed.

Reproduce from an installed checkout with the qualified cached provider mirror:

```sh
node scripts/engine-evaluation/compile-composition-probes.mjs .local/new-composition-probes
python3 scripts/engine-evaluation/check-composition-terraform.py --package .local/new-composition-probes/aws --terraform .venv/bin/terraform --mirror .local/provider-cache --evidence .local/new-aws-schema-evidence
python3 scripts/engine-evaluation/check-composition-terraform.py --package .local/new-composition-probes/cross-provider --terraform .venv/bin/terraform --mirror .local/provider-cache --evidence .local/new-cross-provider-evidence --test
```

Use new paths for each replay; existing evidence is never overwritten. The checker
uses only an explicit offline filesystem mirror and a credential-free environment.
It executes init -backend=false, validate and optional test mock plans, never apply
or an account plan. Receiving deployment/account prerequisites remain unverified.
Supplied-image paths do not implement new scientific application business logic.
No diagram, package or original client export was hand-patched.

## Remaining required work

1. Independently inspect the exact emitted module closure and nested resource
   addresses/provider arrays against expected project/contract identities. Retain
   arbitrary-module, execution-hook, credential and missing-resource failures.
2. Integrate resourcePlan/terraformSketch default dispatch only with that admission;
   preserve all existing regressions and strengthen the earlier mixed counterexample.
3. Update implementation maps and Spec Kit tasks/documents to iterate every unit
   with actual module paths, distinct task IDs/dependencies and concrete tests.
4. Qualify combined workflow/root mock assertions and public Design/export/browser
   behavior, additional domains/combinations and counterexamples; freeze a separate
   runnable alpha.3 only after its requirements pass.
5. Continue GE-005–GE-011, native comparison/holdouts and all original28 complete
   block/connection/system evaluations. No narrower success criterion replaces them.

GE-004 stays in_progress. Offered increments2/10, originals locally qualified1/28,
owner acceptance0 and95% quality unproven remain unchanged. Existing5284 alpha.2.1
and previous previews/stores remain intact. No cloud access/deployment performed.

Disk temporarily prevented new temp/source files. Reclaimed only seven completed
browser-fixture Vite caches and132MB of source-backed dependency .pyc caches,
retaining Python source, project stores, session logs, originals, reports, images,
provider mirrors and running previews. Cleanup manifests are retained. Initial
failed writes are excluded; v3 is the successfully generated/replayed current graph
pipeline. The first legacy v3 attempt wrote nothing because disk allocation failed.
