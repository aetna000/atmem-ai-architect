terraform {
 backend "s3" { bucket = "private-state" }
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
