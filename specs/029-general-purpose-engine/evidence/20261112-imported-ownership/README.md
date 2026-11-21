# Imported deployment ownership guard

Reusable invariant: cloud-state metadata describes an existing deployment and
cannot be reinterpreted as existing application source to create new resources.
The JavaScript import/planner/compiler boundary and backend Data contract now
reject `origin = imported Pulumi state` with `deploymentMode = create`.
They preserve the submitted project and explain the correction: retain the
reference, or model a separate proposed deployment for new resources.

`before.json` records the ea855fb counterexample on all four providers: the same
combination was treated as new and emitted a managed native application resource.
No cloud resources or Terraform state were touched. Default/reference treatment
of imported deployments and explicit creation from existing application source
remain supported; the latter is a different ownership fact.

Four JavaScript regressions exercise import validation, planning and compilation,
input immutability, reference preservation and existing-source deployment on AWS,
Azure, Google and IBM. The backend regression independently checks the same four
providers through its real validation model. `js-tests.log` records505 passes,
`server-tests.log` records429 backend passes, and `build.log` records the successful
production build. Exact changed sources are bound in `source-manifest.json`.

`unchanged-placement-artifacts.json` confirms all twelve placement packages and
independent assertion hashes match the qualified final placement manifest after
this guard change. Native tests were not repeated or counted again. Heavy
regenerated packages remain on MEM0. No UI or running owner job was changed.

This is an ownership defect fix within GE-005, not completed lifecycle parity,
an implemented Terraform/Pulumi import or a migration. Actual state custody,
reference/import/create parity, deeper network/identity policy and runnable
alpha.4 remain. Full28 and unfamiliar local block/connection/system evaluation
remain required; no release, deployment or additional project acceptance is claimed.
