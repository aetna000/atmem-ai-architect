mock_provider "google" {
 override_during = plan
 mock_data "google_project" { defaults={ number="123456789012" } }
}
mock_provider "google-beta" {
 override_during = plan
 mock_resource "google_project_service_identity" { defaults={ email="service-123456789012@gcp-sa-iap.iam.gserviceaccount.com",member="serviceAccount:service-123456789012@gcp-sa-iap.iam.gserviceaccount.com" } }
}
override_resource {
 override_during = plan
 target = google_service_account.block_696e766f696365_api
 values = {"email":"invoice-api@reviewed-project.iam.gserviceaccount.com","member":"serviceAccount:invoice-api@reviewed-project.iam.gserviceaccount.com"}
}
override_resource {
 override_during = plan
 target = google_service_account.block_696e766f696365_worker
 values = {"email":"invoice-worker@reviewed-project.iam.gserviceaccount.com","member":"serviceAccount:invoice-worker@reviewed-project.iam.gserviceaccount.com"}
}
override_resource {
 override_during = plan
 target = google_service_account.block_696e766f696365_parser
 values = {"email":"invoice-parser@reviewed-project.iam.gserviceaccount.com","member":"serviceAccount:invoice-parser@reviewed-project.iam.gserviceaccount.com"}
}
override_resource {
 override_during = plan
 target = google_service_account.block_696e766f696365_ops
 values = {"email":"invoice-ops@reviewed-project.iam.gserviceaccount.com","member":"serviceAccount:invoice-ops@reviewed-project.iam.gserviceaccount.com"}
}
override_resource {
 override_during = plan
 target = google_sql_database_instance.block_696e766f696365
 values = {"connection_name":"reviewed-project:australia-southeast1:invoice-fixture"}
}

variables {
review_approved = true
applications_enabled = true
region = "australia-southeast1"
project_id = "reviewed-project"
model_id = "gemini-reviewed-version"
accounting_endpoint = "https://accounting.example.test/actions"
accounting_scope = "owned-team"
runtime_image = format("australia-southeast1-docker.pkg.dev/reviewed-project/invoice-%s/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",substr(sha256("https://atmem.ai/workspaces/11111111-1111-4111-8111-111111111111/block_696e766f696365/staging"),0,12))
parser_image = format("australia-southeast1-docker.pkg.dev/reviewed-project/invoice-%s/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",substr(sha256("https://atmem.ai/workspaces/11111111-1111-4111-8111-111111111111/block_696e766f696365/staging"),0,12))
staff_principals = ["group:invoice-staff@example.test"]
policy_review_base64 = ""
replay_review_base64 = ""
}
run "private_database_and_identity" {
 command = plan
 assert {
 condition = !google_sql_database_instance.block_696e766f696365.settings[0].ip_configuration[0].ipv4_enabled && google_sql_database_instance.block_696e766f696365.settings[0].availability_type == "REGIONAL" && google_storage_bucket.block_696e766f696365.public_access_prevention == "enforced"
 error_message = "Retain private database, regional recovery and nonpublic documents."
 }
 assert {
 condition = google_cloud_run_v2_service.block_696e766f696365_api[0].iap_enabled && !google_cloud_run_v2_service.block_696e766f696365_api[0].invoker_iam_disabled && google_cloud_run_v2_service_iam_member.block_696e766f696365_parser[0].member == "serviceAccount:${google_service_account.block_696e766f696365_worker.email}"
 error_message = "Staff authentication and worker-only parser invocation are required."
 }
}
run "private_proxy_and_worker_cpu" {
 command = plan
 assert {
 condition = google_cloud_run_v2_service.block_696e766f696365_worker[0].template[0].containers[0].resources[0].cpu_idle == false && google_cloud_run_v2_service.block_696e766f696365_worker[0].template[0].scaling[0].min_instance_count == 1 && contains(google_cloud_run_v2_service.block_696e766f696365_worker[0].template[0].containers[1].args,"--private-ip") && contains(google_cloud_run_v2_service.block_696e766f696365_worker[0].template[0].containers[1].args,"--address=127.0.0.1")
 error_message = "Keep worker CPU allocated and the maintained private-IP proxy scoped to loopback."
 }
}
run "foundation_only" {
 command = plan
 variables { applications_enabled = false }
 assert {
 condition = length(google_cloud_run_v2_service.block_696e766f696365_api) == 0 && length(google_cloud_run_v2_service.block_696e766f696365_worker) == 0 && length(google_cloud_run_v2_service.block_696e766f696365_parser) == 0
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
 variables { runtime_image = "foreign.example.test/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
 expect_failures = [terraform_data.review_gate]
}
run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
