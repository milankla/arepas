terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local backend for now — no remote state, no S3 state bucket needed until
  # Phase 3 (Lambda). Migrate to S3 backend before multi-person collaboration.
  backend "local" {}
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "arepas"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Resolve the AWS account ID at plan time so bucket names are self-documenting
# and globally unique without needing a separate tfvar.
data "aws_caller_identity" "current" {}
