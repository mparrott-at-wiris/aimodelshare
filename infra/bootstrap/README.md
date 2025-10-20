# Terraform Bootstrap

This directory contains the bootstrap Terraform configuration that creates the required AWS resources for storing Terraform state and GitHub Actions OIDC authentication:

- **S3 Bucket**: `aimodelshare-tfstate-prod-copilot-2024` - Stores Terraform state files
- **DynamoDB Table**: `aimodelshare-tf-locks` - Provides state locking to prevent concurrent modifications
- **OIDC Identity Provider**: `token.actions.githubusercontent.com` - Enables GitHub Actions OIDC authentication
- **IAM Role**: `aimodelshare-github-oidc-deployer` - Role for GitHub Actions to deploy infrastructure with comprehensive permissions

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

## Automatic GitHub Actions Configuration

After running the bootstrap, the GitHub Actions role ARN will be available in the Terraform outputs. You can set the `AWS_ROLE_TO_ASSUME` repository secret using:

```bash
# Get the role ARN from bootstrap outputs
cd infra/bootstrap
ROLE_ARN=$(terraform output -raw github_actions_role_arn)
echo "Set AWS_ROLE_TO_ASSUME secret to: $ROLE_ARN"

# Or use GitHub CLI to set it directly:
gh secret set AWS_ROLE_TO_ASSUME --body "$ROLE_ARN"
```

The role includes all necessary permissions for deploying the aimodelshare infrastructure, including:
- S3 access for Terraform state
- DynamoDB access for state locking and application tables
- Lambda function management
- IAM role and policy management (scoped to aimodelshare resources)
- API Gateway management
- CloudWatch Logs access

## Outputs

The bootstrap configuration provides the following outputs:

- `s3_bucket_name`: Name of the state bucket
- `s3_bucket_arn`: ARN of the state bucket  
- `dynamodb_table_name`: Name of the lock table
- `dynamodb_table_arn`: ARN of the lock table
- `terraform_backend_config`: Complete backend configuration object
- `github_actions_role_arn`: ARN of the GitHub Actions IAM role for OIDC authentication
- `github_oidc_provider_arn`: ARN of the GitHub OIDC identity provider

These outputs can be used by other Terraform configurations or workflows.