# Deprecation & Modernization Plan

## Completed (This PR)
- Removed `pkg_resources` in favor of `importlib.metadata`.
- Centralized optional dependency warnings with suppression support.
- Added PyJWT compatibility wrapper for forward upgrade.

## Q4 2025
- Upgrade PyJWT pin to `>=2.8,<3.0` after verification.

## H1 2026
- Audit for Pandas 3.x changes (removed APIs, changed defaults).
- Evaluate adopting structured logging (JSON) for lambda diagnostics.

## Continuous Compatibility (Proposed Nightly Workflow)
```yaml
name: Nightly Future Compatibility
on:
  schedule:
    - cron: "0 3 * * *"
jobs:
  future-compat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          pip install --pre pandas --pre scikit-learn --pre onnx --pre tensorflow
          pip install -e .
          PYTHONWARNINGS="default::DeprecationWarning" pytest -q
```

## Suppressing Optional Warnings
Set environment variable `AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS=1` in CI if noise reduction desired.

## Package Dependencies Timeline

### pkg_resources (COMPLETED)
- **Status**: Deprecated, scheduled for removal as early as Nov 30 2025
- **Action Taken**: Replaced with `importlib.metadata` in `aimodelshare/reproducibility.py`
- **Fallback**: Uses `importlib_metadata` backport for older Python versions

### PyJWT (IN PROGRESS)
- **Current State**: Pinned to `<2.0`
- **Target State**: Upgrade to `>=2.8,<3.0`
- **Action Taken**: Added compatibility wrapper `decode_token_unverified()` in `aimodelshare/modeluser.py`
- **Next Steps**: 
  - Test with PyJWT 2.x in isolated environment
  - Update pin in requirements once validated
  - Verify all JWT decode operations work correctly

### Optional Dependencies
- **Action Taken**: Created centralized warning system in `aimodelshare/utils/optional_deps.py`
- **Benefits**:
  - Single, consistent warning message format
  - Suppressible via `AIMODELSHARE_SUPPRESS_OPTIONAL_WARNINGS` environment variable
  - Uses Python's standard `warnings` module for better control
  - Reduces CI log noise

## Testing Recommendations

### Before PyJWT Upgrade
1. Run full test suite with PyJWT 1.x (current)
2. Run full test suite with PyJWT 2.8+
3. Verify JWT decode operations in:
   - `generatemodelapi.py`
   - Any authentication flows
4. Test with both verification enabled and disabled

### Continuous Integration
1. Add deprecation warning checks to CI
2. Set `PYTHONWARNINGS="default::DeprecationWarning"` in test runs
3. Monitor for new deprecation warnings from dependencies
4. Consider adding nightly builds with pre-release packages

## Migration Notes

### For Users
- No breaking changes in this PR
- Optional dependency warnings can be suppressed via environment variable
- All existing APIs remain unchanged

### For Developers
- Use `importlib.metadata` instead of `pkg_resources` for new code
- Use `decode_token_unverified()` wrapper for JWT operations
- Use `check_optional()` for new optional dependency checks
- TensorFlow INFO logs suppressed in CI via `TF_CPP_MIN_LOG_LEVEL=2`
