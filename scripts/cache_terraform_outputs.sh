#!/bin/bash
# cache_terraform_outputs.sh
# 
# This script exports MORAL_COMPASS_API_BASE_URL environment variable
# and writes terraform outputs to infra/terraform_outputs.json for caching.
#
# Usage: ./scripts/cache_terraform_outputs.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${REPO_ROOT}/infra"
OUTPUTS_FILE="${INFRA_DIR}/terraform_outputs.json"

echo "🔧 Caching Terraform outputs..."

# Change to infra directory
cd "${INFRA_DIR}"

# Get terraform outputs as JSON
if ! terraform output -json > "${OUTPUTS_FILE}"; then
    echo "❌ Failed to get terraform outputs"
    exit 1
fi

echo "✅ Terraform outputs cached to: ${OUTPUTS_FILE}"

# Extract API base URL
API_BASE_URL=$(terraform output -raw api_base_url 2>/dev/null || echo "")

if [[ -z "$API_BASE_URL" || "$API_BASE_URL" == "null" ]]; then
    echo "⚠️  Warning: Could not extract API base URL from terraform outputs"
    exit 1
fi

echo "📍 API Base URL: ${API_BASE_URL}"

# Export to environment (for current shell and CI)
export MORAL_COMPASS_API_BASE_URL="${API_BASE_URL}"
echo "MORAL_COMPASS_API_BASE_URL=${API_BASE_URL}" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true

# Also write to a file that can be sourced
echo "export MORAL_COMPASS_API_BASE_URL=\"${API_BASE_URL}\"" > "${INFRA_DIR}/.env_api"

echo "✅ Environment variable MORAL_COMPASS_API_BASE_URL exported"
echo ""
echo "To use in your shell, run:"
echo "  source ${INFRA_DIR}/.env_api"
