terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}
provider "aws" { region = "us-east-1" }
locals { api_key = "sk-00000000000000000000000000000000" }
