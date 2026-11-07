# Verify account prerequisites before applying

After reviewing `terraform plan -out=reviewed.tfplan`, write `terraform show -json reviewed.tfplan > reviewed-plan.json`. Treat both files as sensitive. Create a local Python virtual environment and install `preflight-requirements.lock` using `pip install --require-hashes --only-binary=:all: -r preflight-requirements.lock`. With the standard AWS credential chain set to the reviewed account, run `python preflight-aws.py --plan-json reviewed-plan.json --receipt preflight-receipt.json`.

The script reads STS identity, regional Lambda reservation capacity and selected Bedrock model control-plane availability. It never creates resources, changes quotas or invokes a model. A quota shortfall must be resolved before apply; do not remove concurrency limits to bypass it. Bedrock catalog access is not proof of Converse runtime access or model quality.

Apply only the reviewed plan after all account, policy, cost, operational and application checks are satisfied. Rerun checks when the plan or account changes.
