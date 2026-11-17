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

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block = "10.43.0.0/16"
}

resource "aws_subnet" "a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.43.0.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
}

resource "aws_subnet" "b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.43.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
}

resource "aws_security_group" "service" {
  name        = "tfe-fixture-service"
  description = "Fixture service group"
  vpc_id      = aws_vpc.main.id
}


resource "aws_db_subnet_group" "main" {
  name       = "tfe-data-main"
  subnet_ids = [aws_subnet.a.id, aws_subnet.b.id]
}

resource "aws_db_parameter_group" "postgres" {
  name   = "tfe-data-postgres"
  family = "postgres16"
  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
}

resource "aws_db_instance" "main" {
  identifier                  = "tfe-data-main"
  engine                      = "postgres"
  engine_version              = "16.3"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  db_name                     = "fixture"
  username                    = "fixture_admin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  parameter_group_name        = aws_db_parameter_group.postgres.name
  vpc_security_group_ids      = [aws_security_group.service.id]
  storage_encrypted           = true
  skip_final_snapshot         = true
}
