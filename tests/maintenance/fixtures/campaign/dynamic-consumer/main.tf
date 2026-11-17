terraform {
 required_providers {
  aws = { source = "hashicorp/aws", version = "5.100.0" }
 }
}
variable "source" { type = string }
module "queue" { source = var.source }
