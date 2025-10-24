# Enhanced Preprocessor Diagnostics

## Overview

This document describes the enhanced diagnostics feature added to `submit_model` for debugging function-based preprocessor exports.

## Problem Statement

When users submit preprocessors as functions (rather than pre-exported zip files), the `export_preprocessor` function can fail if the preprocessor captures non-serializable closure variables (e.g., open file handles, database connections, thread locks). Previously, these failures resulted in generic error messages that didn't specify which variables caused the problem, making debugging difficult.

## Solution

We've added enhanced diagnostics that:

1. **Enumerate closure variables** using `inspect.getclosurevars()`
2. **Test individual serialization** of each closure variable
3. **Log detailed information** about successes and failures
4. **Raise structured exceptions** with the names of failed variables

## New Features

### 1. `debug_preprocessor` Parameter in `submit_model`

A new optional parameter has been added to the `submit_model` function:

```python
def submit_model(
    model_filepath=None,
    apiurl=None,
    prediction_submission=None,
    preprocessor=None,
    reproducibility_env_filepath=None,
    custom_metadata=None,
    submission_type="competition",
    input_dict=None,
    print_output=True,
    debug_preprocessor=False  # NEW PARAMETER
):
```

**Usage:**

```python
# Enable detailed diagnostics
submit_model(
    model_filepath="model.onnx",
    apiurl="https://...",
    preprocessor=my_preprocessor_function,
    debug_preprocessor=True  # Enable diagnostics
)
```

**Behavior:**

- **Default (False):** No additional diagnostic logging
- **Enabled (True):** Logs detailed information about closure variable serialization

### 2. `_diagnose_closure_variables` Function

A new diagnostic function that analyzes closure variables:

```python
def _diagnose_closure_variables(preprocessor_fxn):
    """
    Diagnose closure variables for serialization issues.
    
    Args:
        preprocessor_fxn: Function to diagnose
        
    Returns:
        tuple: (successful: list, failed: list of (name, type, error))
        
    Logs:
        INFO for successful serialization of each closure object
        WARNING for failed serialization attempts
    """
```

**Example Output:**

```
INFO: Analyzing 3 closure variables...
INFO: ✓ Closure variable 'scaler_mean' (type: float) is serializable
INFO: ✓ Closure variable 'scaler_std' (type: float) is serializable
WARNING: ✗ Closure variable 'file_handle' (type: TextIOWrapper) failed serialization: cannot pickle 'TextIOWrapper' instances
WARNING: Serialization failures detected: file_handle (TextIOWrapper)
```

### 3. Enhanced Error Messages in `export_preprocessor`

The `export_preprocessor` function now tracks serialization failures and raises detailed errors:

```python
RuntimeError: Preprocessor export encountered serialization failures for 1 closure variable(s): file_handle.

Details:
  - file_handle (type: TextIOWrapper): TypeError: cannot pickle 'TextIOWrapper' instances

These objects are referenced by your preprocessor function but cannot be serialized.
Common causes include open file handles, database connections, or thread locks.
```

## Common Non-Serializable Objects

The following types of objects commonly cause serialization failures:

1. **File handles** - `open()`, `TextIOWrapper`, `BufferedReader`
2. **Database connections** - SQLite connections, database cursors
3. **Thread synchronization** - `threading.Lock()`, `threading.Event()`
4. **Network sockets** - `socket.socket()`
5. **Generators** - Active generator objects
6. **Module objects** - Imported modules (though imports in the function itself work fine)

## Best Practices

### ✅ DO: Use serializable closure variables

```python
# Good: Simple types are serializable
scaler_mean = 0.5
scaler_std = 1.0
lookup_table = {"a": 1, "b": 2}

def preprocessor(x):
    normalized = (x - scaler_mean) / scaler_std
    return lookup_table.get(normalized, 0)
```

### ❌ DON'T: Capture non-serializable objects

```python
# Bad: File handle cannot be serialized
config_file = open("config.json", "r")

def preprocessor(x):
    config = json.load(config_file)  # Don't do this!
    return x * config['scale']
```

### ✅ DO: Load resources inside the function

```python
# Good: Load resources inside the function
def preprocessor(x):
    # Resources are loaded fresh each time
    with open("config.json", "r") as f:
        config = json.load(f)
    return x * config['scale']
```

## Testing

New tests have been added in `tests/unit/test_preprocessor_diagnostics.py`:

```bash
# Run diagnostics tests
pytest tests/unit/test_preprocessor_diagnostics.py -v

# Run all preprocessor tests
pytest tests/unit/test_preprocessor*.py -v
```

## Backward Compatibility

All changes are **fully backward compatible**:

- The `debug_preprocessor` parameter defaults to `False`
- Existing code continues to work without modification
- The return value of `submit_model` is unchanged
- Existing successful preprocessing pipelines are unaffected

## Technical Details

### Implementation Files

1. **aimodelshare/model.py**
   - Added `_diagnose_closure_variables()` helper function
   - Added `debug_preprocessor` parameter to `submit_model()`
   - Modified `_prepare_preprocessor_if_function()` to accept `debug_mode`

2. **aimodelshare/preprocessormodules.py**
   - Added `_test_object_serialization()` helper
   - Enhanced `export_preprocessor()` to track failed serializations
   - Improved error messages with variable names
   - Replaced deprecated `imp` module with `importlib.util`

### Dependencies

The enhanced diagnostics use only Python standard library modules:
- `inspect` - for analyzing closure variables
- `pickle` - for testing serialization
- `logging` - for diagnostic output

No new external dependencies are required.

## Example Usage

### Scenario 1: Debugging a failing preprocessor

```python
import logging
logging.basicConfig(level=logging.INFO)

# This will fail but show which variable is the problem
file_handle = open("data.txt", "r")

def my_preprocessor(x):
    data = file_handle.read()
    return x + len(data)

submit_model(
    preprocessor=my_preprocessor,
    debug_preprocessor=True,  # See diagnostics
    # ... other parameters
)
```

**Output:**
```
WARNING: ✗ Closure variable 'file_handle' (type: TextIOWrapper) failed serialization
RuntimeError: Preprocessor export encountered serialization failures for 1 closure variable(s): file_handle...
```

### Scenario 2: Verifying a preprocessor works

```python
scaler = MinMaxScaler()
scaler.fit(training_data)

def my_preprocessor(x):
    return scaler.transform(x)

submit_model(
    preprocessor=my_preprocessor,
    debug_preprocessor=True,  # Verify it works
    # ... other parameters
)
```

**Output:**
```
INFO: ✓ Closure variable 'scaler' (type: MinMaxScaler) is serializable
INFO: All 1 closure variables are serializable
```

## Future Enhancements

Potential future improvements:

1. Add suggestions for fixing common serialization issues
2. Automatic conversion of some non-serializable objects (e.g., file paths instead of handles)
3. Integration with CI/CD pipelines for pre-submission validation
4. Web UI display of diagnostic information

## References

- [Python pickle documentation](https://docs.python.org/3/library/pickle.html)
- [inspect module documentation](https://docs.python.org/3/library/inspect.html)
- Issue: Add enhanced diagnostics for function-based preprocessor exports
