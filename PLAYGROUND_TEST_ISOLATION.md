# Playground Test Isolation Project

## Overview

This project creates comprehensive unit tests to help isolate problems in the `test_playgrounds_nodataimport.py` test.

## What We Created

### 47 Unit Tests Across 6 Test Files
1. **test_setup_sanity.py** (10 tests) - Environment and import verification
2. **test_credentials.py** (5 tests) - Credential configuration
3. **test_playground_init.py** (9 tests) - ModelPlayground initialization
4. **test_data_preprocessing.py** (7 tests) - Data loading and preprocessing
5. **test_model_training.py** (7 tests) - Model training and prediction
6. **test_playground_operations.py** (9 tests) - Playground API operations (mocked)

### 2 GitHub Actions Workflows
1. **unit-tests.yml** - Runs all unit tests in parallel (6 jobs)
2. **playground-integration-tests.yml** - Step-by-step integration testing

### 3 Documentation Files
1. **tests/unit/README.md** - Detailed test documentation
2. **tests/unit/DEBUGGING_GUIDE.md** - Step-by-step debugging guide
3. **PLAYGROUND_TEST_ISOLATION.md** - Project overview (this file)

### 1 Test Runner Script
- **tests/unit/run_tests.sh** - Easy local test execution

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

## Quick Reference

### Test Files Location
```
tests/unit/
├── __init__.py
├── README.md                      # Detailed documentation
├── DEBUGGING_GUIDE.md             # Step-by-step debugging
├── run_tests.sh                   # Test runner script
├── test_setup_sanity.py           # Environment checks (10 tests)
├── test_credentials.py            # Credential tests (5 tests)
├── test_playground_init.py        # Initialization tests (9 tests)
├── test_data_preprocessing.py     # Data tests (7 tests)
├── test_model_training.py         # Model tests (7 tests)
└── test_playground_operations.py  # API tests (9 tests)
```

### GitHub Actions
- **Actions → Unit Tests** - Parallel execution of all unit tests
- **Actions → Playground Integration Tests** - Step-by-step integration testing

### Common Commands
```bash
# Run all unit tests
./tests/unit/run_tests.sh all

# Run specific component
./tests/unit/run_tests.sh credentials

# Run with pytest directly
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=aimodelshare --cov-report=html
```

### When test_playgrounds_nodataimport.py Fails
1. Run `./tests/unit/run_tests.sh sanity` to check environment
2. Run `./tests/unit/run_tests.sh all` to find failing component
3. Focus on the failing component's tests
4. Use GitHub Actions for detailed step-by-step logs
5. See `tests/unit/DEBUGGING_GUIDE.md` for detailed help

## Impact

These unit tests reduce debugging time from hours to minutes by:
- Isolating which component is failing
- Running faster than full integration tests
- Providing clear, focused error messages
- Enabling local debugging without AWS setup
- Serving as documentation for component behavior
