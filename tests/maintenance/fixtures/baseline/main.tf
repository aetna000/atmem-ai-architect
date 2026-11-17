terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
# Queue order is an accepted deployment decision.
variable "environment_arn" { type = string }
resource "aws_batch_job_queue" "jobs" {
  name = "research-jobs"
  state = "ENABLED"
  priority = 10
  compute_environments = [var.environment_arn, "arn:aws:batch:us-east-1:123456789012:compute-environment/backup"]
}
output "queue_arn" { value = aws_batch_job_queue.jobs.arn }
