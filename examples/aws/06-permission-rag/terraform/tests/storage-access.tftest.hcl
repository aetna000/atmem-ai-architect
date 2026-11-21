# Terraform 1.7+; mock AWS only. No real credentials or resources.
mock_provider "aws" {}
variables {
  aws_region = "ap-southeast-2"
  aws_account_id = "123456789012"
  review_approved = true
  principal_block_63616c6c65722d616c696365_arn = "arn:aws:iam::123456789012:role/qualification/operator"
  principal_block_63616c6c65722d626f62_arn = "arn:aws:iam::123456789012:role/qualification/operator"
  block_626564726f636b2d6d6f64656c_model_id = "amazon.nova-micro-v1:0"
  caller_block_7261672d6c616d626461_652d616c6963652d617069_subject = "qualification_user_1"
  caller_block_7261672d6c616d626461_652d616c6963652d617069_employee_region = "AU"
  caller_block_7261672d6c616d626461_652d626f622d617069_subject = "qualification_user_2"
  caller_block_7261672d6c616d626461_652d626f622d617069_employee_region = "AU"
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
  variables { principal_block_63616c6c65722d616c696365_arn = "arn:aws:iam::999999999999:role/other" }
  expect_failures = [terraform_data.review_gate]
}
run "wildcard_binding_rejected" {
  command = plan
  variables { principal_block_63616c6c65722d616c696365_arn = "*" }
  expect_failures = [var.principal_block_63616c6c65722d616c696365_arn]
}
