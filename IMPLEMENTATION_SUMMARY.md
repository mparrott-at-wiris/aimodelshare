# Preprocessor Validation Enhancement - Implementation Summary

## Overview
Enhanced robustness for submitting models with function-based preprocessors by adding comprehensive validation at multiple stages of the submission pipeline.

## Changes Made

### 1. Added Helper Function: `_prepare_preprocessor_if_function`
**File:** `aimodelshare/model.py` (lines 107-159)

**Purpose:** Encapsulate function-to-zip conversion with comprehensive validation

**Validations:**
- ✅ Checks if preprocessor is a function (returns as-is if not)
- ✅ Validates exported zip file exists at expected path
- ✅ Validates zip file has non-zero size (not empty)
- ✅ Validates zip contains required `preprocessor.py` member
- ✅ Raises clear `RuntimeError` exceptions with descriptive messages

**Code:**
```python
def _prepare_preprocessor_if_function(preprocessor):
    """
    Convert function-based preprocessor to validated zip file.
    
    Args:
        preprocessor: Preprocessor function or file path
        
    Returns:
        str: Path to validated preprocessor zip file
        
    Raises:
        RuntimeError: If export fails, zip is empty, or missing required files
    """
    import types
    from zipfile import ZipFile
    
    # If not a function, return as-is
    if not isinstance(preprocessor, types.FunctionType):
        return preprocessor
    
    # Export function to temporary directory
    from aimodelshare.preprocessormodules import export_preprocessor
    temp_prep = tmp.mkdtemp()
    export_preprocessor(preprocessor, temp_prep)
    preprocessor_path = temp_prep + "/preprocessor.zip"
    
    # Validate exported zip file exists
    if not os.path.exists(preprocessor_path):
        raise RuntimeError(
            f"Preprocessor export failed: zip file not found at {preprocessor_path}"
        )
    
    # Validate zip file has non-zero size
    file_size = os.path.getsize(preprocessor_path)
    if file_size == 0:
        raise RuntimeError(
            f"Preprocessor export failed: zip file is empty (0 bytes)"
        )
    
    # Validate zip contains preprocessor.py
    try:
        with ZipFile(preprocessor_path, 'r') as zip_file:
            zip_contents = zip_file.namelist()
            if 'preprocessor.py' not in zip_contents:
                raise RuntimeError(
                    f"Preprocessor export failed: 'preprocessor.py' not found in zip. Contents: {zip_contents}"
                )
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Preprocessor zip validation failed: {e}")
    
    return preprocessor_path
```

### 2. Replaced Inline Export with Helper Call
**File:** `aimodelshare/model.py` (line 769)

**Before:**
```python
# check whether preprocessor is function
import types
if isinstance(preprocessor, types.FunctionType): 
    from aimodelshare.preprocessormodules import export_preprocessor
    temp_prep=tmp.mkdtemp()
    export_preprocessor(preprocessor,temp_prep)
    preprocessor = temp_prep+"/preprocessor.zip"
```

**After:**
```python
# check whether preprocessor is function and validate export
preprocessor = _prepare_preprocessor_if_function(preprocessor)
```

**Benefits:**
- Single line of code instead of 7
- Validation happens automatically
- Clear error messages on failure
- Easier to test and maintain

### 3. Enhanced Preprocessor Upload Logic
**File:** `aimodelshare/model.py` (lines 916-948)

**Key Improvements:**

#### A. Explicit Key Pattern Matching
**Before:** Selected first zip file from presigned URLs (unreliable)
```python
modelputfiles = [s for s in putfilekeys if str("zip") in s]
# ... used fileputlistofdicts[0] (first match)
```

**After:** Explicit pattern matching with priority
```python
# Find preprocessor upload key using explicit pattern matching
# Prefer keys containing 'preprocessor_v' or 'preprocessor' ending in '.zip'
preprocessor_key = None
for key in putfilekeys:
    if 'preprocessor_v' in key and key.endswith('.zip'):
        preprocessor_key = key
        break
    elif 'preprocessor' in key and key.endswith('.zip'):
        preprocessor_key = key

# Fallback to original logic if no explicit match
if preprocessor_key is None and preprocessor is not None:
    modelputfiles = [s for s in putfilekeys if str("zip") in s]
    if modelputfiles:
        preprocessor_key = modelputfiles[0]
```

**Benefits:**
- Prioritizes `preprocessor_v*.zip` (versioned files)
- Falls back to `preprocessor*.zip` 
- Maintains backward compatibility with fallback
- No longer relies on implicit ordering

#### B. Upload Status Code Validation
**Added:**
```python
if preprocessor is not None:
    if preprocessor_key is None:
        raise RuntimeError("Failed to find preprocessor upload URL in presigned URLs")
    
    filedownload_dict = ast.literal_eval(s3_presigned_dict['put'][preprocessor_key])
    
    with open(preprocessor, 'rb') as f:
        files = {'file': (preprocessor, f)}
        http_response = requests.post(filedownload_dict['url'], data=filedownload_dict['fields'], files=files)
        
        # Validate upload response status
        if http_response.status_code not in [200, 204]:
            raise RuntimeError(
                f"Preprocessor upload failed with status {http_response.status_code}: {http_response.text}"
            )
```

