mock_provider "ibm" {
 override_during = plan
 mock_data "ibm_code_engine_project" { defaults = { account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", region = "au-syd", resource_group_id = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", crn = "crn:v1:bluemix:public:codeengine:au-syd:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:11111111-1111-1111-1111-111111111111::" } }
 mock_resource "ibm_resource_instance" { defaults = { account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", id = "crn:v1:bluemix:public:cloud-object-storage:global:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:55555555-5555-5555-5555-555555555555::", guid = "55555555-5555-5555-5555-555555555555" } }
}

variables {
review_approved = true
account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
region = "au-syd"
code_engine_project_id = "11111111-1111-1111-1111-111111111111"
registry_namespace = "reviewed-namespace"
registry_pull_secret = "reviewed-registry-pull"
block_666171_name = "reviewed-public-help"
block_666171_image_repository = "architect/public-help"
block_666171_image_digest = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
block_666171_watsonx_project_id = "22222222-2222-2222-2222-222222222222"
block_666171_runtime_instance_id = "33333333-3333-3333-3333-333333333333"
block_666171_model_id = "ibm/reviewed-model"
block_666171_editor_access_group_id = "AccessGroup-44444444-4444-4444-4444-444444444444"
block_666171_catalog_bucket = "reviewed-public-catalog-unique"
block_666171_policy_review = {"accountId":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","projectId":"22222222-2222-2222-2222-222222222222","runtimeInstanceId":"33333333-3333-3333-3333-333333333333","region":"au-syd","model":"ibm/reviewed-model","retentionReview":"REVIEW_REQUIRED","approvedBy":"REVIEW_REQUIRED","evidenceSha256":"0000000000000000000000000000000000000000000000000000000000000000","expiresAt":"REPLACE_AFTER_REVIEW"}
}
run "block_666171_sydney_registry" {
 command = plan
 assert {
 condition = var.region != "au-syd" || startswith(ibm_code_engine_app.block_666171.image_reference,"au.icr.io/")
 error_message = "Sydney uses au.icr.io; region concatenation cannot select a valid registry."
 }
}
run "block_666171_public_boundary" {
 command = plan
 assert {
 condition = ibm_iam_trusted_profile_policy.block_666171_catalog.roles == tolist(["Object Reader"]) && ibm_iam_trusted_profile_policy.block_666171_catalog.resources[0].resource_type == "bucket" && ibm_iam_trusted_profile_policy.block_666171_catalog.resources[0].resource == var.block_666171_catalog_bucket
 error_message = "Runtime may read only the dedicated catalog bucket; no write or public-access grant."
 }
 assert {
 condition = toset(ibm_iam_access_group_policy.block_666171_editor.roles) == toset(["Object Reader", "Object Writer"]) && ibm_iam_access_group_policy.block_666171_editor.resources[0].resource_type == "bucket" && ibm_iam_access_group_policy.block_666171_editor.access_group_id == var.block_666171_editor_access_group_id
 error_message = "Separate existing editors have bucket-scoped object access, never Manager or bucket Writer."
 }
 assert {
 condition = !ibm_cos_bucket.block_666171.force_delete && ibm_cos_bucket.block_666171.object_versioning[0].enable && ibm_code_engine_app.block_666171.run_compute_resource_token_enabled && ibm_code_engine_app.block_666171.run_as_user == 10001
 error_message = "Protect catalog recovery and use nonroot keyless compute identity."
 }
}
run "block_666171_mutable_image_blocked" {
 command = plan
 variables { block_666171_image_digest = "latest" }
 expect_failures = [var.block_666171_image_digest]
}
run "wrong_account_blocked" {
 command = plan
 variables { account_id = "cccccccccccccccccccccccccccccccc" }
 expect_failures = [terraform_data.review_gate]
}
run "unapproved_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
