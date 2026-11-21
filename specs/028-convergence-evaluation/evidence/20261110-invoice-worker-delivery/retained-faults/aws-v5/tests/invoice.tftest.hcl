mock_provider "aws" {
 mock_data "aws_caller_identity" { defaults = { account_id = "123456789012" } }
 mock_data "aws_availability_zones" { defaults = { names = ["ap-southeast-2a","ap-southeast-2b"] } }
 mock_data "aws_route53_zone" { defaults = { name = "example.test.",private_zone = false } }
}

variables {
review_approved = true
applications_enabled = true
region = "ap-southeast-2"
account_id = "123456789012"
public_zone_id = "Z0123456789EXAMPLE"
model_id = "anthropic.reviewed-model-v1:0"
accounting_endpoint = "https://accounting.example.test/actions"
accounting_scope = "owned-account"
runtime_image = "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/invoice-ad29e6b383b8-runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
parser_image = "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/invoice-ad29e6b383b8-parser@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
replay_review_base64 = ""
}
run "private_database_and_parser" {
 command = plan
 assert {
 condition = aws_db_instance.block_696e766f696365.publicly_accessible == false && aws_db_instance.block_696e766f696365.iam_database_authentication_enabled && aws_db_instance.block_696e766f696365.storage_encrypted && aws_lb.block_696e766f696365_parser.internal
 error_message = "Database and parser must retain their private, encrypted and IAM boundaries."
 }
 assert {
 condition = aws_ecs_task_definition.block_696e766f696365_parser[0].task_role_arn == null
 error_message = "Parser must not inherit application data/model authority."
 }
}
run "foundation_only" {
 command = plan
 variables { applications_enabled = false }
 assert {
 condition = length(aws_ecs_service.block_696e766f696365_api) == 0 && length(aws_ecs_service.block_696e766f696365_worker) == 0 && length(aws_ecs_service.block_696e766f696365_parser) == 0
 error_message = "Bootstrap and publication must precede application release."
 }
}
run "foreign_image_rejected" {
 command = plan
 variables { runtime_image = "123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/foreign@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
 expect_failures = [terraform_data.review_gate]
}
run "mutable_image_rejected" {
 command = plan
 variables { runtime_image = "unreviewed:latest" }
 expect_failures = [var.runtime_image]
}
run "foreign_account_rejected" {
 command = plan
 variables { account_id = "999999999999", applications_enabled = false }
 expect_failures = [terraform_data.review_gate]
}

run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
