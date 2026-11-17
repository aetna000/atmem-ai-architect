terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
provider "aws" { region = "us-west-2" }
module "queue" {
 source = "../../modules/queue"
 primary = "arn:aws:batch:us-west-2:123456789012:compute-environment/primary"
 backup = "arn:aws:batch:us-west-2:123456789012:compute-environment/backup"
}
