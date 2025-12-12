# Quick Start: Moral Compass Integration Test

## TL;DR

Run this comprehensive integration test to validate your Moral Compass API:

```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
export SESSION_ID=your-session-id  # Recommended - fetches JWT token automatically
# OR
export JWT_AUTHORIZATION_TOKEN=your-jwt-token  # Alternative: use direct JWT token
python tests/test_moral_compass_comprehensive_integration.py
```

## What It Tests (10 Scenarios)

1. ✅ Create table with playground URL
2. ✅ Find table without auth (public read)
3. ✅ Find table with auth
4. ✅ Create 10 users (teams A, B, C)
5. ✅ Retrieve all users
6. ✅ Verify moral compass score = accuracy × tasks
7. ✅ Update user accuracy & tasks
8. ✅ Verify team assignments
9. ✅ Individual rankings by score
10. ✅ Team rankings by average score

## Test Data

- **10 users** across 3 teams
- **Accuracy**: 0.78 - 0.96
- **Tasks**: 6 - 18
- **Teams**: team-a (3), team-b (4), team-c (3)

## Expected Results

```
================================================================================
TEST SUMMARY
================================================================================
Total Tests: 10
Passed: 10
Failed: 0

✅ ALL TESTS PASSED!
```

## Quick Links

| Document | Purpose |
|----------|---------|
| [test_moral_compass_comprehensive_integration.py](./test_moral_compass_comprehensive_integration.py) | Main test code |
| [MORAL_COMPASS_INTEGRATION_TEST_README.md](./MORAL_COMPASS_INTEGRATION_TEST_README.md) | Full documentation |
| [MORAL_COMPASS_TEST_COVERAGE.md](./MORAL_COMPASS_TEST_COVERAGE.md) | Requirements coverage |
| [../scripts/run_moral_compass_integration_test.sh](../scripts/run_moral_compass_integration_test.sh) | Bash runner script |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MORAL_COMPASS_API_BASE_URL` | **Yes** | API endpoint URL |
| `SESSION_ID` | No | Session ID (fetches JWT token automatically) |
| `JWT_AUTHORIZATION_TOKEN` | No | Direct JWT token (if SESSION_ID not provided) |
| `TEST_TABLE_ID` | No | Custom table ID |
| `TEST_PLAYGROUND_URL` | No | Custom playground URL |

**Note**: If both `SESSION_ID` and `JWT_AUTHORIZATION_TOKEN` are provided, `SESSION_ID` takes precedence.

## Alternative Run Methods

### With Session ID (Recommended)
```bash
export SESSION_ID=your-session-id
python tests/test_moral_compass_comprehensive_integration.py
```

### Using Runner Script
```bash
./scripts/run_moral_compass_integration_test.sh \
  https://your-api.com/prod \
  your-jwt-token
```

### Using pytest
```bash
pytest tests/test_moral_compass_comprehensive_integration.py -v -s
```

### No Auth
```bash
unset SESSION_ID
unset JWT_AUTHORIZATION_TOKEN
python tests/test_moral_compass_comprehensive_integration.py
```

## Common Issues

### "MORAL_COMPASS_API_BASE_URL is required"
➜ Set the environment variable:
```bash
export MORAL_COMPASS_API_BASE_URL=https://your-api-url.com/prod
```

### Authentication errors (401)
➜ Check if auth is enabled and token is valid:
```bash
export JWT_AUTHORIZATION_TOKEN=eyJ...
```

### Connection timeout
➜ Verify API is deployed and accessible

## What Happens

1. Creates test table: `test-mc-comprehensive-XXXXXXXX`
2. Creates 10 users with varying data
3. Tests all API operations
4. Computes rankings
5. Cleans up test table
6. Reports results

## Output Sample

```
======================================================================
TEST: Create 10 Users with Varying Data
======================================================================
   Created user: user-a-1-abc12345 - accuracy=0.95, tasks=10, team=team-a, expected_score=9.5000
   Created user: user-a-2-abc12345 - accuracy=0.85, tasks=15, team=team-a, expected_score=12.7500
   ...
✅ PASS: Create 10 Users with Varying Data
   Created all 10 users successfully
```

## For More Details

See [INTEGRATION_TEST_IMPLEMENTATION_SUMMARY.md](../INTEGRATION_TEST_IMPLEMENTATION_SUMMARY.md) for complete implementation details.

## Need Help?

1. Check [MORAL_COMPASS_INTEGRATION_TEST_README.md](./MORAL_COMPASS_INTEGRATION_TEST_README.md) troubleshooting section
2. Review API Lambda logs in CloudWatch
3. Verify API Gateway endpoint is accessible
4. Check DynamoDB table permissions
