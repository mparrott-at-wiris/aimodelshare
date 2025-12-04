# Moral Compass Comprehensive Integration Test

## Overview

This integration test suite (`test_moral_compass_comprehensive_integration.py`) provides thorough testing of the REST API and Lambda functions used for the Moral Compass user and table tracking data. It validates all functionality required for the Detective Bias app.

## What It Tests

The integration test covers 10 comprehensive test scenarios:

### 1. Table Management
- **Test 1**: Create a table with playground URL
- **Test 2**: Find table by ID without authentication (tests public read access)
- **Test 3**: Find table by ID with authentication

### 2. User Management with Moral Compass Scoring
- **Test 4**: Create 10 users with varying accuracy scores (0.78-0.96), tasks completed (6-18), and team assignments (A, B, C)
- **Test 5**: Retrieve all user information from the table
- **Test 6**: Verify moral compass score calculation (accuracy × tasks completed)
- **Test 7**: Update user with new accuracy score and verify score updates correctly

### 3. Team Information
- **Test 8**: Verify team information can be added and retrieved for each user

### 4. Rankings
- **Test 9**: Compute and display individual rankings by moral compass score
- **Test 10**: Compute and display team rankings by average individual score per team

## Requirements

### Environment Variables

**Required:**
- `MORAL_COMPASS_API_BASE_URL`: Base URL for the REST API
  - Example: `https://abc123.execute-api.us-east-1.amazonaws.com/prod`

**Optional (Authentication - choose one):**
- `SESSION_ID`: Session ID to fetch JWT token from session API (recommended)
  - The test will automatically fetch the JWT token using the session API
  - Takes precedence over JWT_AUTHORIZATION_TOKEN if both are provided
- `JWT_AUTHORIZATION_TOKEN`: JWT token for authenticated requests
  - Direct JWT token (use if SESSION_ID is not available)

**Optional (Test Configuration):**
- `TEST_PLAYGROUND_URL`: Playground URL for table derivation
  - Default: Auto-generated based on test table ID
- `TEST_TABLE_ID`: Explicit table ID for testing
  - Default: Auto-generated unique ID like `test-mc-comprehensive-abc12345`

### Python Dependencies

The test requires the following packages:
- `aimodelshare` (with moral_compass module)
- `requests` (transitive dependency)

## Usage

### Basic Usage (No Authentication)

```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.amazonaws.com/prod
python tests/test_moral_compass_comprehensive_integration.py
```

### With Authentication (Session ID - Recommended)

```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.amazonaws.com/prod
export SESSION_ID=your-session-id
python tests/test_moral_compass_comprehensive_integration.py
```

The test will automatically fetch the JWT token from the session API using the provided session ID.

### With Authentication (Direct JWT Token)

```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.amazonaws.com/prod
export JWT_AUTHORIZATION_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
python tests/test_moral_compass_comprehensive_integration.py
```

### With Custom Table ID

```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.amazonaws.com/prod
export TEST_TABLE_ID=my-test-table-mc
python tests/test_moral_compass_comprehensive_integration.py
```

### Running with pytest

```bash
pytest tests/test_moral_compass_comprehensive_integration.py -v -s
```

## Test Data

The test creates the following user configuration:

| Username | Team | Accuracy | Tasks | Expected Score |
|----------|------|----------|-------|----------------|
| user-a-1 | team-a | 0.95 | 10 | 9.5 |
| user-a-2 | team-a | 0.85 | 15 | 12.75 |
| user-a-3 | team-a | 0.90 | 12 | 10.8 |
| user-b-1 | team-b | 0.92 | 8 | 7.36 |
| user-b-2 | team-b | 0.88 | 14 | 12.32 |
| user-b-3 | team-b | 0.78 | 18 | 14.04 |
| user-b-4 | team-b | 0.96 | 6 | 5.76 |
| user-c-1 | team-c | 0.89 | 11 | 9.79 |
| user-c-2 | team-c | 0.93 | 9 | 8.37 |
| user-c-3 | team-c | 0.87 | 13 | 11.31 |

### Expected Team Rankings

Based on average scores (descending order):
1. **Team A**: Average ~11.02 (3 members)
2. **Team B**: Average ~9.87 (4 members)
3. **Team C**: Average ~9.82 (3 members)

## Expected Output

The test produces detailed output including:

```
================================================================================
MORAL COMPASS COMPREHENSIVE INTEGRATION TEST SUITE
================================================================================
API Base URL: https://your-api-url.amazonaws.com/prod
Test Table ID: test-mc-comprehensive-abc12345
Auth Enabled: True
================================================================================

======================================================================
TEST: Create Table with Playground URL
======================================================================
✅ PASS: Create Table with Playground URL
   Created table: test-mc-comprehensive-abc12345

... [additional test output] ...

   Individual Rankings:
   Rank   Username                       Score      Team      
   ------------------------------------------------------------
   #1     user-b-3                       14.0400    team-b    
   #2     user-a-2                       12.7500    team-a    
   #3     user-b-2                       12.3200    team-b    

   Team Rankings:
   Rank   Team            Avg Score    Members   
   --------------------------------------------------
   #1     team-a          11.0167      3         
   #2     team-b          9.8700       4         
   #3     team-c          9.8233       3         

================================================================================
TEST SUMMARY
================================================================================
Total Tests: 10
Passed: 10
Failed: 0

✅ ALL TESTS PASSED!
================================================================================
```

## Cleanup

The test automatically attempts to clean up the test table after execution. If cleanup fails, you can manually delete the test table:

```bash
# Using the API
curl -X DELETE "https://your-api-url.amazonaws.com/prod/tables/test-mc-comprehensive-abc12345" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Troubleshooting

### "MORAL_COMPASS_API_BASE_URL environment variable is required"

Set the environment variable before running:
```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.amazonaws.com/prod
```

### Authentication Errors (401)

If you see authentication errors:
1. Verify your JWT token is valid: `echo $JWT_AUTHORIZATION_TOKEN`
2. Check if the API has `AUTH_ENABLED=true`
3. If auth is not required, the test will handle this gracefully in Test 2

### Connection Errors

If you see connection errors:
1. Verify the API URL is correct and accessible
2. Check if the Lambda/API Gateway is deployed and running
3. Verify network connectivity

### Test Failures

If specific tests fail:
1. Check the error message for details
2. Verify the Lambda function is properly configured
3. Check DynamoDB table permissions
4. Review CloudWatch logs for the Lambda function

## Integration with CI/CD

To run this test in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Moral Compass Integration Tests
  env:
    MORAL_COMPASS_API_BASE_URL: ${{ secrets.MORAL_COMPASS_API_URL }}
    JWT_AUTHORIZATION_TOKEN: ${{ secrets.JWT_TOKEN }}
  run: |
    python tests/test_moral_compass_comprehensive_integration.py
```

## Phase II Considerations

This integration test helps determine if new functionality is required for the database Lambda API architecture. After running the test, evaluate:

1. **Performance**: Are response times acceptable for the Detective Bias app?
2. **Scalability**: Can the API handle multiple users updating simultaneously?
3. **Feature Gaps**: Are there any missing features identified during testing?
4. **Error Handling**: Are error messages clear and actionable?

Document any issues or enhancement needs for Phase II implementation.

## Additional Resources

- Lambda Function: `/infra/lambda/app.py`
- API Client: `/aimodelshare/moral_compass/api_client.py`
- Integration Helpers: `/aimodelshare/moral_compass/apps/mc_integration_helpers.py`
- Existing Tests: `/tests/test_moral_compass_*.py`
