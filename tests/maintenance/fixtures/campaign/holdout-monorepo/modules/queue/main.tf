terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
variable "primary" { type = string }
variable "backup" { type = string }
resource "aws_batch_job_queue" "shared" {
 name = "holdout-batch"
 state = "ENABLED"
 priority = 3
 compute_environments = [var.primary, var.backup]
}
output "queue_arn" { value = aws_batch_job_queue.shared.arn }
