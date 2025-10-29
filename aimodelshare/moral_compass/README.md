# moral_compass API Client

Production-ready Python client for the moral_compass REST API.

## Features

- **Automatic API Discovery**: Finds API base URL from environment variables, cached terraform outputs, or terraform command
- **Retry Logic**: Automatic retries for network errors and 5xx server errors with exponential backoff
- **Pagination**: Simple iterator helpers for paginating through large result sets
- **Type Safety**: Dataclasses for all API responses
- **Structured Exceptions**: Specific exceptions for different error types (NotFoundError, ServerError)
- **Backward Compatibility**: Available via both `aimodelshare.moral_compass` and `moral_compass` import paths
- **Authentication**: Automatic JWT token attachment from environment variables
- **Ownership Enforcement**: Table-level ownership and authorization controls
- **Naming Conventions**: Enforced naming patterns for moral compass tables

## Installation

```bash
pip install -e .  # Install in development mode
```

## Quick Start

```python
from aimodelshare.moral_compass import MoralcompassApiClient

# Create client (auto-discovers API URL from environment)
client = MoralcompassApiClient()

# Or specify URL explicitly
client = MoralcompassApiClient(api_base_url="https://api.example.com")

# Check API health
health = client.health()
print(health)

# Create a table
client.create_table("my-table", "My Display Name")

# Get table info
table = client.get_table("my-table")
print(f"Table: {table.table_id}, Users: {table.user_count}")

# List all tables with automatic pagination
for table in client.iter_tables():
    print(f"- {table.table_id}: {table.display_name}")

# Add a user to a table
client.put_user("my-table", "user1", submission_count=10, total_count=100)

# Get user stats
user = client.get_user("my-table", "user1")
print(f"User {user.username}: {user.submission_count} submissions")

# List all users in a table
for user in client.iter_users("my-table"):
    print(f"- {user.username}: {user.submission_count} submissions")
```

## Authentication & Authorization

The moral compass API supports authentication and authorization controls when `AUTH_ENABLED=true` on the server.

> **⚠️ SECURITY WARNING**  
> JWT signature verification is currently a **stub implementation** that performs unverified token decoding.  
> **DO NOT use in production** for security-critical operations without implementing JWKS-based signature verification.  
> This is suitable for development and testing only.

### Authentication Token

The client automatically attaches JWT authentication tokens from environment variables:

```bash
# Preferred: Use JWT_AUTHORIZATION_TOKEN
export JWT_AUTHORIZATION_TOKEN="your.jwt.token"

# Legacy: AWS_TOKEN (deprecated, triggers warning)
export AWS_TOKEN="your.aws.token"
```

You can also provide the token explicitly:

```python
from aimodelshare.moral_compass import MoralcompassApiClient

# Explicit token
client = MoralcompassApiClient(auth_token="your.jwt.token")

# Auto-discover from environment
client = MoralcompassApiClient()  # Uses JWT_AUTHORIZATION_TOKEN or AWS_TOKEN
```

### Automatic Token Acquisition

If no JWT token is found in environment variables, the client will attempt to auto-generate one using username and password credentials. This provides seamless integration when users have already configured credentials via `configure_credentials()`:

```bash
# Set credentials for automatic JWT generation
export AIMODELSHARE_USERNAME="your-username"
export AIMODELSHARE_PASSWORD="your-password"

# Alternative variable names also supported
export username="your-username"
export password="your-password"
```

```python
from aimodelshare.moral_compass import MoralcompassApiClient
from aimodelshare.modeluser import get_jwt_token
import os

# Method 1: Let the client auto-generate (recommended)
# Client will automatically use AIMODELSHARE_USERNAME/AIMODELSHARE_PASSWORD
client = MoralcompassApiClient()

# Method 2: Explicitly generate and set JWT token
if not os.getenv('JWT_AUTHORIZATION_TOKEN'):
    username = os.getenv('AIMODELSHARE_USERNAME')
    password = os.getenv('AIMODELSHARE_PASSWORD')
    if username and password:
        get_jwt_token(username, password)  # Sets JWT_AUTHORIZATION_TOKEN
        # Now JWT_AUTHORIZATION_TOKEN is available for subsequent API calls

client = MoralcompassApiClient()
```

