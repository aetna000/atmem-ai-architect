terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

resource "aws_iam_role" "execution" {
  name = "tfe-fixture-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["lambda.amazonaws.com", "ecs-tasks.amazonaws.com", "scheduler.amazonaws.com", "states.amazonaws.com", "bedrock.amazonaws.com", "build.apprunner.amazonaws.com"] }
      Action    = "sts:AssumeRole"
    }]
  })
}


resource "aws_sqs_queue" "jobs" {
  name = "tfe-scheduling-jobs"
}

resource "aws_scheduler_schedule_group" "jobs" {
  name = "tfe-scheduling"
}

resource "aws_scheduler_schedule" "nightly" {
  name                = "tfe-scheduling-nightly"
  group_name          = aws_scheduler_schedule_group.jobs.name
  schedule_expression = "cron(0 2 * * ? *)"
  flexible_time_window {
    mode = "OFF"
  }
  target {
    arn      = aws_sqs_queue.jobs.arn
    role_arn = aws_iam_role.execution.arn
    input    = jsonencode({ job = "nightly" })
  }
}
