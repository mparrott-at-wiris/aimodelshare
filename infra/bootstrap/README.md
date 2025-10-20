# Terraform Bootstrap

This directory contains the bootstrap Terraform configuration that creates the required AWS resources for storing Terraform state:

- **S3 Bucket**: `aimodelshare-tfstate-prod-copilot-2024` - Stores Terraform state files
- **DynamoDB Table**: `aimodelshare-tf-locks` - Provides state locking to prevent concurrent modifications

## Hardcoded Configuration

As requested, this bootstrap uses a hardcoded S3 suffix: `copilot-2024`

The complete bucket name is: `aimodelshare-tfstate-prod-copilot-2024`

## Automated Deployment

The bootstrap resources are automatically created via GitHub Actions:

1. **`bootstrap-terraform.yml`** - Standalone workflow to create/update bootstrap resources
2. **`deploy-infra.yml`** - Modified to call bootstrap before deploying main infrastructure
3. **`destroy-infra.yml`** - Enhanced to optionally destroy bootstrap resources

## Manual Usage

If you need to run the bootstrap manually:

```bash
cd infra/bootstrap
terraform init
terraform plan
terraform apply
```

## Key Features

- **Idempotent**: Can be run multiple times safely
- **Import Support**: Automatically imports existing resources if they already exist
- **Security**: S3 bucket configured with encryption, versioning, and public access blocking
- **Cost-Effective**: DynamoDB table uses pay-per-request billing

## Important Notes

⚠️ **WARNING**: The bootstrap resources are shared across all environments. Destroying them will affect all Terraform workspaces and could cause data loss.

- Only destroy bootstrap resources if you're completely rebuilding the infrastructure
- The S3 bucket will be emptied before destruction to avoid conflicts
- Always backup important state files before destroying bootstrap resources

## Outputs

The bootstrap configuration provides the following outputs:

- `s3_bucket_name`: Name of the state bucket
- `s3_bucket_arn`: ARN of the state bucket  
- `dynamodb_table_name`: Name of the lock table
- `dynamodb_table_arn`: ARN of the lock table
- `terraform_backend_config`: Complete backend configuration object

These outputs can be used by other Terraform configurations or workflows.