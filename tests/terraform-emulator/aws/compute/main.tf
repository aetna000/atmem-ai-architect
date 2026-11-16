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

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/tfe-compute-worker"
  retention_in_days = 14
}

resource "aws_sqs_queue" "work" {
  name                       = "tfe-compute-work"
  visibility_timeout_seconds = 180
}

resource "aws_lambda_function" "worker" {
  function_name    = "tfe-compute-worker"
  role             = aws_iam_role.execution.arn
  runtime          = "python3.13"
  handler          = "handler.handler"
  architectures    = ["arm64"]
  filename         = "${path.module}/handler.zip"
  source_code_hash = filebase64sha256("${path.module}/handler.zip")
  memory_size      = 256
  timeout          = 30
  publish          = true
  environment {
    variables = { QUEUE_URL = aws_sqs_queue.work.id }
  }
  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.worker.function_name
  function_version = aws_lambda_function.worker.version
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  qualifier     = aws_lambda_alias.live.name
  principal     = "events.amazonaws.com"
}

resource "aws_lambda_event_source_mapping" "work" {
  event_source_arn        = aws_sqs_queue.work.arn
  function_name           = aws_lambda_alias.live.arn
  batch_size              = 5
  function_response_types = ["ReportBatchItemFailures"]
}
