output "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.arn
}

output "terraform_backend_config" {
  description = "Backend configuration for use in main Terraform configuration"
  value = {
    bucket         = aws_s3_bucket.terraform_state.bucket
    key           = "aimodelshare/infra/terraform.tfstate"
    region        = var.region
    dynamodb_table = aws_dynamodb_table.terraform_locks.name
    encrypt       = true
  }
}