terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name_prefix = "ncdhhs-pdf-qa"
  common_tags = {
    Project     = "NCDHHS PDF Q&A"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
