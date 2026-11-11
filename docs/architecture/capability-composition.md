# Capability composition foundation

Status: GE-004 implementation in progress. The public export compiler still uses
its established dispatch until module admission and handoff paths are integrated.
This document describes working internal APIs, not a released alpha.3.

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
