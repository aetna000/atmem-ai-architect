# Validate the generated implementation

1. Build runtimes with python3 build-runtime.py when present, then run the shipped app-tests. See BUILD.md for pinned dependencies.
2. Install Terraform 1.7+ (1.10+ for production state), run terraform init -backend=false, terraform validate and terraform test. Retain the provider lock file. Mock plans do not call AWS and intentionally fail for unresolved implementations.
3. Copy deployment.tfvars.json.example and replace every required placeholder with reviewed values. Leave review_approved false until requirements, costs, state, identities and permissions are reviewed. Credentials remain in the standard AWS credential chain.
4. Review effective IAM boundaries and organization policies. Scoped grants do not revoke broader existing permissions. API caller roles have only the generated route permission; end users must not have direct Lambda invocation or catalog write access.
5. Plan with terraform plan -var-file=deployment.tfvars.json -out=reviewed.tfplan. Run PREFLIGHT.md account checks. Apply only the exact reviewed plan after authorization.
6. Verify real application outputs, authenticated denials, recovery, updates/deletes, revocation and cleanup. For S3, verify byte-preserving and exact-version reads, encryption/versioning and anonymous denial. Use controlled identities without broader grants for negative tests.
7. Production storage prevents destruction. Deletion, retention and decommissioning need a reviewed lifecycle procedure; do not bypass protections merely to finish testing.

No execution evidence is embedded in a fresh export. Mock tests, control-plane access and an account plan do not prove deployed behavior or production readiness.
