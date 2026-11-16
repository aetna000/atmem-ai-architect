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

resource "aws_iam_role" "execution" {
  name = "tfe-fixture-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = ["lambda.amazonaws.com", "ecs-tasks.amazonaws.com", "scheduler.amazonaws.com", "states.amazonaws.com", "bedrock.amazonaws.com", "build.apprunner.amazonaws.com"] }
      Action    = "sts:AssumeRole"
    }]
  })
}


resource "aws_bedrock_guardrail" "content" {
  name                      = "tfe-ai-content"
  blocked_input_messaging   = "Request blocked."
  blocked_outputs_messaging = "Response blocked."
  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
  }
}

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

resource "aws_bedrockagent_knowledge_base" "documents" {
  name     = "tfe-ai-documents"
  role_arn = aws_iam_role.execution.arn
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:${data.aws_partition.current.partition}:bedrock:${data.aws_region.current.region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.vectors.arn
      vector_index_name = "documents"
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }
}

resource "aws_apprunner_service" "web" {
  service_name = "tfe-ai-web"
  source_configuration {
    auto_deployments_enabled = false
    image_repository {
      image_identifier      = "public.ecr.aws/aws-containers/hello-app-runner:latest"
      image_repository_type = "ECR_PUBLIC"
      image_configuration {
        port = "8000"
      }
    }
  }
}

