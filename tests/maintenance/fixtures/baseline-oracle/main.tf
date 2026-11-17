terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.0.0" }
  }
}
provider "aws" { region = "us-east-1" }
# Queue order is an accepted deployment decision.
variable "environment_arn" { type = string }
resource "aws_batch_job_queue" "jobs" {
  name = "research-jobs"
  state = "ENABLED"
  priority = 10
  compute_environment_order {
    compute_environment = var.environment_arn
    order = 0
  }
  compute_environment_order {
    compute_environment = "arn:aws:batch:us-east-1:123456789012:compute-environment/backup"
    order = 1
  }
}
output "queue_arn" { value = aws_batch_job_queue.jobs.arn }
