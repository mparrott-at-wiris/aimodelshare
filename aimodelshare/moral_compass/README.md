# moral_compass API Client

Production-ready Python client for the moral_compass REST API.

## Features

- **Automatic API Discovery**: Finds API base URL from environment variables, cached terraform outputs, or terraform command
- **Retry Logic**: Automatic retries for network errors and 5xx server errors with exponential backoff
- **Pagination**: Simple iterator helpers for paginating through large result sets
- **Type Safety**: Dataclasses for all API responses
- **Structured Exceptions**: Specific exceptions for different error types (NotFoundError, ServerError)
- **Backward Compatibility**: Available via both `aimodelshare.moral_compass` and `moral_compass` import paths

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

- `create_table(table_id, display_name=None)` - Create a new table
- `list_tables(limit=50, last_key=None)` - List tables with pagination
- `iter_tables(limit=50)` - Iterate all tables with automatic pagination
- `get_table(table_id)` - Get specific table metadata
- `patch_table(table_id, display_name=None, is_archived=None)` - Update table metadata

### Users

- `put_user(table_id, username, submission_count, total_count)` - Create/update user
- `get_user(table_id, username)` - Get user stats
- `list_users(table_id, limit=50, last_key=None)` - List users with pagination
- `iter_users(table_id, limit=50)` - Iterate all users with automatic pagination

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
