# Terraform 1.7+; mock AWS only. No real credentials or resources.
mock_provider "aws" {}
variables {
  aws_region = "ap-southeast-2"
  aws_account_id = "123456789012"
  review_approved = true
  block_6d6f64656c_model_id = "amazon.nova-micro-v1:0"
}
run "generated_storage_plan" {
  command = plan
}
run "unapproved_plan_rejected" {
  command = plan
  variables { review_approved = false }
  expect_failures = [terraform_data.review_gate]
}
