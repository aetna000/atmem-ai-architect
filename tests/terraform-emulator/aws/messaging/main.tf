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

resource "aws_sqs_queue" "dead_letter" {
  name                      = "tfe-messaging-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "work" {
  name                       = "tfe-messaging-work"
  visibility_timeout_seconds = 120
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dead_letter" {
  queue_url = aws_sqs_queue.dead_letter.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.work.arn]
  })
}

resource "aws_sqs_queue" "ordered" {
  name                        = "tfe-messaging-ordered.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

resource "aws_sns_topic" "alerts" {
  name = "tfe-messaging-alerts"
}

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudwatch.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alerts.arn
    }]
  })
}

resource "aws_sns_topic_subscription" "alerts_to_queue" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.work.arn
}

resource "aws_kinesis_stream" "telemetry" {
  name             = "tfe-messaging-telemetry"
  shard_count      = 1
  retention_period = 24
}
