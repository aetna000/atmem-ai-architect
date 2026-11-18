terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
module "queue" {
 source = "example.invalid/modules/batch/aws"
 version = ">= 1.0.0, < 2.0.0"
}
