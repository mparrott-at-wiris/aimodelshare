# Cleanup Test Resources

This document describes how to use the cleanup tools for managing test playgrounds and IAM resources.

## Overview

During testing, the aimodelshare package creates various AWS resources:
- **API Gateway REST APIs** (playgrounds) - created when tests deploy model playgrounds
- **IAM users and policies** - created during the `set_credentials` process with names starting with `temporaryaccessAImodelshare`

The cleanup tools help identify and delete these resources to avoid resource accumulation and unnecessary AWS costs.

## Tools

### 1. Cleanup Script (`scripts/cleanup_test_resources.py`)

A Python script that provides an interactive interface for listing and deleting resources.

#### Features
- Lists all API Gateway REST APIs (playgrounds) in a region
- Lists IAM users created by the test framework
- Shows associated resources (policies, access keys) for each IAM user
- Interactive selection of resources to delete
- Dry-run mode for safe preview
- Proper cleanup of all associated resources before deletion

#### Usage

**Dry-run mode (safe preview):**
```bash
python scripts/cleanup_test_resources.py --dry-run
```

**Interactive cleanup in us-east-1 (default):**
```bash
python scripts/cleanup_test_resources.py
```

**Interactive cleanup in a specific region:**
```bash
python scripts/cleanup_test_resources.py --region us-west-2
```

#### Prerequisites
- AWS credentials configured (via environment variables, AWS CLI, or IAM role)
- Python 3.6+
- boto3 library installed

#### Interactive Mode

When running in interactive mode, the script will:

1. List all playgrounds with details:
   - API ID
   - Name
   - Creation date
   - Description

2. List all IAM users (filtered by prefix) with details:
   - Username
   - Creation date
   - User ID
   - Number of attached policies
   - Number of access keys

3. Prompt for selection:
   - Enter comma-separated numbers (e.g., `1,3,5`)
   - Enter ranges (e.g., `1-5`)
   - Enter `all` to select all resources
   - Enter `none` or press Enter to skip

4. Show summary and request confirmation

5. Delete selected resources in the correct order:
   - For IAM users: delete access keys → detach/delete policies → delete user
   - For playgrounds: delete the API Gateway REST API

#### Example Session

```
============================================================
AWS Resource Cleanup - Test Playgrounds & IAM Users
============================================================

Fetching playgrounds...

Found 3 playground(s):

1. ID: abc123def
   Name: test-playground-classification
   Created: 2024-10-25 14:32:10
   Description: Test playground for CI

2. ID: xyz789ghi
   Name: test-playground-regression
   Created: 2024-10-26 09:15:22
   Description: N/A

3. ID: mno456pqr
   Name: production-model-api
   Created: 2024-10-01 08:00:00
   Description: Production API

Fetching IAM users (filtered by 'temporaryaccessAImodelshare' prefix)...

Found 2 IAM user(s):

1. Username: temporaryaccessAImodelshare1a2b3c4d
   Created: 2024-10-25 14:30:00
   User ID: AIDAI1234567890ABCDEF
   Policies: 1
   Access Keys: 1

2. Username: temporaryaccessAImodelshare5e6f7g8h
   Created: 2024-10-26 09:12:00
   User ID: AIDAI9876543210GHIJKL
   Policies: 1
   Access Keys: 1

============================================================
Select resources to delete:

Playgrounds to delete (enter comma-separated numbers, or 'all' for all, or 'none'):
  [1-3]: 1,2

IAM users to delete (enter comma-separated numbers, or 'all' for all, or 'none'):
  [1-2]: all

============================================================
SUMMARY:

Playgrounds to delete: 2
  - test-playground-classification (abc123def)
  - test-playground-regression (xyz789ghi)

IAM users to delete: 2
  - temporaryaccessAImodelshare1a2b3c4d
  - temporaryaccessAImodelshare5e6f7g8h

============================================================
WARNING: This action cannot be undone!

Type 'DELETE' to confirm: DELETE

============================================================
Deleting resources...

✓ Deleted playground: abc123def
✓ Deleted playground: xyz789ghi
  ✓ Deleted access key: AKIAI1234567890ABCDEF
  ✓ Detached policy: temporaryaccessAImodelsharePolicy1a2b3c4d
  ✓ Deleted custom policy: temporaryaccessAImodelsharePolicy1a2b3c4d
✓ Deleted IAM user: temporaryaccessAImodelshare1a2b3c4d
  ✓ Deleted access key: AKIAI9876543210GHIJKL
  ✓ Detached policy: temporaryaccessAImodelsharePolicy5e6f7g8h
  ✓ Deleted custom policy: temporaryaccessAImodelsharePolicy5e6f7g8h
✓ Deleted IAM user: temporaryaccessAImodelshare5e6f7g8h

============================================================
Cleanup complete: 4 successful, 0 failed
============================================================
```

