# AI Model Share - Terraform Infrastructure

This directory contains Terraform infrastructure for the AI Model Share playground API backend.

## Features

- **Remote State**: S3 backend with DynamoDB state locking for team collaboration
- **OIDC Authentication**: Secure deployments from GitHub Actions without long-lived AWS keys
- **Multi-Environment**: Separate dev, stage, and prod environments via Terraform workspaces
- **Serverless Architecture**: Lambda + API Gateway + DynamoDB for scalable, cost-effective operations
- **Lambda Layer Support**: Optional layer for additional Python dependencies

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  Lambda Function │───▶│   DynamoDB     │
│  (HTTP API v2)  │    │   (Python 3.11) │    │   (On-Demand)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│      CORS       │    │  Lambda Layer   │
│   (Optional)    │    │   (Optional)    │
└─────────────────┘    └─────────────────┘
```

## API Endpoints

- `POST /tables` - Create a new playground table
- `GET /tables` - List all playground tables
- `GET /tables/{tableId}` - Get specific table metadata
- `PATCH /tables/{tableId}` - Update table (e.g., archive status)
- `GET /tables/{tableId}/users` - List users in a table
- `GET /tables/{tableId}/users/{username}` - Get user data
- `PUT /tables/{tableId}/users/{username}` - Update user scores

## One-Time AWS Setup

### 1. Create S3 Bucket for Terraform State

Replace `<YOUR-SUFFIX>` with a unique identifier:

```bash
# For us-east-1 (omit LocationConstraint)
aws s3api create-bucket \
  --bucket aimodelshare-tfstate-prod-<YOUR-SUFFIX>

# For other regions, use:
# aws s3api create-bucket \
#   --bucket aimodelshare-tfstate-prod-<YOUR-SUFFIX> \
#   --create-bucket-configuration LocationConstraint=<YOUR-REGION>

aws s3api put-bucket-versioning \
  --bucket aimodelshare-tfstate-prod-<YOUR-SUFFIX> \
  --versioning-configuration Status=Enabled
```

### 2. Create DynamoDB Table for State Locking

```bash
aws dynamodb create-table \
  --table-name aimodelshare-tf-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 3. Create OIDC IAM Role

Create trust policy file `gh-oidc-trust.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubOIDCTrust",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
            "repo:mparrott-at-wiris/aimodelshare:*"
          ]
        },
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

Create the role:

```bash
aws iam create-role \
  --role-name aimodelshare-github-oidc-deployer \
  --assume-role-policy-document file://gh-oidc-trust.json
```

Create and attach deployment policy (see `deploy-policy.json` in problem statement).

### 4. Update Terraform Backend Configuration

Edit the backend block in `main.tf` to use your bucket name:

```hcl
backend "s3" {
  bucket         = "aimodelshare-tfstate-prod-<YOUR-SUFFIX>"
  key            = "aimodelshare/infra/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "aimodelshare-tf-locks"
  encrypt        = true
}
```

## GitHub Configuration

### Required Repository Secrets

- `AWS_ROLE_TO_ASSUME`: IAM role ARN for OIDC deployment

### Required Repository Variables

- `AWS_REGION`: AWS region (default: us-east-1)

## Local Development

### Prerequisites

- Terraform >= 1.6.0
- AWS CLI configured
- Python 3.11+ (for Lambda development)

### Initialize and Deploy

```bash
# Initialize Terraform
cd infra
terraform init

# Create/select workspace
terraform workspace new dev  # or stage/prod

# Plan deployment
terraform plan

# Apply changes
terraform apply
```

### Optional: Build Lambda Layer

If using additional Python dependencies:

```bash
cd layer
bash build_layer.sh
```

Then set `use_layer = true` in your Terraform configuration.

## Environment Management

The infrastructure supports three environments via Terraform workspaces:

- **dev**: Development environment
- **stage**: Staging environment  
- **prod**: Production environment

Each environment gets:
- Separate AWS resources with environment-specific naming
- Isolated API endpoints
- Environment-specific tags

## Deployment

### Automatic (GitHub Actions)

Deployments are triggered automatically when:
- Code is pushed to `main` branch
- Changes are made to files in `infra/**` or workflow files

The deployment workflow runs in parallel for all three environments.

### Manual Deployment

For manual deployments, use the workflow dispatch feature in GitHub Actions or run Terraform locally.

### Destruction

Use the "Destroy Infra" workflow in GitHub Actions to tear down an environment. This is a manual workflow that requires specifying the environment to destroy.

## Monitoring and Troubleshooting

### CloudWatch Logs

Lambda function logs are automatically sent to CloudWatch Logs:
- Log group: `/aws/lambda/{function-name}`
- Retention: 14 days (default)

### API Gateway Logs

Enable API Gateway logging in the AWS console for detailed request/response logging.

### DynamoDB Metrics

Monitor DynamoDB through CloudWatch metrics:
- Read/Write capacity consumption
- Error rates
- Item count

## Security Considerations

- IAM roles follow least-privilege principles
- API supports CORS for web applications
- Input validation implemented in Lambda function
- State files encrypted in S3
- Point-in-time recovery enabled on DynamoDB

## Cost Optimization

- DynamoDB configured for on-demand billing
- Lambda has reasonable timeout (10s) and memory (256MB)
- API Gateway HTTP API (v2) for lower costs vs REST API
- No NAT gateways or other expensive resources

## Customization

### Environment Variables

Modify variables in `variables.tf`:
- `region`: AWS region
- `name_prefix`: Resource naming prefix
- `cors_allow_origins`: Allowed CORS origins
- `enable_pitr`: DynamoDB point-in-time recovery
- `safe_concurrency`: Enable safer DynamoDB operations

### Lambda Configuration

Adjust Lambda settings in `main.tf`:
- Runtime version
- Memory allocation
- Timeout duration
- Environment variables

## Troubleshooting

### Common Issues

1. **State locking errors**: Ensure DynamoDB table exists and has correct permissions
2. **OIDC role assumption failures**: Verify role trust policy and repository configuration
3. **Lambda deployment failures**: Check ZIP file size and dependencies
4. **API Gateway 502 errors**: Check Lambda function logs for errors

### Getting Help

Check CloudWatch logs and enable detailed error logging for debugging deployment issues.