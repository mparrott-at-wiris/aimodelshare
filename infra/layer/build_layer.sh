#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

rm -rf python layer.zip
mkdir -p python

# Install deps to ./python so AWS Lambda recognizes it as a layer
pip install -r requirements.txt --target python

# Zip it
zip -r9 layer.zip python

echo "Built layer.zip at $(pwd)/layer.zip"