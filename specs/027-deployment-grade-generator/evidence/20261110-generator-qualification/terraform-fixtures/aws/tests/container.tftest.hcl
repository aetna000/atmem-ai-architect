mock_provider "aws" {}
variables {
review_approved = true
region = "ap-southeast-2"
account_id = "123456789012"
block_736572766963652f6e65772d7632_name = "architect-app-1"
block_736572766963652f6e65772d7632_image = "registry.example.com/architect@sha256:0000000000000000000000000000000000000000000000000000000000000000"
block_736572766963652f6e65772d7632_log_group = "/architect/application"
block_736572766963652f6e65772d7632_repository_arn = "arn:aws:ecr:ap-southeast-2:123456789012:repository/architect"
block_736572766963652f6e65772d7632_subnets = ["subnet-reviewed"]
block_736572766963652f6e65772d7632_security_groups = ["sg-reviewed"]
}
run "block_736572766963652f6e65772d7632_security" {
 command = plan
 assert {
 condition = jsondecode(aws_ecs_task_definition.block_736572766963652f6e65772d7632.container_definitions)[0].image == var.block_736572766963652f6e65772d7632_image
 error_message = "Use the reviewed immutable image."
 }
 assert {
 condition = aws_ecs_service.block_736572766963652f6e65772d7632.network_configuration[0].assign_public_ip == false
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
 condition = aws_ecs_service.block_736572766963652f6e65772d7632.name == var.block_736572766963652f6e65772d7632_name
 error_message = "Container service name must use the reviewed input."
 }
}
run "unapproved_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
