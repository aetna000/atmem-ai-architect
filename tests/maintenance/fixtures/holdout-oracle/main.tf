terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.0.0" }
  }
}
provider "aws" { region = "us-east-1" }
provider "aws" {
  alias = "west"
  region = "us-west-2"
}
locals {
  primary = "arn:aws:batch:us-west-2:123456789012:compute-environment/primary"
}
resource "aws_s3_bucket" "logs" { bucket = "maintenance-holdout-logs" }
resource "aws_batch_job_queue" "nightly" {
  provider = aws.west
  name = "nightly"
  priority = 2
  state = "DISABLED"
  compute_environment_order {
    compute_environment = local.primary
    order = 0
  }
}
