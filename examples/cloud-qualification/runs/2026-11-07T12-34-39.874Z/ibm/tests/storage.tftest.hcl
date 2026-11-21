mock_provider "ibm" {}
variables {
  review_approved = true
  region = "au-syd"
  cos_instance_crn = "crn:v1:bluemix:public:cloud-object-storage:global:a/00000000000000000000000000000000:11111111-1111-1111-1111-111111111111::"
  iam_service_id = "ServiceId-22222222-2222-2222-2222-222222222222"
  block_646f63756d656e7473_name = "atmem-synthetic-storage-1"
}
run "reviewed_storage_plan" { command = plan }
run "unreviewed_plan_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
