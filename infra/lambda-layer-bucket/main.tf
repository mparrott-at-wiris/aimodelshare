terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # No remote backend - ephemeral state per workflow run
  # Future enhancement: add S3/DynamoDB backend if needed
}

variable "bucket_name" {
  description = "Name of the S3 bucket for Lambda layer storage"
  type        = string
}

variable "aws_region" {
  description = "AWS region for the S3 bucket"
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "layer_storage" {
  bucket = var.bucket_name

  tags = {
    Name        = var.bucket_name
    Purpose     = "Lambda Layer ZIP storage"
    ManagedBy   = "Terraform"
    Environment = "production"
  }

  # Do not force destroy - preserve bucket on Terraform destroy
  # force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "layer_storage" {
  bucket = aws_s3_bucket.layer_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "layer_storage" {
  bucket = aws_s3_bucket.layer_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Optional: Enable versioning (commented out by default)
# resource "aws_s3_bucket_versioning" "layer_storage" {
#   bucket = aws_s3_bucket.layer_storage.id
#
#   versioning_configuration {
#     status = "Enabled"
#   }
# }

output "bucket_name" {
  description = "The name of the created S3 bucket"
  value       = aws_s3_bucket.layer_storage.bucket
}
