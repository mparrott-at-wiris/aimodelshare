#!/usr/bin/env bash
# Verify API is reachable by calling the health endpoint.
#
# Usage: ./verify_api_reachable.sh
#
# This script checks if the API is reachable by making a GET request to /health.
# It uses the MORAL_COMPASS_API_BASE_URL environment variable.

set -euo pipefail

API_BASE_URL="${MORAL_COMPASS_API_BASE_URL:-}"

if [ -z "${API_BASE_URL}" ]; then
    echo "❌ Error: MORAL_COMPASS_API_BASE_URL environment variable is not set"
    exit 1
fi

echo "🔍 Verifying API reachability..."
echo "📍 API Base URL: ${API_BASE_URL}"

HEALTH_URL="${API_BASE_URL}/health"
echo "🌐 Calling: ${HEALTH_URL}"

# Make request with timeout
if curl -f -s -S --max-time 10 "${HEALTH_URL}" > /dev/null 2>&1; then
    echo "✅ API is reachable and healthy"
    exit 0
else
    echo "❌ API is not reachable or returned an error"
    echo "   Attempting to get more details..."
    curl -v --max-time 10 "${HEALTH_URL}" || true
    exit 1
fi