The auto-generation process:
1. Checks for existing JWT_AUTHORIZATION_TOKEN (skips if found)
2. Looks for AIMODELSHARE_USERNAME/AIMODELSHARE_PASSWORD or username/password
3. Calls `get_jwt_token()` to generate and set JWT_AUTHORIZATION_TOKEN
4. Uses the generated token for API authentication
5. Logs success/failure for debugging

### Table Ownership

When authentication is enabled, tables have ownership metadata:

```python
# Create a table for a playground (stores owner identity)
response = client.create_table(
    table_id="my-playground-mc",
    display_name="My Moral Compass Table",
    playground_url="https://example.com/playground/my-playground"
)
# Response is a dict with structure:
# {
#     'tableId': 'my-playground-mc',
#     'displayName': 'My Moral Compass Table',
#     'ownerPrincipal': 'user@example.com',  # Owner's identity
#     'playgroundId': 'my-playground',
#     'message': 'Table created successfully'
# }
print(response['ownerPrincipal'])  # Shows who created the table

# Convenience method to create with naming convention
response = client.create_table_for_playground(
    playground_url="https://example.com/playground/my-playground",
    suffix="-mc"  # Creates table: my-playground-mc
)
```

### Naming Convention

When `MC_ENFORCE_NAMING=true` on the server, moral compass tables must follow the pattern: `<playgroundId>-mc`

```python
# Valid: Follows naming convention
client.create_table(
    table_id="my-playground-mc",
    playground_url="https://example.com/playground/my-playground"
)

# Invalid: Will return 400 error if MC_ENFORCE_NAMING=true
client.create_table(
    table_id="random-name",
    playground_url="https://example.com/playground/my-playground"
)
```

### Authorization Rules

When `AUTH_ENABLED=true`:

- **Table Creation**: Only authenticated users can create tables
- **Table Deletion**: Only the owner or admin can delete tables (requires `ALLOW_TABLE_DELETE=true`)
- **User Updates**: Only the user themselves or admin can update their progress
- **Read Operations**: Public by default when `ALLOW_PUBLIC_READ=true`

```python
# Delete a table (owner or admin only)
client.delete_table("my-playground-mc")

# Update own progress
client.update_moral_compass(
    table_id="my-playground-mc",
    username="my-username",
    metrics={"accuracy": 0.85},
    tasks_completed=3,
    total_tasks=6
)
```

### Helper Functions

Use the `aimodelshare.auth` module for identity management:

```python
from aimodelshare.auth import get_primary_token, get_identity_claims

# Get token from environment
token = get_primary_token()

# Extract identity claims (DEVELOPMENT ONLY - signature not verified)
if token:
    # Currently verify=False (stub implementation)
    # TODO: Use verify=True after implementing JWKS verification for production
    claims = get_identity_claims(token, verify=False)
    print(f"User: {claims['principal']}")
    print(f"Email: {claims.get('email')}")
    print(f"Subject: {claims['sub']}")
```

## API Base URL Configuration

The client discovers the API base URL using the following priority:

1. **Environment Variable**: `MORAL_COMPASS_API_BASE_URL` or `AIMODELSHARE_API_BASE_URL`
2. **Cached Terraform Outputs**: `infra/terraform_outputs.json`
3. **Terraform Command**: Runs `terraform output -raw api_base_url` in the `infra/` directory
4. **Explicit Parameter**: Pass `api_base_url` to the client constructor

```bash
# Set via environment variable
export MORAL_COMPASS_API_BASE_URL="https://your-api.example.com"
```

## Error Handling

