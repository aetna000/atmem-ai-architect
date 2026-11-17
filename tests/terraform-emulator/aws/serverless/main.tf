terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "tfe-ai-vectors"
  type = "encryption"
  policy = jsonencode({
    Rules       = [{ ResourceType = "collection", Resource = ["collection/tfe-ai-vectors"] }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_collection" "vectors" {
  name       = "tfe-ai-vectors"
  type       = "VECTORSEARCH"
  depends_on = [aws_opensearchserverless_security_policy.encryption]
}

