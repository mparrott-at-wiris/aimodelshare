# Unit Tests for Playground Components

This directory contains unit tests designed to help isolate problems in the playground test suite, specifically `test_playgrounds_nodataimport.py`.

## Purpose

The `test_playgrounds_nodataimport.py` test is a comprehensive integration test that exercises many components:
- Credential configuration
- Data loading and preprocessing
- Model training
- Playground creation
- Model submission
- Deployment

When this test fails, it can be difficult to determine which component is causing the issue. These unit tests break down the test into smaller, focused tests that can be run independently.

## Test Structure

### 1. `test_credentials.py`
Tests credential configuration functionality:
- Manual credential input (mocked)
- Setting credentials from environment variables
- Reading credentials from file
- AWS token generation

**Key tests:**
- `test_manual_credential_input()` - Verifies credentials can be set via mocked getpass
- `test_set_credentials_from_environment()` - Verifies environment variable usage
- `test_credentials_file_not_found_handled()` - Verifies error handling

### 2. `test_playground_init.py`
Tests ModelPlayground class initialization:
- Initialization with required parameters
- Task type validation (classification vs regression)
- Input type handling
- Error handling for missing parameters

**Key tests:**
- `test_init_with_all_params()` - Verifies basic initialization
- `test_init_classification_task()` - Verifies classification setup
- `test_init_with_invalid_task_type()` - Verifies error handling

### 3. `test_data_preprocessing.py`
Tests data loading and preprocessing:
- Penguins dataset loading from seaborn
- Data cleaning (dropna)
- Train/test splitting
- StandardScaler preprocessing
- Preprocessor function creation

**Key tests:**
- `test_penguin_dataset_loading()` - Verifies seaborn dataset access
- `test_train_test_split_penguin_data()` - Verifies data splitting
- `test_preprocessor_creation()` - Verifies StandardScaler setup
- `test_preprocessor_function_wrapper()` - Verifies preprocessor function

### 4. `test_model_training.py`
Tests model training and prediction:
- LogisticRegression model creation
- Model training with various data
- Prediction generation
- Model with preprocessor integration

**Key tests:**
- `test_model_training_with_simple_data()` - Verifies basic training
- `test_penguin_model_training()` - Verifies training on penguins data
- `test_prediction_labels_generation()` - Verifies prediction output
- `test_model_with_preprocessor_function()` - Verifies full pipeline

### 5. `test_playground_operations.py`
Tests ModelPlayground API operations (mocked):
- Playground creation
- Model submission
- Leaderboard retrieval
- Model deployment
- Deployment deletion

**Key tests:**
- `test_playground_create()` - Verifies create API call
- `test_submit_model_mocked()` - Verifies model submission
- `test_get_leaderboard_mocked()` - Verifies leaderboard retrieval
- `test_deploy_model_mocked()` - Verifies deployment

## Running the Tests

### Using the test runner script (recommended):
```bash
# Run all tests
./tests/unit/run_tests.sh

# Run specific test group
./tests/unit/run_tests.sh credentials
./tests/unit/run_tests.sh playground_init
./tests/unit/run_tests.sh data_preprocessing
./tests/unit/run_tests.sh model_training
./tests/unit/run_tests.sh playground_operations
./tests/unit/run_tests.sh sanity
```

### Using pytest directly:

#### Run all unit tests:
```bash
pytest tests/unit/ -v
```

#### Run a specific test file:
```bash
pytest tests/unit/test_credentials.py -v
```

#### Run a specific test:
```bash
pytest tests/unit/test_credentials.py::TestCredentialConfiguration::test_manual_credential_input -v
```

#### Run with coverage:
```bash
pytest tests/unit/ --cov=aimodelshare --cov-report=html
```

## GitHub Actions Workflows

### 1. `unit-tests.yml`
Runs all unit tests in parallel across different test groups. This workflow:
- Runs on pull requests and manual triggers
- Tests each component independently
- Generates coverage reports
- Completes in ~5-10 minutes

**Usage:**
- Automatically runs on PRs
- Can be manually triggered via GitHub Actions UI

### 2. `playground-integration-tests.yml`
Runs integration tests for each step of the playground workflow in isolation. This workflow:
- Can be triggered manually with a choice of which step to test
- Tests: credentials, data_loading, preprocessing, model_training, playground_create
- Each step runs independently to isolate failures
- Completes in ~5-10 minutes per step

**Usage:**
```bash
# Manual trigger via GitHub Actions UI
# Select which step to test: all, credentials, data_loading, etc.
```

## Debugging Workflow

When `test_playgrounds_nodataimport.py` fails:

1. **Run unit tests first:**
   ```bash
   pytest tests/unit/ -v
   ```

2. **If a specific unit test fails, focus on that component:**
   - Credentials issue → Check `test_credentials.py`
   - Data loading issue → Check `test_data_preprocessing.py`
   - Model issue → Check `test_model_training.py`
   - Playground issue → Check `test_playground_operations.py`

3. **Use the integration workflow to test specific steps:**
   - Go to GitHub Actions
   - Select "Playground Integration Tests (Isolated Steps)"
   - Choose the specific step to test
   - Review detailed logs

4. **Common failure points:**
   - **Credentials**: Missing or invalid environment variables
   - **Data loading**: Network issues or seaborn dataset unavailable
   - **Preprocessing**: Sklearn version incompatibility
   - **Model training**: Data shape mismatches
   - **Playground API**: API endpoint changes or authentication issues

## Benefits

These unit tests provide:
1. **Fast feedback** - Run in minutes instead of hours
2. **Isolation** - Identify exact component causing failures
3. **Reproducibility** - Run locally without full AWS setup
4. **Documentation** - Tests serve as examples of how each component works
5. **Regression prevention** - Catch issues before they reach integration tests

## Maintenance

When updating the main playground test:
1. Update corresponding unit tests to match new behavior
2. Add new unit tests for new functionality
3. Keep tests focused and independent
4. Mock external dependencies (API calls, AWS services)

## Dependencies

Minimum requirements for unit tests:
```
pytest
pandas
numpy
scikit-learn
seaborn  # for data preprocessing tests
```

Full integration test requirements are in `requirements.txt`.
