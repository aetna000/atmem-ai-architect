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


resource "aws_sfn_state_machine" "workflow" {
  name     = "tfe-scheduling-workflow"
  role_arn = aws_iam_role.execution.arn
  definition = jsonencode({
    StartAt = "Done"
    States  = { Done = { Type = "Succeed" } }
  })
}

