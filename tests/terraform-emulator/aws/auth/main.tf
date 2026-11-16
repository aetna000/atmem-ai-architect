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


resource "aws_cognito_user_pool" "users" {
  name                     = "tfe-auth-users"
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]
  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
}

resource "aws_cognito_resource_server" "api" {
  identifier   = "https://api.fixture.invalid"
  name         = "tfe-auth-api"
  user_pool_id = aws_cognito_user_pool.users.id
  scope {
    scope_name        = "read"
    scope_description = "Read access"
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name                                 = "tfe-auth-web"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "${aws_cognito_resource_server.api.identifier}/read"]
  callback_urls                        = ["https://app.fixture.invalid/callback"]
  supported_identity_providers         = ["COGNITO"]
}

resource "aws_cognito_user_pool_domain" "hosted" {
  domain       = "tfe-auth-fixture"
  user_pool_id = aws_cognito_user_pool.users.id
}

