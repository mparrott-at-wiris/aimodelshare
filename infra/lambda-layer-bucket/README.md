# Lambda Layer S3 Bucket - Terraform Configuration

## Overview

This Terraform configuration manages an S3 bucket for storing large AWS Lambda Layer ZIP files that exceed the direct upload size limit (50 MB). The bucket is used by the GitHub Actions workflow `.github/workflows/publish-lambda-layers.yml` when publishing layers.

## Purpose

When Lambda layer ZIP files are large (approaching or exceeding 50 MB), they cannot be uploaded directly via the AWS Lambda API's `--zip-file` parameter. Instead, they must be uploaded to S3 first, then referenced using the `--content` parameter with `S3Bucket` and `S3Key` values.

This Terraform module creates and manages:
- An S3 bucket with server-side encryption (AES256)
- Public access block settings (all public access blocked)
- Optional versioning (commented out by default)

## State Management

**Important**: This configuration uses **ephemeral local state** - no remote backend is configured. Each workflow run initializes Terraform fresh and manages state locally for that run only.

### Workflow Integration

The GitHub Actions workflow handles bucket lifecycle as follows:

1. **Bucket Detection**: Before applying Terraform, the workflow checks if the bucket already exists using `aws s3api head-bucket`
2. **Import if Exists**: If the bucket exists, it runs `terraform import aws_s3_bucket.layer_storage <bucket_name>` to import it into local state
3. **Apply**: Runs `terraform apply` to ensure the bucket and its configuration are up-to-date

This approach allows the workflow to:
- Create the bucket on first run
- Manage existing buckets without errors
- Update bucket configuration on subsequent runs
- Work without persistent state storage

## Usage

### Variables

- `bucket_name` (required): Name of the S3 bucket to create/manage
- `aws_region` (default: `us-east-1`): AWS region for the bucket

### Manual Usage

If you want to use this configuration manually (outside the workflow):

```bash
cd infra/lambda-layer-bucket

# Initialize Terraform
terraform init

# Check if bucket exists and import if needed
aws s3api head-bucket --bucket <your-bucket-name> 2>/dev/null && \
  terraform import aws_s3_bucket.layer_storage <your-bucket-name> || true

# Plan changes
terraform plan -var="bucket_name=<your-bucket-name>" -var="aws_region=us-east-1"

# Apply changes
terraform apply -var="bucket_name=<your-bucket-name>" -var="aws_region=us-east-1"
```

### Workflow Usage

The workflow automatically handles this when `auto_create_bucket=true` and `use_s3_upload=true`:

```yaml
use_s3_upload: true
s3_bucket: my-lambda-layers-bucket
auto_create_bucket: true
```

## Resources Created

1. **`aws_s3_bucket.layer_storage`**: The main S3 bucket
2. **`aws_s3_bucket_public_access_block.layer_storage`**: Blocks all public access
3. **`aws_s3_bucket_server_side_encryption_configuration.layer_storage`**: Enables AES256 encryption

## Security

- All public access is blocked by default
- Server-side encryption (AES256) is enabled
- Bucket does not have `force_destroy` enabled (preserves data on Terraform destroy)

## Future Enhancements

- Add S3 backend for persistent state management
- Enable versioning for layer ZIP files
- Add lifecycle policies for old objects
- Support multi-region buckets
- Add bucket replication for disaster recovery

## Outputs

- `bucket_name`: The name of the created/managed S3 bucket (passed to subsequent workflow jobs)
