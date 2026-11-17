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

resource "aws_secretsmanager_secret" "api_key" {
  name                    = "tfe/configuration/api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = jsonencode({ placeholder = "synthetic-value" })
}

resource "aws_ssm_parameter" "endpoint" {
  name  = "/tfe/configuration/endpoint"
  type  = "String"
  value = "https://example.invalid"
}

resource "aws_ssm_parameter" "secure" {
  name  = "/tfe/configuration/secure"
  type  = "SecureString"
  value = "synthetic-value"
}

resource "aws_ssm_document" "runbook" {
  name            = "tfe-configuration-runbook"
  document_type   = "Command"
  document_format = "JSON"
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Fixture command"
    mainSteps = [{
      action = "aws:runShellScript"
      name   = "echo"
      inputs = { runCommand = ["echo emulator"] }
    }]
  })
}
