# Decisions

- Explicit `data.binding=aws-iam-principal` and edge `access=s3-read|s3-read-write` are required; free text cannot grant permissions.
- Supply reviewed existing IAM role/user ARNs at Terraform plan time. Same-account commercial AWS only; no root, wildcard, session or cross-account principals. No existing identity is created or mutated.
- Scope grants to the referenced generated bucket. Read grants include versioned reads; write adds PutObject, not deletion. This does not revoke permissions from other IAM policies.
- Keep production data destruction protected. Preserve unknown integrations as genuine blockers.
- Ship mock-provider tests and explicit deployment inputs in the generated package. No validation receipt is fabricated inside an unexecuted export.
