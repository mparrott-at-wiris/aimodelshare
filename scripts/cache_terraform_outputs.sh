#!/usr/bin/env bash
# Cache Terraform outputs to JSON file and export API base URL to GitHub Actions environment.
# 
# Usage: ./cache_terraform_outputs.sh
#
# This script:
# 1. Runs `terraform output -json` in the infra directory
# 2. Saves the output to infra/terraform_outputs.json
# 3. Extracts api_base_url and exports it to $GITHUB_ENV (if running in GitHub Actions)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${REPO_ROOT}/infra"
OUTPUT_FILE="${INFRA_DIR}/terraform_outputs.json"

echo "📦 Caching Terraform outputs..."

# Check if infra directory exists
if [ ! -d "${INFRA_DIR}" ]; then
    echo "❌ Error: infra directory not found at ${INFRA_DIR}"
    exit 1
fi

# Check if terraform is available
if ! command -v terraform &> /dev/null; then
    echo "❌ Error: terraform command not found"
    exit 1
fi

# Change to infra directory and get outputs
cd "${INFRA_DIR}"

# Get all outputs as JSON
echo "Running: terraform output -json"
terraform output -json > "${OUTPUT_FILE}"

echo "✅ Terraform outputs cached to: ${OUTPUT_FILE}"

# Extract api_base_url
API_BASE_URL=$(terraform output -raw api_base_url 2>/dev/null || echo "")

if [ -z "${API_BASE_URL}" ] || [ "${API_BASE_URL}" = "null" ]; then
    echo "⚠️  Warning: api_base_url not found in Terraform outputs"
    exit 0
fi

echo "📍 API Base URL: ${API_BASE_URL}"

# Export to GitHub Actions environment if running in CI
if [ -n "${GITHUB_ENV:-}" ]; then
    echo "MORAL_COMPASS_API_BASE_URL=${API_BASE_URL}" >> "${GITHUB_ENV}"
    echo "✅ Exported MORAL_COMPASS_API_BASE_URL to GitHub Actions environment"
else
    echo "ℹ️  Not running in GitHub Actions, skipping environment export"
    echo "   To use locally, run: export MORAL_COMPASS_API_BASE_URL='${API_BASE_URL}'"
fi
