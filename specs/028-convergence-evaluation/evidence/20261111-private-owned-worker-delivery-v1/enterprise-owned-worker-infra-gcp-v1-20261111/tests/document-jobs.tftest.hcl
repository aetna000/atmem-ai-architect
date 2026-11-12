mock_provider "google" {}
mock_provider "google-beta" {}
override_resource {
 override_during = plan
 target = google_service_account.block_6b6e6f776c65646765_vm
 values = {
 email = "document-vm@reviewed-project.iam.gserviceaccount.com"
 name = "projects/reviewed-project/serviceAccounts/document-vm@reviewed-project.iam.gserviceaccount.com"
 }
}
override_resource {
 override_during = plan
 target = google_project_service_identity.block_6b6e6f776c65646765_batch_agent
 values = {
 email = "service-123456789012@gcp-sa-cloudbatch.iam.gserviceaccount.com"
 member = "serviceAccount:service-123456789012@gcp-sa-cloudbatch.iam.gserviceaccount.com"
 }
}
variables {
 review_approved = true
 images_ready = true
 project_id = "reviewed-project"
 worker_service_account = "owned-worker@reviewed-project.iam.gserviceaccount.com"
 parser_image = format("%s-docker.pkg.dev/reviewed-project/%s/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","australia-southeast1",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
 transfer_image = format("%s-docker.pkg.dev/reviewed-project/%s/transfer@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","australia-southeast1",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12)))
 parser_revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
run "private_document_substrate" {
 command = plan
 assert {
 condition = google_storage_bucket.block_6b6e6f776c65646765.uniform_bucket_level_access && google_storage_bucket.block_6b6e6f776c65646765.public_access_prevention == "enforced" && !google_storage_bucket.block_6b6e6f776c65646765.versioning[0].enabled && google_storage_bucket.block_6b6e6f776c65646765.soft_delete_policy[0].retention_duration_seconds == 0 && !google_storage_bucket.block_6b6e6f776c65646765.force_destroy
 error_message = "No public access, mutable history or hidden soft-delete retention for temporary document bytes."
 }
 assert {
 condition = output.document_executor_configuration.provider == "gcp" && output.document_executor_configuration.parserRevision == var.parser_revision && output.document_executor_configuration.configuration == output.document_job_configuration && output.document_job_configuration.format == "enterprise-google-document-job-v1" && output.document_job_configuration.region == "australia-southeast1" && output.document_job_configuration.workerServiceAccount == var.worker_service_account && output.document_job_configuration.vmServiceAccount == google_service_account.block_6b6e6f776c65646765_vm.email
 error_message = "Keep exact runtime configuration, selected region and separate identities."
 }
}
run "scoped_job_identity" {
 command = plan
 assert {
 condition = toset(google_project_iam_custom_role.block_6b6e6f776c65646765_control.permissions) == toset(["batch.jobs.create","batch.jobs.get","batch.jobs.delete","batch.operations.get"]) && google_service_account_iam_member.block_6b6e6f776c65646765_worker_act_as.service_account_id == google_service_account.block_6b6e6f776c65646765_vm.name && google_service_account_iam_member.block_6b6e6f776c65646765_worker_act_as.role == "roles/iam.serviceAccountUser"
 error_message = "Do not grant generic administrator or project-wide actAs authority."
 }
 assert {
 condition = toset(google_project_iam_custom_role.block_6b6e6f776c65646765_transfer_objects.permissions) == toset(["storage.objects.get","storage.objects.create"]) && toset(google_project_iam_custom_role.block_6b6e6f776c65646765_worker_objects.permissions) == toset(["storage.objects.get","storage.objects.create","storage.objects.delete"]) && google_storage_bucket_iam_member.block_6b6e6f776c65646765_transfer.bucket == google_storage_bucket.block_6b6e6f776c65646765.name
 error_message = "Transfer identities receive temporary-byte access only; deletion stays with the controller."
 }
}
run "private_network" {
 command = plan
 assert {
 condition = google_compute_subnetwork.block_6b6e6f776c65646765.private_ip_google_access && !google_compute_network.block_6b6e6f776c65646765.auto_create_subnetworks && google_compute_network.block_6b6e6f776c65646765.delete_default_routes_on_create && google_compute_route.block_6b6e6f776c65646765_api.dest_range == "199.36.153.8/30" && google_compute_route.block_6b6e6f776c65646765_direct.dest_range == "34.126.0.0/18"
 error_message = "Retain explicit private Google routing without a default internet route."
 }
 assert {
 condition = google_compute_firewall.block_6b6e6f776c65646765_allow_api.priority < google_compute_firewall.block_6b6e6f776c65646765_deny_egress.priority && google_compute_firewall.block_6b6e6f776c65646765_deny_egress.direction == "EGRESS" && google_dns_record_set.block_6b6e6f776c65646765_private_vip.type == "A" && toset(google_dns_record_set.block_6b6e6f776c65646765_registry_wildcard.rrdatas) == toset(["private.googleapis.com."])
 error_message = "Private API/registry DNS and restrictive firewall ordering must remain connected."
 }
}
run "foundation_configuration_not_ready" {
 command = plan
 variables {
 images_ready = false
 parser_image = ""
 transfer_image = ""
 parser_revision = ""
 }
 assert {
 condition = output.document_job_configuration == null
 error_message = "Do not advertise a configured parser before real artifacts are published."
 }
}
run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "foreign_worker_rejected" {
 command = plan
 variables { worker_service_account = "owned-worker@foreign-project.iam.gserviceaccount.com" }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "same_worker_and_vm_rejected" {
 command = plan
 variables { worker_service_account = format("%s-vm@reviewed-project.iam.gserviceaccount.com",format("doc-%s",substr(sha256("https://atmem.ai/workspaces/private-knowledge-qualification/block_6b6e6f776c65646765/qualification"),0,12))) }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "mutable_image_rejected" {
 command = plan
 variables { parser_image = "unreviewed:latest" }
 expect_failures = [var.parser_image]
}
run "foreign_registry_rejected" {
 command = plan
 variables { transfer_image = "foreign.example/transfer@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
 expect_failures = [terraform_data.block_6b6e6f776c65646765_review]
}
run "missing_parser_receipt_rejected" {
 command = plan
 variables { parser_revision = "" }
 expect_failures = [var.parser_revision]
}
run "selected_region_cannot_drift" {
 command = plan
 variables { region = "us-central1" }
 expect_failures = [var.region]
}
