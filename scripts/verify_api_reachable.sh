#!/bin/bash
# verify_api_reachable.sh
#
# This script verifies that the API /health endpoint is reachable.
#
# Usage: ./scripts/verify_api_reachable.sh [API_BASE_URL]
#
# If API_BASE_URL is not provided as an argument, it will try to:
# 1. Use MORAL_COMPASS_API_BASE_URL environment variable
# 2. Use AIMODELSHARE_API_BASE_URL environment variable
# 3. Read from cached terraform outputs
# 4. Get from terraform command

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${REPO_ROOT}/infra"

# Determine API base URL
API_BASE_URL="${1:-}"

if [[ -z "$API_BASE_URL" ]]; then
    # Try environment variables
    API_BASE_URL="${MORAL_COMPASS_API_BASE_URL:-}"
fi

if [[ -z "$API_BASE_URL" ]]; then
    API_BASE_URL="${AIMODELSHARE_API_BASE_URL:-}"
fi

if [[ -z "$API_BASE_URL" ]]; then
    # Try cached terraform outputs
    OUTPUTS_FILE="${INFRA_DIR}/terraform_outputs.json"
    if [[ -f "$OUTPUTS_FILE" ]]; then
        API_BASE_URL=$(jq -r '.api_base_url.value // .api_base_url // empty' "$OUTPUTS_FILE" 2>/dev/null || echo "")
    fi
fi

if [[ -z "$API_BASE_URL" ]]; then
    # Try terraform command
    if [[ -d "$INFRA_DIR" ]]; then
        API_BASE_URL=$(cd "$INFRA_DIR" && terraform output -raw api_base_url 2>/dev/null || echo "")
    fi
fi

if [[ -z "$API_BASE_URL" || "$API_BASE_URL" == "null" ]]; then
    echo "❌ Could not determine API base URL"
    echo "Please provide it as an argument or set MORAL_COMPASS_API_BASE_URL environment variable"
    exit 1
fi

echo "🔍 Verifying API reachability at: ${API_BASE_URL}/health"

# Retry logic
MAX_ATTEMPTS=10
RETRY_DELAY=3

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "Attempt ${attempt}/${MAX_ATTEMPTS}..."
    
    if curl -f -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/health" | grep -q "200"; then
        echo "✅ API health endpoint is reachable!"
        
        # Show response
        echo ""
        echo "Health response:"
        curl -s "${API_BASE_URL}/health" | jq . || curl -s "${API_BASE_URL}/health"
        
        exit 0
    fi
    
    if [[ $attempt -lt $MAX_ATTEMPTS ]]; then
        echo "⏳ API not ready, waiting ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    fi
done

echo "❌ API health endpoint not reachable after ${MAX_ATTEMPTS} attempts"
exit 1
