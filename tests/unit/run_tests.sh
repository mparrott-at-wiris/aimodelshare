#!/bin/bash
# Script to run unit tests for playground components
# This helps identify which component is failing in test_playgrounds_nodataimport.py

set -e

echo "======================================"
echo "Playground Component Unit Tests"
echo "======================================"
echo ""

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "Error: pytest is not installed"
    echo "Install with: pip install pytest"
    exit 1
fi

# Check if aimodelshare can be imported
if ! python -c "import aimodelshare" 2>/dev/null; then
    echo "Error: aimodelshare cannot be imported"
    echo "Install with: pip install -e ."
    exit 1
fi

echo "Running sanity checks..."
python -m pytest tests/unit/test_setup_sanity.py -v
echo ""

# Parse command line arguments
TEST_GROUP="${1:-all}"

if [ "$TEST_GROUP" == "all" ]; then
    echo "Running all unit tests..."
    python -m pytest tests/unit/ -v --tb=short
elif [ "$TEST_GROUP" == "credentials" ]; then
    echo "Running credential tests..."
    python -m pytest tests/unit/test_credentials.py -v --tb=short
elif [ "$TEST_GROUP" == "playground_init" ]; then
    echo "Running playground initialization tests..."
    python -m pytest tests/unit/test_playground_init.py -v --tb=short
elif [ "$TEST_GROUP" == "data_preprocessing" ]; then
    echo "Running data preprocessing tests..."
    python -m pytest tests/unit/test_data_preprocessing.py -v --tb=short
elif [ "$TEST_GROUP" == "model_training" ]; then
    echo "Running model training tests..."
    python -m pytest tests/unit/test_model_training.py -v --tb=short
elif [ "$TEST_GROUP" == "playground_operations" ]; then
    echo "Running playground operations tests..."
    python -m pytest tests/unit/test_playground_operations.py -v --tb=short
elif [ "$TEST_GROUP" == "sanity" ]; then
    echo "Running sanity checks only..."
    python -m pytest tests/unit/test_setup_sanity.py -v --tb=short
else
    echo "Unknown test group: $TEST_GROUP"
    echo ""
    echo "Usage: $0 [test_group]"
    echo ""
    echo "Available test groups:"
    echo "  all                  - Run all tests (default)"
    echo "  credentials          - Test credential configuration"
    echo "  playground_init      - Test ModelPlayground initialization"
    echo "  data_preprocessing   - Test data loading and preprocessing"
    echo "  model_training       - Test model training and prediction"
    echo "  playground_operations - Test playground API operations"
    echo "  sanity              - Run sanity checks only"
    echo ""
    exit 1
fi

echo ""
echo "======================================"
echo "Tests completed!"
echo "======================================"
