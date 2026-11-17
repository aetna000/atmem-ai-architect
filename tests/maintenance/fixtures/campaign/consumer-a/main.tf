terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
provider "aws" { region = "us-east-1" }
module "queue" {
 source = "git::https://example.invalid/shared-batch.git?ref=v1.0.0"
 primary = "arn:aws:batch:us-east-1:123456789012:compute-environment/primary"
 backup = "arn:aws:batch:us-east-1:123456789012:compute-environment/backup"
}
output "queue" { value = module.queue.queue_arn }