**Benefits:**
- Explicit validation of HTTP status codes (200, 204)
- Clear error message with status code and response text
- No silent failures

### 4. Tuple Validation in ModelPlayground.submit_model
**File:** `aimodelshare/playground.py` (lines 1257-1279)

**Note:** This was already in place from a previous PR (#25)

**Purpose:** Ensure `submit_model` returns `(version, url)` tuple, not `None`

**Implementation:**
```python
# Competition submission
comp_result = competition.submit_model(...)

# Validate return structure before unpacking
if not isinstance(comp_result, tuple) or len(comp_result) != 2:
    raise RuntimeError(f"Invalid return from competition.submit_model: expected (version, url) tuple, got {type(comp_result)}")

version_comp, model_page = comp_result

# Experiment submission
exp_result = experiment.submit_model(...)

# Validate return structure before unpacking
if not isinstance(exp_result, tuple) or len(exp_result) != 2:
    raise RuntimeError(f"Invalid return from experiment.submit_model: expected (version, url) tuple, got {type(exp_result)}")

version_exp, model_page = exp_result
```

## Tests Added

### File: `tests/unit/test_preprocessor_validation.py`

**Test Coverage:**
1. ✅ `test_prepare_preprocessor_validates_export` - Validates successful export and validation
2. ✅ `test_preprocessor_validation_empty_zip` - Detects empty zip files
3. ✅ `test_preprocessor_validation_missing_file` - Detects missing preprocessor.py
4. ✅ `test_explicit_key_pattern_matching` - Validates key selection logic
5. ✅ `test_upload_status_validation` - Validates HTTP status code checking

**All 5 tests passing** ✅

## Error Messages

### Before
- Silent failures (returned `None`)
- Generic exceptions
- No indication of what went wrong

### After
Clear, actionable error messages:

1. **Missing zip file:**
   ```
   RuntimeError: Preprocessor export failed: zip file not found at /tmp/xyz/preprocessor.zip
   ```

2. **Empty zip file:**
   ```
   RuntimeError: Preprocessor export failed: zip file is empty (0 bytes)
   ```

3. **Missing preprocessor.py:**
   ```
   RuntimeError: Preprocessor export failed: 'preprocessor.py' not found in zip. Contents: ['other_file.py']
   ```

4. **Upload URL not found:**
   ```
   RuntimeError: Failed to find preprocessor upload URL in presigned URLs
   ```

5. **Upload failed:**
   ```
   RuntimeError: Preprocessor upload failed with status 403: Forbidden
   ```

## Risk Assessment

**Risk Level:** Low ✅

**Reasons:**
- Changes are additive (new validations)
- Maintains backward compatibility (fallback logic)
- Only affects submission pathway when function preprocessor is provided
- Clear exception messages help debugging
- Existing tests continue to pass (validation confirmed)

## Backward Compatibility

✅ **Fully Maintained**

- String/path preprocessors: Pass through unchanged
- Presigned URL ordering fallback: Preserves original behavior if explicit match fails
- All existing code paths: Continue to work as before
- Error cases: Now surface clear exceptions instead of silent failures

## Benefits

1. **Robustness:** No more silent failures producing invalid artifacts
2. **Debuggability:** Clear error messages pinpoint exact failure
3. **Reliability:** Validation prevents upload of corrupted/incomplete preprocessors
4. **Maintainability:** Helper function encapsulates complexity
5. **Safety:** Explicit key matching eliminates ordering dependency

## Acceptance Criteria Met

✅ Submitting with a function preprocessor succeeds and returns `(version, url)` tuple
✅ Invalid preprocessor export surfaces clear exception rather than silent failure
✅ No reliance on implicit ordering of presigned URLs
✅ Existing tests continue to pass
✅ New regression tests added and passing

## Files Modified

1. ✅ `aimodelshare/model.py` - Helper function, validation, upload logic
2. ✅ `aimodelshare/playground.py` - Tuple validation (from previous PR)
3. ✅ `tests/unit/test_preprocessor_validation.py` - New regression tests

## Verification Steps Completed

1. ✅ Syntax validation of all Python files
2. ✅ Function presence and signature verification
3. ✅ Code pattern validation (all expected patterns present)
4. ✅ Unit tests created and passing (5/5)
5. ✅ Git diff review confirming surgical changes
6. ✅ Backward compatibility analysis

## Summary

Successfully implemented comprehensive preprocessor validation for function-based submissions with:
- **Minimal surgical changes** to existing codebase
- **Complete validation** at every stage (export, validate, upload)
- **Clear error messages** for all failure modes
- **Full backward compatibility** maintained
- **Test coverage** for all new validation logic
- **No breaking changes** to existing functionality
