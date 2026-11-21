# Component-owned application source selection

A proposed non-note component can select `implementation=approval-workflow` and
carry its complete `approvalProfile`. The profile must match that exact component
ID/provider and retain its source, destination, operation policy, logical account,
environment and native identity settings. Existing/imported systems and reference
bindings cannot become new applications through this declaration.

The structured producer validates the same pure Python `ApplicationProfile` used
by delivered runtimes. Its module needs no database, identity SDK or cloud request.
Browser/import/export validation enforces the same bounded declaration language;
a cross-language corpus checks positive and negative cases. Save/reopen retains
the whole declaration. It is part of the component's architecture-work basis, so
changing it invalidates prior context review while retaining earlier snapshots.

Projects selecting this new intent use project file3.0.0. Ordinary projects retain
2.3.0; this reader accepts older files. A3.0 file requires the supported approval
intent and its normal component validation. Older previews reject the new major
version instead of silently dropping the intent/declaration during import. Do not
strip a version marker to make an older preview open a file. Roll back with the
older candidate's own unchanged store and preserve new files/history separately.

The actual Terraform/delivery export now carries the component-bound profile,
shared API runtime, `api:app_factory`, provider dependency lock, Dockerfile and
assembly-status record under `applications/<resource-address>/`. Only shared
mechanisms/native adapters are included; invoice business code is not selected
by this intent. The API entrypoint has internal connection/key-source injection
for local qualification; HTTP/profile data cannot set these arguments.

The source selector does not claim provider infrastructure or domain behavior.
Resource planning keeps the component unimplemented even if its label/service
still says S3. Independent generation-quality admission rejects a forged completed
row. `assembly-status.json` records missing domain/worker, provider/environment/
identity/database linkage and operating acceptance; environment contradictions
remain explicit. There is no dummy worker, automatic schema migration or work-gate
removal. The implementation map names the state `shared_api_assembly_only`.

The Spec Kit links real emitted files and the original requirement/component IDs.
Its application-source task follows setup/security work and precedes the component
resource task. That task requires real domain/worker source and local positive/
negative checks; dependent resource/integration tasks still own native linkage
and actual destination compatibility. No task is automatically completed.

The source-assembly registry is separate from reviewed Terraform resource contracts.
Planner/native handoff guidance states this limited applicability and forbids
inventing native IDs or substituting business recipes. A missing profile stays
missing while choices are unresolved. Full intent-to-template/deferred output
binding, native resource/environment linkage, executable worker/domain code and
connected whole-system acceptance remain required before alpha.5. The engine must
derive routine machine bindings from reviewed resources, rather than ask clients
to invent provider IDs or discard their existing systems.
