terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
resource "aws_s3_bucket" "probe" {
 bucket = "forbidden-execution"
 provisioner "local-exec" { command = "id" }
}
