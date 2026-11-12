mock_provider "google" {}
variables {
review_approved = true
region = "australia-southeast1"
project_id = "reviewed-project"
block_736572766963652f6e65772d7632_name = "architect-app-1"
block_736572766963652f6e65772d7632_image = "registry.example.com/architect@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}
run "block_736572766963652f6e65772d7632_security" {
 command = plan
 assert {
 condition = google_cloud_run_v2_service.block_736572766963652f6e65772d7632.template[0].containers[0].image == var.block_736572766963652f6e65772d7632_image
 error_message = "Use the reviewed immutable image."
 }
 assert {
 condition = google_cloud_run_v2_service.block_736572766963652f6e65772d7632.ingress == "INGRESS_TRAFFIC_INTERNAL_ONLY"
 error_message = "Unrequested public exposure is forbidden."
 }
}
run "block_736572766963652f6e65772d7632_reject_mutable_image" {
 command = plan
 variables { block_736572766963652f6e65772d7632_image = "registry.example.com/app:latest" }
 expect_failures = [var.block_736572766963652f6e65772d7632_image]
}
run "block_736572766963652f6e65772d7632_footprint" {
 command = plan
 assert {
 condition = google_cloud_run_v2_service.block_736572766963652f6e65772d7632.name == var.block_736572766963652f6e65772d7632_name
 error_message = "Container service name must use the reviewed input."
 }
}
run "unapproved_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
