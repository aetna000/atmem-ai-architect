mock_provider "google" {}
variables {
  review_approved = true
  region = "australia-southeast1"
  project_id = "synthetic-qualification"
  principal_member = "serviceAccount:operator@synthetic-qualification.iam.gserviceaccount.com"
  block_646f63756d656e7473_name = "atmem-synthetic-storage-1"
}
run "reviewed_storage_plan" { command = plan }
run "unreviewed_plan_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
