# Capability composition foundation

Status: the public compiler, independent module admission, implementation map and
Spec Kit now use capability composition. Four-provider service and browser checks
pass; the frozen runnable alpha.3 must still be verified before release.

The core partitions explicitly contracted delivery units from a complete design,
retaining existing neighbors and every unresolved requirement/interface. A reviewed
adapter owns a unit's concrete domain/provider policy. Its generated package enters
a shared linker that scopes files/resources in local modules, lifts provider
configuration and reviewed variables to the root, passes explicit provider aliases
and preserves child gates/tests. Labels, business names and corpus IDs never choose
an adapter. Requirement changes and unknown links remain visible; unit structure
and Terraform schema checks do not establish complete application coverage.

The current registry supports the existing invoice workflow and supplied-container
footprint. More contracts must implement their real behavior and transfer tests;
adding an ID or clearing a gap does not add capability. Whole-project root state
custody and operating responsibilities require separate acceptance; a child's
backend is not inherited by other units. No Terraform apply is authorized.

Primary implementation references:

- [Terraform providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers): provider configurations belong at the root; explicit mappings permit distinct configurations of the same provider.
- [Terraform JSON configuration syntax](https://developer.hashicorp.com/terraform/language/syntax/json): strings and expression contexts require deliberate handling during variable relocation.
- [IBM provider2.9 Code Engine app contract](https://raw.githubusercontent.com/IBM-Cloud/terraform-provider-ibm/v2.9.0/website/docs/r/code_engine_app.html.markdown): pinned source reviewed for compatibility with the common2.9 lock; cached native schema/mock checks remain distinct from cloud behavior.

Current executable evidence and exact limits:
`specs/029-general-purpose-engine/evidence/20261111-composition-linker/README.md`.

Long component identities retain their raw values in project, requirements and
manifest records. Filesystem/resource tokens keep the established full UTF-8 hex
encoding through 124 bytes; longer IDs use a `d` prefix and SHA-256 digest via
exactly pinned @noble/hashes 2.4.0. The odd-length digest token cannot overlap the
even-length full-hex encoding. Duplicate/colliding identities stop generation
before overwriting files. This bounds path components for valid Unicode IDs and
preserves existing short addresses. Existing state that used longer addresses
requires explicit migration review; this release performs no state migration.

Explicit runtime settings on supplied-image container footprints are retained as
blocking implementation gaps until provider lowering implements and independently
validates them. A default footprint must not claim that an explicit memory,
retention or concurrency requirement was implemented.

Public evidence, including seven browser exports, actual four-provider native
schema/unit mocks, five-unit combined-root assertions and Unicode unpack checks:
`specs/029-general-purpose-engine/evidence/20261111-public-composition/README.md`.
