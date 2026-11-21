# Generated S3 operator access

Implement the missing storage scenario end to end through the project model, architect proposals, durable project files, resource schedule and native Terraform generator.

A typed existing IAM-principal reference and typed S3 read/read-write edge generate a required principal ARN input and bucket-scoped permissions. Never infer grants from free-text labels. Do not create or mutate existing identities. Accept only IAM role/user ARNs in the selected account; reject root, wildcard, session and cross-account principals. No delete grants. Keep versioned reads, TLS denial, encryption, ownership and public-access blocking. Unrecognized integrations remain blocked.

Acceptance: typed proposal and save/reopen round trip; exact least-privilege policy assertions; invalid-contract negative tests; provider-schema and mock plans for both access modes, wrong account, invalid ARN and unresolved integrations; live model UI export. Account-specific plans and deployed behavior are distinct evidence stages.
