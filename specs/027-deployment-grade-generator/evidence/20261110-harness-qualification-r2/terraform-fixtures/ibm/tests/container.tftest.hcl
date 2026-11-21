mock_provider "ibm" {}
variables {
review_approved = true
region = "au-syd"
block_736572766963652f6e65772d7632_name = "architect-app-1"
block_736572766963652f6e65772d7632_image = "registry.example.com/architect@sha256:0000000000000000000000000000000000000000000000000000000000000000"
code_engine_project_id = "11111111-1111-1111-1111-111111111111"
}
run "block_736572766963652f6e65772d7632_security" {
 command = plan
 assert {
 condition = ibm_code_engine_app.block_736572766963652f6e65772d7632.image_reference == var.block_736572766963652f6e65772d7632_image
 error_message = "Use the reviewed immutable image."
 }
 assert {
 condition = ibm_code_engine_app.block_736572766963652f6e65772d7632.managed_domain_mappings == "local"
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
 condition = ibm_code_engine_app.block_736572766963652f6e65772d7632.name == var.block_736572766963652f6e65772d7632_name
 error_message = "Container service name must use the reviewed input."
 }
}
run "unapproved_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
