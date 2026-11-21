mock_provider "google" {}
variables {
  review_approved = true
  region = "australia-southeast1"
  project_id = "synthetic-qualification"
  principal_member = "serviceAccount:operator@synthetic-qualification.iam.gserviceaccount.com"
  block_6275636b6574_name = "atmem-synthetic-storage"
}
run "reviewed_storage_plan" { command = plan }
run "unreviewed_plan_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
