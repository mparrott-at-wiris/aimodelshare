# IAM Refactoring Guide

This guide documents the architectural changes made to improve security and reduce IAM resource proliferation in the AIModelShare library.

## Overview

The library has been refactored to:
1. **Eliminate ephemeral IAM users** - Replace per-run IAM user creation with STS AssumeRole sessions
2. **Consolidate IAM roles** - Use reusable, shared IAM roles instead of creating unique roles per API/deployment
3. **Implement least privilege** - Restrict overly broad S3 permissions to specific actions and buckets
4. **Idempotent resource provisioning** - Use utilities that ensure resources exist without creating duplicates

## Key Changes

### 1. STS AssumeRole for Authentication

**Old Behavior:**
- Created a new IAM user with long-term credentials for each run
- Generated access keys stored in environment variables
- Created ephemeral managed policies with random names

**New Behavior:**
- Uses STS AssumeRole to obtain temporary credentials (default)
- Requires `AIMODELSHARE_EXECUTION_ROLE_ARN` environment variable
- Backward compatibility available via `use_ephemeral_users=True` flag (deprecated)

**Migration Steps:**

1. Create an execution role in your AWS account:
```bash
# Example role trust policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT:user/YOUR_USER"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

2. Set the environment variable:
```python
import os
os.environ["AIMODELSHARE_EXECUTION_ROLE_ARN"] = "arn:aws:iam::YOUR_ACCOUNT:role/aimodelshare-execution-role"
```

3. Update your code:
```python
# Old (deprecated)
from aimodelshare.modeluser import create_user_getkeyandpassword
create_user_getkeyandpassword()  # Creates IAM user

# New (recommended)
from aimodelshare.modeluser import create_user_getkeyandpassword
create_user_getkeyandpassword()  # Verifies role ARN is set

# Or use STS session directly
from aimodelshare.modeluser import get_execution_session
session = get_execution_session()
```

### 2. Consolidated IAM Roles

**Old Behavior:**
- CodeBuild: Created `codebuild_role` and `codebuild_policy` per run, deleted/recreated each time
- Lambda (containerization): Created `lambda_role_<api_id>` and `lambda_policy_<api_id>` per API
- Lambda (API): Created `myService-dev-us-<region>-lambdaRole<uuid>` per deployment
- API Gateway: Created `lambda_invoke_function_assume_apigw_role_2` per deployment

**New Behavior:**
- **CodeBuild**: Uses single reusable `aimodelshare-codebuild-role` with `aimodelshare-codebuild-policy`
- **Lambda Execution**: Uses single reusable `aimodelshare-lambda-exec` with `aimodelshare-lambda-exec-policy`
- **API Lambda**: Uses single reusable `aimodelshare-api-lambda-role` with `aimodelshare-api-lambda-policy`
- **API Gateway Invocation**: Uses single reusable `aimodelshare-apigw-invoke-role` with `aimodelshare-apigw-invoke-policy`

**Benefits:**
- Reduced IAM resource count (from N roles/policies to 4 shared ones)
- Simplified cleanup (no orphaned resources)
- Easier auditing and compliance
- Faster deployments (no role creation/deletion delays)

### 3. Restricted S3 Permissions

**Old Behavior:**
```json
{
  "Action": "s3:*",
  "Resource": "*"
}
```

**New Behavior:**
```json
{
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::aimodelshare*",
    "arn:aws:s3:::aimodelshare*/*"
  ]
}
```

**Benefits:**
- Follows principle of least privilege
- Limits access to only necessary S3 actions
- Scopes permissions to aimodelshare buckets only
- Reduces risk of accidental data access/modification

### 4. New IAM Utils Module

A new module `aimodelshare/iam_utils.py` provides idempotent resource provisioning:

**Functions:**
- `ensure_bucket(s3_client, bucket_name, region)` - Creates bucket if it doesn't exist
- `ensure_role(iam_client, role_name, trust_relationship, description)` - Creates/updates role
- `ensure_managed_policy(iam_client, policy_name, policy_document, description)` - Creates/updates policy with version management
- `ensure_inline_policy(iam_client, role_name, policy_name, policy_document)` - Creates/updates inline policy
- `canonical_policy_doc(policy_dict)` - Normalizes policy document for comparison
- `policy_hash(policy_dict)` - Generates hash for policy comparison
- `attach_managed_policy_to_role(iam_client, role_name, policy_arn)` - Attaches policy if not already attached

**Usage Example:**
```python
from aimodelshare import iam_utils
import boto3