```python
from aimodelshare.moral_compass import (
    MoralcompassApiClient,
    NotFoundError,
    ServerError,
    ApiClientError
)

client = MoralcompassApiClient()

try:
    table = client.get_table("nonexistent-table")
except NotFoundError:
    print("Table not found (404)")
except ServerError:
    print("Server error (5xx)")
except ApiClientError as e:
    print(f"API error: {e}")
```

## Pagination

### Manual Pagination

```python
# Get first page
response = client.list_tables(limit=10)
tables = response["tables"]
last_key = response.get("lastKey")

# Get next page if available
if last_key:
    response = client.list_tables(limit=10, last_key=last_key)
    tables.extend(response["tables"])
```

### Automatic Pagination with Iterators

```python
# Automatically handles pagination behind the scenes
for table in client.iter_tables(limit=50):
    print(table.table_id)

for user in client.iter_users("my-table", limit=50):
    print(user.username)
```

## Dataclasses

### MoralcompassTableMeta

```python
from aimodelshare.moral_compass import MoralcompassTableMeta

table = MoralcompassTableMeta(
    table_id="my-table",
    display_name="My Table",
    created_at="2024-01-01T00:00:00Z",
    is_archived=False,
    user_count=42
)
```

### MoralcompassUserStats

```python
from aimodelshare.moral_compass import MoralcompassUserStats

user = MoralcompassUserStats(
    username="user1",
    submission_count=10,
    total_count=100,
    last_updated="2024-01-01T12:00:00Z"
)
```

## Backward Compatibility

Both import paths are supported:

```python
# New path (recommended)
from aimodelshare.moral_compass import MoralcompassApiClient

# Legacy path (backward compatible)
from moral_compass import MoralcompassApiClient
```

## API Methods

### Tables

- `create_table(table_id, display_name=None, playground_url=None)` - Create a new table
- `create_table_for_playground(playground_url, suffix='-mc', display_name=None)` - Create table with naming convention
- `list_tables(limit=50, last_key=None)` - List tables with pagination
- `iter_tables(limit=50)` - Iterate all tables with automatic pagination
- `get_table(table_id)` - Get specific table metadata
- `patch_table(table_id, display_name=None, is_archived=None)` - Update table metadata
- `delete_table(table_id)` - Delete a table (requires owner/admin auth)

### Users

- `put_user(table_id, username, submission_count, total_count)` - Create/update user
- `get_user(table_id, username)` - Get user stats
- `list_users(table_id, limit=50, last_key=None)` - List users with pagination
- `iter_users(table_id, limit=50)` - Iterate all users with automatic pagination
- `update_moral_compass(table_id, username, metrics, tasks_completed=0, total_tasks=0, questions_correct=0, total_questions=0, primary_metric=None)` - Update user's moral compass score

### Health

- `health()` - Check API health status

## Testing

### Unit Tests

```bash
# Run all tests except integration tests
pytest -m "not integration"
```

### Integration Tests

```bash
# Requires deployed API with MORAL_COMPASS_API_BASE_URL set
export MORAL_COMPASS_API_BASE_URL="https://your-api.example.com"
pytest -m integration tests/test_moral_compass_client_minimal.py -v
```

## CI/CD Integration

The deploy-infra workflow automatically:
1. Caches terraform outputs
2. Verifies API health endpoint is reachable
3. Installs the package in editable mode
4. Runs integration tests

See `.github/workflows/deploy-infra.yml` for details.

## Scripts

### Cache Terraform Outputs

```bash
bash scripts/cache_terraform_outputs.sh
```

Exports `MORAL_COMPASS_API_BASE_URL` and writes `infra/terraform_outputs.json`.

### Verify API Health

```bash
bash scripts/verify_api_reachable.sh [API_BASE_URL]
```

Checks that the `/health` endpoint is reachable with retries.

## Version

Current version: 0.1.0

```python
from aimodelshare.moral_compass import __version__
print(__version__)  # "0.1.0"
```

## License

Same as parent aimodelshare package.
