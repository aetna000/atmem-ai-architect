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

resource "aws_cloudwatch_log_group" "application" {
  name              = "/tfe/observability/application"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_metric_filter" "errors" {
  name           = "tfe-observability-errors"
  log_group_name = aws_cloudwatch_log_group.application.name
  pattern        = "ERROR"
  metric_transformation {
    name      = "ErrorCount"
    namespace = "TfeFixture"
    value     = "1"
  }
}

resource "aws_sns_topic" "alarms" {
  name = "tfe-observability-alarms"
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "tfe-observability-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ErrorCount"
  namespace           = "TfeFixture"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_event_rule" "nightly" {
  name                = "tfe-observability-nightly"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "nightly" {
  rule      = aws_cloudwatch_event_rule.nightly.name
  target_id = "notify"
  arn       = aws_sns_topic.alarms.arn
}

resource "aws_s3_bucket" "trail" {
  bucket        = "tfe-observability-trail"
  force_destroy = true
}

resource "aws_s3_bucket_policy" "trail" {
  bucket = aws_s3_bucket.trail.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Principal = { Service = "cloudtrail.amazonaws.com" }, Action = "s3:GetBucketAcl", Resource = aws_s3_bucket.trail.arn },
      { Effect = "Allow", Principal = { Service = "cloudtrail.amazonaws.com" }, Action = "s3:PutObject", Resource = "${aws_s3_bucket.trail.arn}/AWSLogs/*", Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } } },
    ]
  })
}

resource "aws_cloudtrail" "audit" {
  name                          = "tfe-observability-audit"
  s3_bucket_name                = aws_s3_bucket.trail.id
  include_global_service_events = true
  depends_on                    = [aws_s3_bucket_policy.trail]
}
