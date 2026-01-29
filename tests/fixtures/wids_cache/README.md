# WiDS Cache Key Compatibility Test Suite

This test suite validates that WiDS cache artifacts are compatible with the Sustainability model-building app's expectations.

## Purpose

The Sustainability app uses a prediction cache to provide fast model predictions without retraining. The cache uses a specific key format:

```
model_name|complexity|data_size_label|comma_joined_features
```

Example:
```
The Balanced Generalist|2|Small (20%)|building_class,facility_type,floor_area,year_built
```

This test suite ensures:
1. All cache keys follow the expected format
2. The cache covers all model options available in the app
3. The cache covers all data size options
4. Default configurations are fully covered (critical for first-time users)
5. Feature sets are properly formatted (alphabetically sorted, comma-separated)

## Test Files

- **test_wids_cache_key_compatibility.py** - Main test module
- **fixtures/wids_cache/** - Test fixture directory containing sample cache files

## Fixtures

The test uses small representative fixture files that mimic the real cache format:

- `wids_prediction_cache.json.gz` - Base cache with ~8 sample entries
- `wids_prediction_cache_full_models.json.gz` - Full models cache with ~5 sample entries

### Updating Fixtures

If the cache key format changes or new models/options are added to the app:

1. Generate real cache data using `precompute_wids_cache.py`:
   ```bash
   python precompute_wids_cache.py
   ```

2. Either:
   - Copy a sample of entries to the fixture files, OR
   - Update the fixture creation script (see test file) to generate new fixtures

3. Ensure fixtures contain at least:
   - All default configurations
   - Examples of each model type
   - Examples of each data size option
   - Examples of different feature set combinations

## Running Tests

Run the full test suite:
```bash
pytest tests/test_wids_cache_key_compatibility.py -v
```

Run specific tests:
```bash
# Test key structure
pytest tests/test_wids_cache_key_compatibility.py::test_cache_key_structure -v

# Test model coverage
pytest tests/test_wids_cache_key_compatibility.py::test_model_coverage -v

# Test default configuration coverage
pytest tests/test_wids_cache_key_compatibility.py::test_default_configuration_coverage -v
```

Run with verbose output:
```bash
pytest tests/test_wids_cache_key_compatibility.py -v -s
```

## Test Coverage

The test suite includes:

1. **test_fixture_files_exist** - Validates fixture files are present and readable
2. **test_conversion_creates_databases** - Tests SQLite conversion logic
3. **test_cache_key_structure** - Validates all keys have 4 pipe-delimited segments
4. **test_cache_key_delimiter** - Ensures all keys use "|" delimiter
5. **test_model_coverage** - Checks all app models are in cache
6. **test_data_size_coverage** - Checks all app data sizes are in cache
7. **test_default_configuration_coverage** - Critical test for first-time user experience
8. **test_feature_set_format** - Validates feature names are sorted and comma-separated
9. **test_complexity_range** - Checks complexity values are in valid range (1-10)
10. **test_real_vs_fixture_indication** - Documents which data source is being used

## CI/CD Integration

These tests run in CI to catch cache compatibility issues before deployment. 

Key benefits:
- **Early detection** - Catch format mismatches before cache building
- **Coverage validation** - Ensure no app options are missing from cache
- **Regression prevention** - Detect breaking changes to cache format
- **Documentation** - Tests serve as living documentation of cache format

## Actionable Failure Messages

When tests fail, they provide specific guidance:

- **Missing models**: Lists which models need to be added to the cache
- **Missing data sizes**: Lists which data size options are missing
- **Invalid key format**: Shows the exact keys that don't match expected structure
- **Missing defaults**: Critical failures that prevent first-time users from submitting

Example failure message:
```
Cache is missing default configuration(s):
  - Default model 'The Balanced Generalist' not found in cache
  - Default data size 'Small (20%)' not found in cache
  
Default configuration must be fully covered to allow first-time users to submit.
```

## Maintenance

### When to Update Tests

Update tests when:
- New models are added to the app
- Data size options change
- Feature sets are modified
- Default configurations change
- Cache key format is updated

### How to Update Tests

1. Update fixtures with new sample data
2. Run tests to identify gaps
3. Fix cache generation or update test expectations
4. Verify all tests pass

## Related Files

- **convert_db_wids.py** - Converts gzipped JSON cache to SQLite
- **precompute_wids_cache.py** - Generates the full cache artifacts
- **aimodelshare/moral_compass/apps/sustainability/model_building_app_en_sustainability.py** - App that consumes the cache

## Notes

- Tests use regex parsing to extract app constants without importing the full app module (avoids Gradio initialization)
- Fixture files are small (~300 bytes each) to keep the test suite lightweight
- Tests run quickly (<1 second) for fast feedback in CI
- SQLite conversion happens in temporary directories to avoid side effects
