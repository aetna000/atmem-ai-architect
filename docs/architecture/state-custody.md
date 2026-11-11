# Whole-project Terraform state

Application target and state backend are separate choices. An existing platform
backend belongs to its recorded owner and must not be replaced because the
application targets a different provider. The generic root contract is optional:

```json
{
  "version": 1,
  "environments": {
    "production": {
      "backend": "gcs",
      "owner": "Existing platform team",
      "residency": "Australia required; destination unverified",
      "decisionId": "state-choice"
    }
  }
}
```

Store it as `project.extensions.terraformState`. Supported backend contracts are
s3, azurerm, gcs and http. Unsupported choices or fields are rejected without
truncation or substitution; preserve the original record and implement the missing
adapter. No bucket, endpoint, private path or credential is inferred from owner or
residency text. Existing invoice provider defaults remain a compatibility policy.

The generator emits the selected backend at the root, private-input placeholders,
STATE.md, state-custody.json and a concrete Spec Kit verification task. Children
keep their original resources/tests and no backend. A choice, context review or
Accepted decision never sets migration/operating acceptance. Review remains false,
and custody acceptance remains blocking. Backend settings and the recorded owner,
environment and decision are checked independently of emitted metadata.

Before any separately authorized destination work, verify custody/access, namespace,
encryption, locking and version recovery. A migration additionally needs a verified
private backup, lineage/serial/resource inventory, writer freeze, approved plan and
rollback evidence. Do not use initialization errors as permission to migrate or
reconfigure. State and saved plans can contain sensitive values; they and backend
credentials stay outside generated source. Local programme qualification does not
require cloud account access or migration.

See the source-bound native/configuration checks and precise limits in
`specs/029-general-purpose-engine/evidence/20261112-state-custody/README.md`.
