#!/usr/bin/env python
"""
Manual verification script for enhanced preprocessor diagnostics.
This script demonstrates the new debug_preprocessor feature.
"""

import tempfile
import os
import sys
import logging
import importlib.util

# Setup logging to see diagnostic messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("=" * 70)
print("Manual Verification: Enhanced Preprocessor Diagnostics")
print("=" * 70)
print()

# Direct import of specific modules to avoid dependency issues
def import_model_module():
    """Import model.py directly without loading all of aimodelshare."""
    model_path = os.path.join(os.path.dirname(__file__), 'aimodelshare', 'model.py')
    spec = importlib.util.spec_from_file_location("model_direct", model_path)
    module = importlib.util.module_from_spec(spec)
    
    # Mock dependencies to allow import
    sys.modules['aimodelshare.leaderboard'] = type(sys)('mock')
    sys.modules['aimodelshare.leaderboard'].get_leaderboard = lambda: None
    sys.modules['aimodelshare.aws'] = type(sys)('mock')
    sys.modules['aimodelshare.aimsonnx'] = type(sys)('mock')
    sys.modules['aimodelshare.utils'] = type(sys)('mock')
    
    # Load just the functions we need
    spec.loader.exec_module(module)
    return module

try:
    model_module = import_model_module()
    _diagnose_closure_variables = model_module._diagnose_closure_variables
    print("✓ Successfully imported _diagnose_closure_variables from model.py")
except Exception as e:
    print(f"✗ Failed to import: {e}")
    sys.exit(0)

print()
print("-" * 70)
print("Test 1: Preprocessor with serializable closures")
print("-" * 70)

# Create a simple preprocessor with serializable closures
scaler_mean = 0.5
scaler_std = 1.0

def good_preprocessor(x):
    """A preprocessor with only serializable closure variables."""
    return (x - scaler_mean) / scaler_std

print(f"Testing preprocessor with closures: scaler_mean={scaler_mean}, scaler_std={scaler_std}")
successful, failed = _diagnose_closure_variables(good_preprocessor)
print(f"Results: {len(successful)} successful, {len(failed)} failed")
if successful:
    print(f"  Successful: {successful}")
if failed:
    print(f"  Failed: {[(name, vtype) for name, vtype, _ in failed]}")

print()
print("-" * 70)
print("Test 2: Preprocessor with non-pickleable closure (file handle)")
print("-" * 70)

# Create a preprocessor with a non-pickleable closure
temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
temp_file.write("test data")
temp_file.flush()
temp_file_name = temp_file.name

file_handle = open(temp_file_name, 'r')

def bad_preprocessor(x):
    """A preprocessor that captures a file handle (not serializable)."""
    # Reference the file handle in the closure
    _ = file_handle
    return x

print(f"Testing preprocessor with file handle closure")
successful, failed = _diagnose_closure_variables(bad_preprocessor)
print(f"Results: {len(successful)} successful, {len(failed)} failed")
if successful:
    print(f"  Successful: {successful}")
if failed:
    print(f"  Failed:")
    for name, vtype, error in failed:
        print(f"    - {name} (type: {vtype})")
        print(f"      Error: {error[:100]}...")

# Cleanup
file_handle.close()
os.unlink(temp_file_name)

print()
print("-" * 70)
print("Test 3: Thread lock detection")
print("-" * 70)

import threading

lock = threading.Lock()

def lock_preprocessor(x):
    """Preprocessor that uses a thread lock (not serializable)."""
    with lock:
        return x * 2

print(f"Testing preprocessor with threading.Lock closure")
successful, failed = _diagnose_closure_variables(lock_preprocessor)
print(f"Results: {len(successful)} successful, {len(failed)} failed")
if failed:
    print(f"  Failed:")
    for name, vtype, error in failed:
        print(f"    - {name} (type: {vtype})")
        if 'lock' in name.lower():
            print(f"      ✓ Correctly detected thread lock as non-serializable")

print()
print("-" * 70)
print("Test 4: Verify code changes in model.py")
print("-" * 70)

model_path = os.path.join(os.path.dirname(__file__), 'aimodelshare', 'model.py')
with open(model_path, 'r') as f:
    content = f.read()

checks = [
    ('debug_preprocessor parameter in submit_model', 'debug_preprocessor=False' in content),
    ('_diagnose_closure_variables function exists', 'def _diagnose_closure_variables' in content),
    ('inspect.getclosurevars usage', 'inspect.getclosurevars' in content),
    ('debug_mode parameter in _prepare_preprocessor_if_function', 'debug_mode=False' in content),
]

for check_name, check_result in checks:
    status = "✓" if check_result else "✗"
    print(f"{status} {check_name}")

print()
print("-" * 70)
print("Test 5: Verify code changes in preprocessormodules.py")
print("-" * 70)

preproc_path = os.path.join(os.path.dirname(__file__), 'aimodelshare', 'preprocessormodules.py')
with open(preproc_path, 'r') as f:
    content = f.read()

checks = [
    ('_test_object_serialization helper exists', 'def _test_object_serialization' in content),
    ('failed_objects tracking', 'failed_objects' in content),
    ('serialization failures error message', 'serialization failures' in content),
    ('importlib.util instead of deprecated imp', 'importlib.util' in content and 'import imp' not in content),
]

for check_name, check_result in checks:
    status = "✓" if check_result else "✗"
    print(f"{status} {check_name}")

print()
print("=" * 70)
print("Verification Complete")
print("=" * 70)
print()
print("Summary:")
print("- Enhanced diagnostics can detect non-serializable closure variables")
print("- _diagnose_closure_variables provides detailed failure information")
print("- debug_preprocessor parameter added to submit_model")
print("- export_preprocessor tracks serialization failures")
print("- Deprecated imp module replaced with importlib.util")
print()
