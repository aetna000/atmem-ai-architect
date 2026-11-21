mock_provider "ibm" {
 override_during = plan
 mock_data "ibm_code_engine_project" { defaults = { account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", region = "au-syd", resource_group_id = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", crn = "crn:v1:bluemix:public:codeengine:au-syd:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:11111111-1111-1111-1111-111111111111::" } }
}
variables {
review_approved = true
account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
region = "au-syd"
code_engine_project_id = "11111111-1111-1111-1111-111111111111"
registry_namespace = "reviewed-namespace"
registry_pull_secret = "reviewed-registry-pull"
block_776f726b7370616365_name = "reviewed-ai-app"
block_776f726b7370616365_image_repository = "architect/app"
block_776f726b7370616365_image_digest = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
block_776f726b7370616365_watsonx_project_id = "22222222-2222-2222-2222-222222222222"
block_776f726b7370616365_runtime_instance_id = "33333333-3333-3333-3333-333333333333"
block_776f726b7370616365_model_id = "ibm/reviewed-model"
block_776f726b7370616365_appid_plan = "graduated-tier"
block_776f726b7370616365_authorized_user_subjects = []
block_776f726b7370616365_policy_review = {"accountId":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","projectId":"22222222-2222-2222-2222-222222222222","runtimeInstanceId":"33333333-3333-3333-3333-333333333333","region":"au-syd","model":"ibm/reviewed-model","retentionReview":"REVIEW_REQUIRED","approvedBy":"REVIEW_REQUIRED","evidenceSha256":"0000000000000000000000000000000000000000000000000000000000000000","expiresAt":"REPLACE_AFTER_REVIEW"}
}
run "block_776f726b7370616365_sydney_registry" {
 command = plan
 assert {
 condition = var.region != "au-syd" || startswith(ibm_code_engine_app.block_776f726b7370616365.image_reference,"au.icr.io/")
 error_message = "Sydney image pulls must use au.icr.io, never a region-derived invented registry."
 }
}
run "block_776f726b7370616365_identity" {
 command = plan
 assert {
 condition = ibm_code_engine_app.block_776f726b7370616365.run_compute_resource_token_enabled && ibm_code_engine_app.block_776f726b7370616365.run_as_user == 10001
 error_message = "Use nonroot Code Engine compute identity."
 }
 assert {
 condition = ibm_appid_application.block_776f726b7370616365.type == "singlepageapp" && !ibm_appid_idp_cloud_directory.block_776f726b7370616365.signup_enabled && !ibm_appid_idp_google.block_776f726b7370616365.is_active && !ibm_appid_idp_facebook.block_776f726b7370616365.is_active && !ibm_appid_idp_saml.block_776f726b7370616365.is_active
 error_message = "Only admin-enrolled scoped users belong in this owned App ID tenant."
 }
 assert {
 condition = ibm_iam_trusted_profile_policy.block_776f726b7370616365.resources[0].resource_instance_id == var.block_776f726b7370616365_runtime_instance_id && ibm_iam_trusted_profile_policy.block_776f726b7370616365.resources[0].service == "pm-20" && ibm_iam_trusted_profile_policy.block_776f726b7370616365.roles == tolist(["Writer"])
 error_message = "No account-wide model grant or substituted service."
 }
 assert {
 condition = ibm_iam_trusted_profile_link.block_776f726b7370616365.cr_type == "CE" && ibm_iam_trusted_profile_link.block_776f726b7370616365.link[0].component_type == "app" && length(ibm_appid_user_roles.block_776f726b7370616365) == 0
 error_message = "Bind this compute resource; user allowlist starts empty."
 }
}
run "block_776f726b7370616365_reject_mutable_image" {
 command = plan
 variables { block_776f726b7370616365_image_digest = "latest" }
 expect_failures = [var.block_776f726b7370616365_image_digest]
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
