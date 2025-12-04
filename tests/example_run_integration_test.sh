#!/bin/bash
#
# Example: How to run the Moral Compass Integration Test
#
# This script demonstrates how to set up and run the integration test
# with appropriate environment variables.
#

# Example 1: Basic usage with environment variables
echo "Example 1: Using environment variables"
echo "========================================"
export MORAL_COMPASS_API_BASE_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/prod"
export JWT_AUTHORIZATION_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-token-here"

# Run the test directly
# python tests/test_moral_compass_comprehensive_integration.py

echo ""
echo "Example 2: Using the runner script"
echo "===================================="
# ./scripts/run_moral_compass_integration_test.sh

echo ""
echo "Example 3: With custom table ID"
echo "================================"
export TEST_TABLE_ID="my-custom-test-table-mc"
# python tests/test_moral_compass_comprehensive_integration.py

echo ""
echo "Example 4: Using pytest"
echo "======================="
# pytest tests/test_moral_compass_comprehensive_integration.py -v -s

echo ""
echo "Example 5: Quick test without auth"
echo "==================================="
unset JWT_AUTHORIZATION_TOKEN
# python tests/test_moral_compass_comprehensive_integration.py

echo ""
echo "NOTE: Uncomment the command lines above to actually run the tests"
echo "      Make sure to replace the API URL and JWT token with real values"
