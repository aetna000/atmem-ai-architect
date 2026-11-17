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


data "aws_ami" "linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_launch_template" "app" {
  name          = "tfe-servers-app"
  image_id      = data.aws_ami.linux.id
  instance_type = "t3.micro"
  metadata_options {
    http_tokens = "required"
  }
  vpc_security_group_ids = [aws_security_group.service.id]
}

resource "aws_autoscaling_group" "app" {
  name                = "tfe-servers-app"
  min_size            = 1
  max_size            = 2
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.a.id, aws_subnet.b.id]
  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

