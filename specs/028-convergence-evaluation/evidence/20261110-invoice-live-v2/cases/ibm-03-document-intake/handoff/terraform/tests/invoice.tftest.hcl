mock_provider "ibm" {
 override_during = plan
 mock_data "ibm_resource_group" { defaults = { id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",account_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" } }
 mock_resource "ibm_code_engine_project" { defaults = { project_id="11111111-1111-4111-8111-111111111111",crn="crn:v1:bluemix:public:codeengine:au-syd:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:11111111-1111-4111-8111-111111111111::" } }
 mock_resource "ibm_resource_instance" { defaults = { guid="55555555-5555-4555-8555-555555555555",id="crn:v1:bluemix:public:cloud-object-storage:global:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:55555555-5555-4555-8555-555555555555::" } }
 mock_resource "ibm_iam_trusted_profile" { defaults = { profile_id="Profile-66666666-6666-4666-8666-666666666666",iam_id="iam-Profile-66666666-6666-4666-8666-666666666666" } }
 mock_resource "ibm_appid_application" { defaults = { client_id="77777777-7777-4777-8777-777777777777",oauth_server_url="https://au-syd.appid.cloud.ibm.com/oauth/v4/55555555-5555-4555-8555-555555555555" } }
}
override_resource {
 override_during = plan
 target = ibm_cos_bucket.block_696e766f6963652d776f726b666c6f77
 values = { crn = "crn:v1:bluemix:public:cloud-object-storage:global:a/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:55555555-5555-4555-8555-555555555555:bucket:fixture-invoices" }
}
override_resource {
 override_during = plan
 target = ibm_iam_trusted_profile.block_696e766f6963652d776f726b666c6f77_api
 values = {"profile_id":"Profile-66666666-6666-4666-8666-666666666666","iam_id":"iam-Profile-66666666-6666-4666-8666-666666666666"}
}
override_resource {
 override_during = plan
 target = ibm_iam_trusted_profile.block_696e766f6963652d776f726b666c6f77_worker
 values = {"profile_id":"Profile-88888888-8888-4888-8888-888888888888","iam_id":"iam-Profile-88888888-8888-4888-8888-888888888888"}
}
override_resource {
 override_during = plan
 target = ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_api[0]
 values = { endpoint = format("https://invoice-%s-api.project-fixture.au-syd.codeengine.appdomain.cloud",substr(sha256("https://atmem.ai/workspaces/evaluation-ibm-03-document-intake/block_696e766f6963652d776f726b666c6f77/staging"),0,12)) }
}
override_resource {
 override_during = plan
 target = ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_parser[0]
 values = { endpoint = format("https://invoice-%s-parser.project-fixture.private.au-syd.codeengine.appdomain.cloud",substr(sha256("https://atmem.ai/workspaces/evaluation-ibm-03-document-intake/block_696e766f6963652d776f726b666c6f77/staging"),0,12)) }
}

variables {
review_approved = true
applications_enabled = true
region = "au-syd"
account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
resource_group_name = "reviewed-applications"
model_id = "ibm/reviewed-model"
watsonx_project_id = "22222222-2222-2222-2222-222222222222"
runtime_instance_id = "33333333-3333-3333-3333-333333333333"
accounting_endpoint = "https://accounting.example.test/actions"
accounting_scope = "owned-team"
registry_pull_secret = "registry-pull"
runtime_image = format("au.icr.io/invoice-%s/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",substr(sha256("https://atmem.ai/workspaces/evaluation-ibm-03-document-intake/block_696e766f6963652d776f726b666c6f77/staging"),0,12))
parser_image = format("au.icr.io/invoice-%s/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",substr(sha256("https://atmem.ai/workspaces/evaluation-ibm-03-document-intake/block_696e766f6963652d776f726b666c6f77/staging"),0,12))
staff_subjects = ["44444444-4444-4444-4444-444444444444"]
policy_review_base64 = ""
replay_review_base64 = ""
operations_enabled = true
maintenance_enabled = true
operator_logs_instance_id = "88888888-8888-4888-8888-888888888888"
operator_notification_integration_id = "12345"
}
run "operator_before_applications" {
 command = plan
 variables {
 applications_enabled = false
 maintenance_enabled = false
 }
 assert {
 condition = length(ibm_code_engine_job.block_696e766f6963652d776f726b666c6f77_operator_initialize) == 1 && length(ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_api) == 0 && ibm_code_engine_job.block_696e766f6963652d776f726b666c6f77_operator_monitor[0].run_service_account == "none" && !ibm_code_engine_job.block_696e766f6963652d776f726b666c6f77_operator_monitor[0].run_compute_resource_token_enabled && ibm_code_engine_job.block_696e766f6963652d776f726b666c6f77_operator_monitor[0].scale_retry_limit == 0
 error_message = "Bootstrap is separate, bounded and without application/cloud authority."
 }
}
run "operator_mutable_image_rejected" {
 command = plan
 variables {
 applications_enabled = false
 runtime_image = "unreviewed:latest"
 maintenance_enabled = false
 }
 expect_failures = [var.runtime_image]
}
run "operating_jobs_required" {
 command = plan
 variables {
 operations_enabled = false
 maintenance_enabled = false
 }
 expect_failures = [terraform_data.review_gate]
}
run "maintenance_without_jobs_rejected" {
 command = plan
 variables {
 applications_enabled = false
 operations_enabled = false
 }
 expect_failures = [terraform_data.review_gate]
}
run "notification_id_overflow_rejected" {
 command = plan
 variables { operator_notification_integration_id = "4294967296" }
 expect_failures = [var.operator_notification_integration_id]
}

run "private_database_and_parser" {
 command = plan
 assert {
 condition = ibm_database.block_696e766f6963652d776f726b666c6f77.service_endpoints == "private" && ibm_database.block_696e766f6963652d776f726b666c6f77.version == "18" && ibm_database.block_696e766f6963652d776f726b666c6f77.deletion_protection
 error_message = "Retain private native PostgreSQL and recovery protection."
 }
 assert {
 condition = ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_parser[0].managed_domain_mappings == "local_private" && !ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_parser[0].run_compute_resource_token_enabled && ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_parser[0].run_service_account == "none"
 error_message = "Untrusted PDF parser has private TLS and no cloud compute/API identity."
 }
 assert {
 condition = startswith(ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_api[0].image_reference,"au.icr.io/") && ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_worker[0].scale_min_instances == 1
 error_message = "Use the actual Sydney registry hostname and retain the background worker."
 }
}
run "foundation_only" {
 command = plan
 variables {
 applications_enabled = false
 operations_enabled = false
 maintenance_enabled = false
 }
 assert {
 condition = length(ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_api) == 0 && length(ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_worker) == 0 && length(ibm_code_engine_app.block_696e766f6963652d776f726b666c6f77_parser) == 0 && length(ibm_code_engine_job.block_696e766f6963652d776f726b666c6f77_operator_initialize) == 0
 error_message = "Bootstrap and publication precede application release."
 }
}
run "mutable_image_rejected" {
 command = plan
 variables { runtime_image = "unreviewed:latest" }
 expect_failures = [var.runtime_image]
}
run "foreign_registry_rejected" {
 command = plan
 variables { runtime_image = "foreign.test/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
 expect_failures = [terraform_data.review_gate]
}
run "empty_staff_rejected" {
 command = plan
 variables { staff_subjects = [] }
 expect_failures = [terraform_data.review_gate]
}
run "wrong_account_rejected" {
 command = plan
 variables { account_id = "cccccccccccccccccccccccccccccccc" }
 expect_failures = [terraform_data.review_gate]
}
run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
