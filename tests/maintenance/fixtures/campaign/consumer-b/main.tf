terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
provider "aws" { region = "eu-west-1" }
module "archive" {
 source = "git::https://example.invalid/shared-batch.git?ref=v1.0.0"
 primary = "arn:aws:batch:eu-west-1:123456789012:compute-environment/primary"
 backup = "arn:aws:batch:eu-west-1:123456789012:compute-environment/backup"
}