iam_client = boto3.client('iam')

# Ensure role exists with correct trust policy
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}
created, updated = iam_utils.ensure_role(
    iam_client, 
    "my-lambda-role", 
    trust_policy,
    description="Lambda execution role"
)

# Ensure managed policy exists
policy_doc = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": ["arn:aws:s3:::my-bucket/*"]
    }]
}
policy_arn, created, updated = iam_utils.ensure_managed_policy(
    iam_client,
    "my-lambda-policy",
    policy_doc,
    description="Lambda S3 access policy"
)

# Attach policy to role
iam_utils.attach_managed_policy_to_role(iam_client, "my-lambda-role", policy_arn)
```

## Files Modified

### Core Modules
- **`aimodelshare/iam_utils.py`** (NEW) - Idempotent IAM resource provisioning utilities
- **`aimodelshare/modeluser.py`** - Added STS AssumeRole support, deprecated IAM user creation
- **`aimodelshare/containerization.py`** - Uses reusable CodeBuild and Lambda roles
- **`aimodelshare/api.py`** - Uses reusable API Lambda and API Gateway roles
- **`aimodelshare/bucketpolicy.py`** - Restricted S3 permissions to specific actions

### Policy Templates
- **`aimodelshare/iam/codebuild_policy.txt`** - Restricted S3 permissions to aimodelshare* buckets
- **`aimodelshare/iam/lambda_policy.txt`** - Restricted S3 permissions to aimodelshare* buckets
- **`aimodelshare/json_templates/lambda_policy_1.txt`** - Restricted S3 permissions to aimodelshare* buckets

## Backward Compatibility

The refactoring maintains backward compatibility:

1. **Ephemeral IAM users** can still be used by setting `use_ephemeral_users=True`:
   ```python
   from aimodelshare.modeluser import create_user_getkeyandpassword
   create_user_getkeyandpassword(use_ephemeral_users=True)  # Deprecated, emits warning
   ```

2. **Existing deployments** continue to work - only new deployments use consolidated roles

3. **Gradual migration** is supported - you can migrate at your own pace

## Recommendations

1. **For new deployments:**
   - Set up `AIMODELSHARE_EXECUTION_ROLE_ARN` 
   - Use default `create_user_getkeyandpassword()` (no IAM user creation)
   - Benefit from consolidated roles and improved security

2. **For existing deployments:**
   - Continue using existing credentials
   - Plan migration to STS AssumeRole for better security
   - Clean up orphaned IAM users and policies from old deployments

3. **Security best practices:**
   - Regularly rotate the execution role's access
   - Monitor STS AssumeRole activity via CloudTrail
   - Use IAM conditions to further restrict role usage (e.g., IP address, time of day)
   - Review and audit the consolidated roles periodically

## Troubleshooting

### Error: "AIMODELSHARE_EXECUTION_ROLE_ARN environment variable must be set"
**Solution:** Either:
1. Set the environment variable: `os.environ["AIMODELSHARE_EXECUTION_ROLE_ARN"] = "arn:aws:iam::..."`
2. Use deprecated path: `create_user_getkeyandpassword(use_ephemeral_users=True)`

### Error: "Failed to assume role"
**Possible causes:**
1. Role ARN is incorrect
2. Your IAM user/role doesn't have permission to assume the role
3. Role's trust policy doesn't allow your principal

**Solution:** Verify the role ARN and trust policy, ensure your credentials have `sts:AssumeRole` permission.

### Roles not being created
**Solution:** The new utilities are idempotent - if roles already exist with different configurations, they will be updated. Check IAM console to verify role existence and configuration.

## Support

For questions or issues related to this refactoring, please refer to:
- This guide
- Code comments in `iam_utils.py`
- AIModelShare documentation at aimodelshare.com
