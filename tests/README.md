# Tests

This directory contains tests for the aimodelshare project.

## Test Files

- `test_playground.py` - Tests for the ModelPlayground functionality including sklearn, keras, and pytorch model testing
- `test_aimsonnx.py` - Tests for ONNX model functionality
- `test_api_integration.py` - **API Integration Tests for the deployed REST API**

## API Integration Tests

The `test_api_integration.py` script contains comprehensive integration tests for the REST API deployed via the GitHub Actions workflow.

### What it Tests

The script tests all main API endpoints:

- **GET /tables** - List all logical tables
- **POST /tables** - Create a new logical table
- **GET /tables/{tableId}** - Get specific table metadata
- **PATCH /tables/{tableId}** - Update table metadata (archive/unarchive)
- **GET /tables/{tableId}/users** - List all users for a table
- **GET /tables/{tableId}/users/{username}** - Get specific user data
- **PUT /tables/{tableId}/users/{username}** - Update or create user data

### Usage

```bash
# Run integration tests against a deployed API
python tests/test_api_integration.py <api_base_url>

# Example:
python tests/test_api_integration.py https://abc123.execute-api.us-east-1.amazonaws.com/dev
```

### Features

- ✅ **Complete endpoint coverage** - Tests all 7 main API operations
- ✅ **Error case testing** - Tests invalid inputs and edge cases
- ✅ **API readiness check** - Waits for API to be available before testing
- ✅ **Detailed logging** - Clear output with emojis for easy reading
- ✅ **Unique test data** - Uses UUIDs to avoid conflicts
- ✅ **Proper cleanup** - Creates and manages test data safely
- ✅ **Timeout handling** - Robust network request handling

### Automatic Execution

These tests are automatically run as part of the deployment process in the GitHub Actions workflow (`.github/workflows/deploy-infra.yml`). They execute after the infrastructure is successfully deployed to validate that the API is working correctly.

### Dependencies

The integration tests require the `requests` library, which is automatically installed during the workflow execution.

### Test Output

The tests provide clear output with status indicators:

- ✅ Green checkmarks for passed tests
- ❌ Red X marks for failed tests
- 🚀 Rocket for test start
- ⏳ Hourglass for waiting/retry operations
- 🔍 Magnifying glass for checks

Example output:
```
🚀 Starting API Integration Tests
🔗 API Base URL: https://abc123.execute-api.us-east-1.amazonaws.com/dev
🧪 Test Table ID: test-table-c25cc68d
👤 Test Username: testuser-7430d113
------------------------------------------------------------
🔍 Checking API availability...
✅ API is ready (attempt 1)
✅ test_list_tables_empty: PASSED
✅ test_create_table: PASSED
✅ test_create_duplicate_table: PASSED
...
------------------------------------------------------------
✅ All 14 tests passed successfully!
```