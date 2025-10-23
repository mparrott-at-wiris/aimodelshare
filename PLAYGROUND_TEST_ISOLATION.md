# Playground Test Isolation Project

## Overview

This project creates comprehensive unit tests to help isolate problems in the `test_playgrounds_nodataimport.py` test.

## Problem Statement

The `test_playgrounds_nodataimport.py` test is a comprehensive integration test that can fail at multiple points:
- Credential configuration
- Data loading from seaborn
- Data preprocessing
- Model training
- Playground creation
- Model submission
- Deployment

When this test fails, it's difficult to determine the root cause without extensive debugging.

## Solution

We've created:

### 1. Unit Test Suite (`tests/unit/`)
Five focused test modules that isolate each component:

- **test_credentials.py** - Tests credential configuration independently
- **test_playground_init.py** - Tests ModelPlayground initialization
- **test_data_preprocessing.py** - Tests data loading and preprocessing  
- **test_model_training.py** - Tests model training and prediction
- **test_playground_operations.py** - Tests playground API operations (mocked)

### 2. GitHub Actions Workflows

- **unit-tests.yml** - Runs all unit tests in parallel (~5-10 min)
- **playground-integration-tests.yml** - Tests each workflow step independently

## Usage

### Running Unit Tests Locally

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test module
pytest tests/unit/test_credentials.py -v

# Run with coverage
pytest tests/unit/ --cov=aimodelshare --cov-report=html
```

### Using GitHub Actions

1. **Automatic on PRs**: Unit tests run automatically on pull requests

2. **Manual Integration Tests**:
   - Go to GitHub Actions
   - Select "Playground Integration Tests (Isolated Steps)"
   - Choose which step to test (or 'all')
   - Review results to see exactly which step fails

## Debugging Workflow

When `test_playgrounds_nodataimport.py` fails:

1. **Run unit tests** to identify which component is failing
2. **Use integration workflow** to test specific steps in isolation
3. **Review logs** from the failing component
4. **Fix the specific issue** without needing to run the full integration test

## Benefits

- **Fast Feedback**: Unit tests run in minutes vs hours for full integration
- **Precise Isolation**: Identify exact component causing failures
- **No AWS Required**: Most tests use mocks, can run locally
- **Documentation**: Tests serve as examples of component usage
- **Regression Prevention**: Catch issues early

## File Structure

```
tests/
├── unit/
│   ├── __init__.py
│   ├── README.md                    # Detailed documentation
│   ├── test_credentials.py           # Credential tests
│   ├── test_playground_init.py       # Initialization tests
│   ├── test_data_preprocessing.py    # Data preprocessing tests
│   ├── test_model_training.py        # Model training tests
│   └── test_playground_operations.py # API operation tests (mocked)
└── test_playgrounds_nodataimport.py  # Original integration test

.github/workflows/
├── unit-tests.yml                    # Parallel unit test runner
└── playground-integration-tests.yml  # Step-by-step integration tests
```

## Key Features

### Mocking Strategy
- External API calls are mocked to avoid dependencies
- AWS services are mocked to allow local testing
- Real computation (sklearn, pandas) is tested without mocks

### Test Independence
- Each test cleans up after itself
- No shared state between tests
- Can run tests in any order

### Comprehensive Coverage
- Tests cover happy paths and error cases
- Includes validation of data shapes and types
- Tests error handling and edge cases

## Next Steps

1. Run unit tests to ensure they pass in CI
2. Use integration workflow to diagnose current test failures
3. Fix identified issues in smaller, isolated tests
4. Validate fixes with full integration test

## Maintenance

- Add new unit tests when adding features to ModelPlayground
- Update tests when APIs change
- Keep tests focused on single components
- Document any changes to test structure
