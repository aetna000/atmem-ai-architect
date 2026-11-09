# Infrastructure generation and validation research

Reviewed 2026-11-10. This research informs the generator; it does not certify any
library as universally correct. Repository status and licensing were checked via
GitHub repository metadata. No upstream deployment scripts were executed.

## Selected architecture

Use an explicit design/ownership model, typed provider compilers and independently
validated generated artifacts. Reuse maintained cloud modules where their contracts
fit. Pin and test versions before adding module dependencies. Skill guidance alone
is not proof that generated configuration implements a system.

| Project | Appropriate use | Important boundary | Decision |
|---|---|---|---|
| [terraform-aws-modules ECS](https://github.com/terraform-aws-modules/terraform-aws-ecs) | AWS ECS component design, interfaces, IAM and examples | Community maintained; review exact resource, module and AWS provider versions | Reference for AWS compiler; evaluate module-backed adapter |
| [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/) / [Container App](https://github.com/Azure/terraform-azurerm-avm-res-app-containerapp) | Reviewed Azure resource patterns and tests | Existing environment, identity and secret prerequisites remain meaningful | Reference for Azure compiler; evaluate pinned AVM adapter |
| [Cloud Foundation Fabric](https://github.com/GoogleCloudPlatform/cloud-foundation-fabric) | GCP modules and complete blueprints | Designed as a toolkit/fork; do not assume every module is a standalone drop-in | Reference for Google compiler and connected patterns |
| [IBM Code Engine modules](https://github.com/terraform-ibm-modules/terraform-ibm-code-engine) | IBM project/app/secret/binding composition | Exact project visibility, image secrets and provider limitations need verification | Reference for IBM compiler; evaluate pinned module adapter |
| [TFLint](https://github.com/terraform-linters/tflint) | Independent language/provider lint; structured diagnostics | Not business behavior validation. Core lint is not cloud-rule coverage. Plugin versions and licenses require review | Integrated optional server lint; v0.66.0 tested locally |
| [Checkov](https://github.com/bridgecrewio/checkov) | Graph/security policies, Terraform and plan scans | Policy coverage differs by provider; its documented Terraform support does not establish IBM coverage | Candidate additional policy adapter; not installed/integrated yet |
| [Trivy](https://github.com/aquasecurity/trivy) | IaC misconfiguration, dependency and image checks | A scan cannot establish application behavior; review IBM resource coverage | Candidate security/image adapter |
| [Terratest](https://github.com/gruntwork-io/terratest) | Real environment integration qualification | Typical tests apply/destroy infrastructure and require explicit account authorization | Later authorized staging qualification; not executed |
| [aztfexport](https://github.com/Azure/aztfexport) | Import existing Azure infrastructure | Maintainers explicitly state generated configuration may not fully reproduce infrastructure | Explicit import workflow only; never reference-only handling |
| [Terraformer](https://github.com/GoogleCloudPlatform/terraformer) | Historical reverse-engineering examples | Archived/deprecated March 16, 2026; no further support/security updates | Rejected as a new dependency |

Maintained status was observed for the selected AWS/Azure/Google/IBM reference
repositories, TFLint, Checkov, Trivy and Terratest. Licenses recorded by GitHub:
AWS ECS, Fabric, IBM Code Engine, Checkov, Trivy and Terratest Apache-2.0;
Azure Container App MIT; aztfexport MPL-2.0. TFLint's README additionally documents
BUSL-1.1-covered files and combined executable licensing; do not describe its binary
as solely MPL-2.0 based on GitHub's summary field.

## Engine alternatives

- [OpenTofu](https://opentofu.org/docs/intro/migration/): closest open-source engine
  alternative. Test configuration, provider and state compatibility before adopting;
  OpenTofu-specific features may affect Terraform compatibility. Not installed/tested
  in this batch, so exports do not claim dual-engine qualification.
- [Pulumi](https://www.pulumi.com/docs/iac/concepts/): typed TypeScript/Python and
  reusable components may simplify compiler engineering. Assess with the same cloud
  and workload fixtures. Its [provider bridge](https://www.pulumi.com/docs/iac/concepts/providers/any-terraform-provider/)
  can consume Terraform/OpenTofu providers, but that is not evidence that this app's
  current metadata-only Pulumi export is deployable. No engine switch performed.
- [CDKTF](https://developer.hashicorp.com/terraform/cdktf/release): deprecated by
  HashiCorp December 10, 2025; rejected as a new generation foundation.

## Implemented and observed

- Native private supplied-image container footprints for AWS Fargate, Azure
  Container Apps, Google Cloud Run and IBM Code Engine. These are AtMem compiler
  implementations, not vendored upstream module code. No claim of module integration.
- Real Terraform provider schema validation passed for all four generated footprints.
- Generated provider-mock tests: 16 passed; assert emitted name, immutable image,
  private exposure and rejection of unapproved/mutable-image inputs. No account plan
  or deployed runtime check was performed.
- Verified TFLint v0.66.0 darwin_arm64 archive against the upstream release checksum.
  Tested core recommended rules on all four outputs: zero issues/errors after fixing
  an unused Azure region variable. No third-party provider plugins loaded.
- Optional operator setting `ATMEM_ARCHITECT_TFLINT_BIN` enables the independent
  server-generated-config lint step. The runner uses its own trusted configuration,
  a private temporary HOME and a reduced environment; no automatic `--fix` mutates
  an export. Findings must be fixed in the generator and artifacts regenerated.

Provider schema and linter findings already caught real generator defects: invalid
IBM visibility and an unused Azure input. Continue independent checks during compiler
expansion; do not use an AI's assurance as an acceptance test.
