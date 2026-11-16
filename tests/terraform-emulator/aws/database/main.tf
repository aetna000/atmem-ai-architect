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

resource "aws_dynamodb_table" "records" {
  name         = "tfe-database-records"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant"
  range_key    = "record"

  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "record"
    type = "S"
  }
  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "by-status"
    hash_key        = "status"
    range_key       = "record"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table_item" "seed" {
  table_name = aws_dynamodb_table.records.name
  hash_key   = aws_dynamodb_table.records.hash_key
  range_key  = aws_dynamodb_table.records.range_key
  item = jsonencode({
    tenant = { S = "fixture" }
    record = { S = "seed" }
    status = { S = "ready" }
  })
}

resource "aws_dynamodb_table" "provisioned" {
  name           = "tfe-database-provisioned"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}
