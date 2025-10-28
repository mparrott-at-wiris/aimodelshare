# Region-Aware Naming for Moral Compass Tables

## Overview

Moral Compass tables now support region-aware naming to enable the same playground to have separate tables in different AWS regions. This is useful for:

- Multi-region deployments
- Regional data isolation
- Compliance requirements (e.g., data residency)
- Testing across regions

## Naming Conventions

### Non-Region-Aware (Traditional)
Tables can use the standard naming pattern:
```
<playgroundId>-mc
```

Example: `my-playground-mc`

### Region-Aware (New)
Tables can include the AWS region in their name:
```
<playgroundId>-<region>-mc
```

Example: `my-playground-us-east-1-mc`

The region must follow AWS region format: `<area>-<location>-<number>` (e.g., `us-east-1`, `eu-west-2`, `ap-south-1`)

## Usage

### Python API Client

#### Creating a region-aware table

```python
from aimodelshare.moral_compass import MoralcompassApiClient

client = MoralcompassApiClient()

# Create table for a specific region
result = client.create_table_for_playground(
    playground_url='https://example.com/playground/my-playground',
    region='us-east-1'  # Specify the AWS region
)
# Creates table: my-playground-us-east-1-mc

# Create table for another region
result = client.create_table_for_playground(
    playground_url='https://example.com/playground/my-playground',
    region='eu-west-2'
)
# Creates table: my-playground-eu-west-2-mc
```

#### Creating a non-region-aware table (backward compatible)

```python
# Omit the region parameter for traditional naming
result = client.create_table_for_playground(
    playground_url='https://example.com/playground/my-playground'
)
# Creates table: my-playground-mc
```

#### Direct table creation

```python
# You can also create tables directly with the full table ID
client.create_table(
    table_id='my-playground-us-east-1-mc',
    display_name='My Playground (US East 1)',
    playground_url='https://example.com/playground/my-playground'
)
```

### Discovering the Current Region

```python
from aimodelshare.moral_compass import get_aws_region

# Get the current AWS region
region = get_aws_region()

if region:
    print(f"Current region: {region}")
    
    # Use it to create a region-aware table
    result = client.create_table_for_playground(
        playground_url='https://example.com/playground/my-playground',
        region=region
    )
else:
    # No region configured, use traditional naming
    result = client.create_table_for_playground(
        playground_url='https://example.com/playground/my-playground'
    )
```

### Region Discovery

The `get_aws_region()` function discovers the AWS region from multiple sources in order:

1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. Cached terraform outputs (`infra/terraform_outputs.json`)
4. Returns `None` if no region is found

## Infrastructure Configuration

### Terraform

The AWS region is automatically passed to the Lambda function:

```hcl
# infra/main.tf
resource "aws_lambda_function" "api" {
  # ...
  environment {
    variables = {
      AWS_REGION_NAME = var.region
      # ... other variables
    }
  }
}
```

### Lambda Function

The Lambda function automatically:
- Extracts the region from region-aware table IDs
- Validates the region format (must match AWS region pattern)
- Stores region metadata in the table record

## Metadata

When a table is created with region-aware naming, the metadata includes:

```json
{
  "tableId": "my-playground-us-east-1-mc",
  "playgroundId": "my-playground",
  "region": "us-east-1",
  "displayName": "My Playground (us-east-1)",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "..."
}
```

For non-region-aware tables, the region defaults to the deployment region:

```json
{
  "tableId": "my-playground-mc",
  "playgroundId": "my-playground",
  "region": "us-east-1",  // Deployment region
  "displayName": "My Playground",
  "..."
}
```

## Validation

When `MC_ENFORCE_NAMING=true`, the Lambda function validates:

1. **Non-region-aware**: Table ID must match `<playgroundId>-mc`
2. **Region-aware**: Table ID must match `<playgroundId>-<region>-mc` where region follows AWS format

Invalid examples:
- `my-playground-invalid-mc` (invalid region format)
- `wrong-playground-mc` (playground ID mismatch)
- `my-playground-us-east-mc` (missing region number)

## Use Cases

### Multi-Region Deployment

```python
# Create tables for different regions
regions = ['us-east-1', 'eu-west-2', 'ap-south-1']

for region in regions:
    client.create_table_for_playground(
        playground_url='https://example.com/playground/global-app',
        region=region,
        display_name=f'Global App ({region})'
    )
```

### Region-Specific Data Access

```python
# Access region-specific data
region = get_aws_region() or 'us-east-1'
table_id = f'my-playground-{region}-mc'

user_data = client.get_user(table_id, 'user123')
```

### Migration from Non-Region-Aware to Region-Aware

```python
# Old table (non-region-aware)
old_table_id = 'my-playground-mc'

# Create new region-aware table
new_table_id = 'my-playground-us-east-1-mc'
client.create_table_for_playground(
    playground_url='https://example.com/playground/my-playground',
    region='us-east-1'
)

# Migrate data (pseudo-code)
# ... copy users from old_table_id to new_table_id

# Optionally archive the old table
client.patch_table(old_table_id, is_archived=True)
```

## Backward Compatibility

All existing functionality remains backward compatible:

- Tables without region in the name continue to work
- The `region` parameter is optional in `create_table_for_playground()`
- Existing tables are not affected
- Non-region-aware table creation still works as before

## Testing

Run the test suite to verify region-aware naming:

```bash
python -m pytest tests/test_region_aware_naming.py -v
```

This tests:
- Region extraction from table IDs
- Table name validation
- API client region parameter
- Region discovery
