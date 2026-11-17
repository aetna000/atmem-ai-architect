terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
variable "environments" { type = list(string) }
resource "aws_batch_job_queue" "unknown" {
 name = "unknown"
 priority = 1
 state = "ENABLED"
 compute_environments = var.environments
}