### 2. GitHub Action Workflow

A GitHub Actions workflow (`.github/workflows/cleanup-test-resources.yml`) that can be triggered manually to list resources.

#### Usage

1. Go to the "Actions" tab in the GitHub repository
2. Select "Cleanup Test Resources" workflow
3. Click "Run workflow"
4. Select options:
   - **Mode**: `dry-run` (list only) or `interactive` (shows instructions)
   - **Region**: AWS region to scan (default: us-east-1)
5. Click "Run workflow"

#### Modes

**Dry-run mode:**
- Lists all playgrounds and IAM users
- Does not delete anything
- Safe to run anytime

**Interactive mode:**
- Lists resources and provides instructions for local cleanup
- Does not perform deletions (GitHub Actions doesn't support interactive input)
- Use this to identify resources, then run the script locally to delete them

## Safety Features

1. **Dry-run mode**: Preview resources without making changes
2. **Interactive selection**: Choose exactly which resources to delete
3. **Confirmation required**: Type 'DELETE' to confirm in production mode
4. **Prefix filtering**: IAM users filtered by `temporaryaccessAImodelshare` prefix to avoid accidental deletion of other users
5. **Proper cleanup order**: Deletes associated resources before deleting main resources
6. **Error handling**: Continues with other deletions if one fails

## Important Notes

1. **Deletions are permanent**: There is no undo functionality. Always review carefully before confirming.

2. **Check production resources**: The script lists ALL API Gateway APIs in a region. Make sure not to delete production playgrounds.

3. **IAM user filtering**: By default, only IAM users starting with `temporaryaccessAImodelshare` are shown. This prefix is used by the test framework.

4. **Custom policies**: The script will delete custom IAM policies that contain 'temporaryaccess' in their ARN, assuming they were created for test users.

5. **AWS credentials**: Ensure you have appropriate AWS permissions:
   - `apigateway:GET*` and `apigateway:DELETE*` for API Gateway
   - `iam:List*`, `iam:Get*`, `iam:Delete*`, `iam:Detach*` for IAM operations

6. **Multiple regions**: If you've created resources in multiple regions, run the script for each region separately.

## Troubleshooting

**"AWS credentials not configured properly"**
- Configure AWS credentials using one of these methods:
  - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables
  - Configure AWS CLI (`aws configure`)
  - Use IAM role (if running on EC2 or in GitHub Actions)

**"Error listing playgrounds/users"**
- Check AWS permissions
- Verify the region is correct
- Check AWS service health status

**"Error deleting IAM user"**
- The user might have additional resources not handled by the script
- Manually check the user in AWS Console and remove all attachments
- Run the script again

**"Policy cannot be deleted"**
- AWS-managed policies cannot be deleted (only detached)
- Check if the policy is attached to other users or roles

## Best Practices

1. **Regular cleanup**: Run the cleanup script regularly (weekly/monthly) to prevent resource accumulation
2. **Use dry-run first**: Always run with `--dry-run` first to review what would be deleted
3. **Document production resources**: Keep a list of production playground IDs to avoid accidental deletion
4. **Tag resources**: Consider tagging production resources for easier identification
5. **Monitor costs**: Check AWS billing to identify unused resources
