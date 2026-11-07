# Terraform 1.7+; mock AWS only. No real credentials or resources.
mock_provider "aws" {}
variables {
  aws_region = "ap-southeast-2"
  aws_account_id = "123456789012"
  review_approved = true
  principal_block_6f70657261746f72_arn = "arn:aws:iam::123456789012:role/qualification/operator"
}
run "generated_storage_plan" {
  command = plan
}
run "unapproved_plan_rejected" {
  command = plan
  variables { review_approved = false }
  expect_failures = [terraform_data.review_gate]
}
run "cross_account_binding_rejected" {
  command = plan
  variables { principal_block_6f70657261746f72_arn = "arn:aws:iam::999999999999:role/other" }
  expect_failures = [terraform_data.review_gate]
}
run "wildcard_binding_rejected" {
  command = plan
  variables { principal_block_6f70657261746f72_arn = "*" }
  expect_failures = [var.principal_block_6f70657261746f72_arn]
}
