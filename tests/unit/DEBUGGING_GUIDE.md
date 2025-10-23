# How to Use Unit Tests to Debug test_playgrounds_nodataimport.py

## Quick Start

When `test_playgrounds_nodataimport.py` fails in CI, follow these steps:

### Step 1: Run Sanity Tests
```bash
./tests/unit/run_tests.sh sanity
```
This verifies your environment is set up correctly.

### Step 2: Run All Unit Tests Locally
```bash
./tests/unit/run_tests.sh all
```
This runs all component tests to identify which component is failing.

### Step 3: Focus on Failing Component
If a specific component test fails, run just that test:
```bash
./tests/unit/run_tests.sh credentials        # If credentials are the issue
./tests/unit/run_tests.sh data_preprocessing # If data loading is the issue
./tests/unit/run_tests.sh model_training     # If model training is the issue
# etc.
```

### Step 4: Use GitHub Actions for Detailed Logs
If you can't reproduce locally, use the GitHub Actions workflows:

1. Go to your repository's Actions tab
2. Select "Playground Integration Tests (Isolated Steps)"
3. Click "Run workflow"
4. Choose the specific step to test
5. Review the detailed logs

## Common Failure Scenarios

### Scenario 1: Credentials Test Fails

**Symptoms:**
- `test_credentials.py` tests fail
- Error about missing environment variables
- Authentication errors

**Diagnosis:**
```bash
./tests/unit/run_tests.sh credentials
```

**Common Causes:**
- Missing `USERNAME`, `PASSWORD`, `AWS_ACCESS_KEY_ID`, or other env vars
- Invalid credentials format
- Expired AWS credentials

**Solutions:**
- Check GitHub Secrets are set correctly
- Verify credentials file format matches expected pattern
- Update AWS credentials if expired

### Scenario 2: Data Loading Fails

**Symptoms:**
- `test_data_preprocessing.py` tests fail
- Error loading penguins dataset
- Network timeout errors

**Diagnosis:**
```bash
./tests/unit/run_tests.sh data_preprocessing
```

**Common Causes:**
- Seaborn package not installed
- Network issues accessing seaborn datasets
- Pandas version incompatibility

**Solutions:**
- Install seaborn: `pip install seaborn`
- Check network connectivity
- Update pandas: `pip install --upgrade pandas`

### Scenario 3: Model Training Fails

**Symptoms:**
- `test_model_training.py` tests fail
- sklearn errors
- Shape mismatch errors

**Diagnosis:**
```bash
./tests/unit/run_tests.sh model_training
```

**Common Causes:**
- sklearn version incompatibility
- Data preprocessing issues
- Memory issues

**Solutions:**
- Check sklearn version: `pip install scikit-learn==1.2.1`
- Verify data shapes are correct
- Check available memory

### Scenario 4: Playground Operations Fail

**Symptoms:**
- `test_playground_operations.py` tests fail
- API call errors
- Timeout errors

**Diagnosis:**
```bash
./tests/unit/run_tests.sh playground_operations
```

**Common Causes:**
- API endpoint changes
- Network connectivity issues
- Authentication token problems

**Solutions:**
- Check API endpoints are correct
- Verify AWS_TOKEN is set
- Check network connectivity

## Using the Integration Workflow

The `playground-integration-tests.yml` workflow provides step-by-step testing:

### Available Steps:
- `credentials` - Tests credential configuration
- `data_loading` - Tests loading penguins dataset
- `preprocessing` - Tests data preprocessing
- `model_training` - Tests model training
- `playground_create` - Tests ModelPlayground initialization

### How to Use:
1. Go to GitHub Actions
2. Select "Playground Integration Tests (Isolated Steps)"
3. Click "Run workflow"
4. Select step to test (or 'all' for complete test)
5. Wait for results
6. Review logs for the specific step

### Reading the Results:

Each step will show:
- ✅ Success: Component is working correctly
- ❌ Failure: Component has an issue

The logs will show exactly what failed in that step.

## Example Debugging Session

Let's say `test_playgrounds_nodataimport.py` fails in CI with this error:
```
ModuleNotFoundError: No module named 'seaborn'
```

### Debug Process:

1. **Run sanity test**:
   ```bash
   ./tests/unit/run_tests.sh sanity
   ```
   Result: `test_seaborn_available` fails - seaborn not installed

2. **Install seaborn**:
   ```bash
   pip install seaborn
   ```

3. **Run data preprocessing tests**:
   ```bash
   ./tests/unit/run_tests.sh data_preprocessing
   ```
   Result: All tests pass ✅

4. **Run full unit test suite**:
   ```bash
   ./tests/unit/run_tests.sh all
   ```
   Result: All tests pass ✅

5. **Fix CI**: Update requirements or workflow to include seaborn

6. **Verify**: Re-run `test_playgrounds_nodataimport.py`

## Advanced Usage

### Running with Verbose Output
```bash
pytest tests/unit/ -vv --tb=long
```

### Running with Coverage
```bash
pytest tests/unit/ --cov=aimodelshare --cov-report=html
open htmlcov/index.html
```

### Running Specific Test
```bash
pytest tests/unit/test_credentials.py::TestCredentialConfiguration::test_manual_credential_input -vv
```

### Running with Markers (if added)
```bash
pytest tests/unit/ -m "not slow"
```

## Continuous Integration

The unit tests are automatically run on:
- Every pull request
- Every push to master
- Manual trigger via GitHub Actions

You can view results in the Actions tab of your repository.

## Tips for Success

1. **Start with sanity tests** - Always run these first to verify environment
2. **Use the test runner script** - It provides better error messages
3. **Test one component at a time** - Isolate the problem
4. **Check the logs** - Both local and CI logs provide valuable info
5. **Update tests when code changes** - Keep tests in sync with implementation

## Getting Help

If tests fail and you can't determine why:

1. Check the test logs for detailed error messages
2. Review the test code to understand what's being tested
3. Look at the original `test_playgrounds_nodataimport.py` to see how it uses the component
4. Create a minimal reproduction case
5. Open an issue with:
   - Error message
   - Test output
   - Environment details (Python version, package versions)

## Maintenance

When updating the playground functionality:

1. Update corresponding unit tests
2. Run unit tests locally before committing
3. Check CI results after pushing
4. Update documentation if test behavior changes
