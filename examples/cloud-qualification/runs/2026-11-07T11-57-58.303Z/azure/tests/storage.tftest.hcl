mock_provider "azurerm" {}
variables {
  review_approved = true
  region = "australiaeast"
  subscription_id = "11111111-1111-1111-1111-111111111111"
  resource_group_name = "synthetic-qualification"
  principal_object_id = "22222222-2222-2222-2222-222222222222"
  block_646f63756d656e7473_name = "atmemsyntheticstorage"
}
run "reviewed_storage_plan" { command = plan }
run "unreviewed_plan_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
