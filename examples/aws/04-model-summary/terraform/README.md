# AtMem AI Architect Terraform sketch

Revision r2; staging.

Explicit proposed S3 blocks get native resources: a bucket, public-access block, encryption, versioning, bucket-owner-enforced ownership and a deny-insecure-transport policy. Buckets prevent destruction. Typed existing IAM-principal bindings and direct s3-read/s3-read-write edges generate required same-account role/user ARN inputs and bucket-scoped access policies. Labels alone never grant permissions. Read includes versioned reads; write adds PutObject, not deletion. Existing identities are not created or changed. Other IAM, model access, application code, network policy, services and integrations still require engineering work. Typed text-statistics Lambda components additionally generate a tested handler, execution role, scoped logging, published version, live alias and caller permission. Other workloads remain incomplete; this is not a complete deployable application unless all required implementations and integrations are covered and verified.

Default review gate prevents a successful plan; unresolved work also blocks it. Review resource-schedule.json and the architecture document, implement missing generator capabilities and regenerate from the project; do not hand-clear unfinished_work to make a plan pass.

For production, read STATE.md and supply the reviewed S3 backend configuration; local state is for staging validation only. Build packaged runtimes first using python3 build-runtime.py when present (see BUILD.md). Run the shipped Python application tests where present: python3 -m unittest discover -s app-tests -p '*_test.py'. Run terraform test for generated mock-provider checks.

On your own machine: install Terraform, review provider version constraints, then run terraform init -backend=false and terraform validate. Retain the generated provider lock file. Configure the standard AWS credential chain separately; never put credentials in project files. Supply aws_region, aws_account_id and every generated principal_*_arn input to terraform plan. Principal ARNs must identify existing roles/users in that account; root/session/wildcard and cross-account bindings are rejected. Review inherited IAM permissions, permission boundaries and organization policies separately: a scoped bucket grant does not revoke permissions granted elsewhere. Run the read-only account prerequisites in PREFLIGHT.md. Review the actual account, region, changes, costs and permissions before approving any apply. This export carries no validation evidence. Use AtMem AI Architect’s Terraform → Test Terraform view to run local schema checks. No cloud plan or deployment has been validated.

Review AES256 versus customer-managed keys, retention, version-storage cost, access policies and state storage against your requirements. The diagram's region is documented but not silently used; aws_region must be deliberately supplied.

References:
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning
- https://developer.hashicorp.com/terraform/language/resources/terraform-data
