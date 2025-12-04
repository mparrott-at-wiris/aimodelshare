#!/bin/bash
#
# Moral Compass Integration Test Runner
#
# This script runs the comprehensive integration test for the Moral Compass API.
#
# Usage:
#   ./scripts/run_moral_compass_integration_test.sh [api_base_url] [jwt_token]
#
# Arguments:
#   api_base_url - (Optional) API base URL, defaults to env var MORAL_COMPASS_API_BASE_URL
#   jwt_token    - (Optional) JWT token, defaults to env var JWT_AUTHORIZATION_TOKEN
#
# Examples:
#   # Use environment variables
#   export MORAL_COMPASS_API_BASE_URL=https://api.example.com/prod
#   export JWT_AUTHORIZATION_TOKEN=eyJ...
#   ./scripts/run_moral_compass_integration_test.sh
#
#   # Pass as arguments
#   ./scripts/run_moral_compass_integration_test.sh https://api.example.com/prod eyJ...
#

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

print_info "Moral Compass Integration Test Runner"
echo ""

# Set API base URL
if [ -n "$1" ]; then
    export MORAL_COMPASS_API_BASE_URL="$1"
    print_info "Using API base URL from argument: $MORAL_COMPASS_API_BASE_URL"
elif [ -n "$MORAL_COMPASS_API_BASE_URL" ]; then
    print_info "Using API base URL from environment: $MORAL_COMPASS_API_BASE_URL"
else
    print_error "MORAL_COMPASS_API_BASE_URL is required"
    echo ""
    echo "Usage:"
    echo "  $0 <api_base_url> [jwt_token]"
    echo ""
    echo "Or set environment variables:"
    echo "  export MORAL_COMPASS_API_BASE_URL=https://api.example.com/prod"
    echo "  export JWT_AUTHORIZATION_TOKEN=eyJ..."
    echo "  $0"
    exit 1
fi

# Set JWT token if provided
if [ -n "$2" ]; then
    export JWT_AUTHORIZATION_TOKEN="$2"
    print_info "Using JWT token from argument"
elif [ -n "$JWT_AUTHORIZATION_TOKEN" ]; then
    print_info "Using JWT token from environment"
else
    print_warning "No JWT token provided - some tests may fail if auth is enabled"
fi

echo ""
print_info "Running integration test..."
echo ""

# Run the test
python tests/test_moral_compass_comprehensive_integration.py

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_success "Integration test completed successfully!"
else
    print_error "Integration test failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
