terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
resource "aws_batch_job_queue" "invalid" {
 name = "invalid"
 state = "ENABLED"
 compute_environments = ["arn:aws:batch:us-east-1:123456789012:compute-environment/a"]
}
