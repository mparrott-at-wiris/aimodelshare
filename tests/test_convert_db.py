"""
Test script for convert_db.py to verify dual cache file support.
Tests the following scenarios:
1. Both cache files present (merge with full_models precedence)
2. Only base cache present
3. Only full_models cache present
4. Neither cache present (should error)
5. SQLite structure remains backward compatible
"""

import os
import sys
import json
import gzip
import sqlite3
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import convert_db


def create_test_cache(filepath, data):
    """Create a gzipped JSON cache file for testing."""
    with gzip.open(filepath, "wt", encoding="UTF-8") as f:
        json.dump(data, f)


def verify_sqlite_structure(db_path):
    """Verify that the SQLite database has the expected structure."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache'")
    if not cursor.fetchone():
        conn.close()
        return False, "Table 'cache' not found"
    
    # Check columns
    cursor.execute("PRAGMA table_info(cache)")
    columns = cursor.fetchall()
    expected_columns = {"key", "value"}
    actual_columns = {col[1] for col in columns}
    
    if expected_columns != actual_columns:
        conn.close()
        return False, f"Column mismatch. Expected {expected_columns}, got {actual_columns}"
    
    # Check primary key
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cache'")
    create_sql = cursor.fetchone()[0]
    if "PRIMARY KEY" not in create_sql:
        conn.close()
        return False, "PRIMARY KEY not found in table definition"
    
    conn.close()
    return True, "Structure valid"


def test_both_caches_present():
    """Test when both cache files are present - full_models should take precedence."""
    print("\n" + "="*60)
    print("TEST 1: Both cache files present (merge with precedence)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save original directory
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create test data with overlapping keys
            base_data = {
                "key1": "base_value1",
                "key2": "base_value2",
                "key3": "base_value3",
            }
            
            full_models_data = {
                "key2": "full_models_value2",  # This should override base
                "key3": "full_models_value3",  # This should override base
                "key4": "full_models_value4",  # This is unique to full_models
            }
            
            # Create cache files
            create_test_cache("prediction_cache.json.gz", base_data)
            create_test_cache("prediction_cache_full_models.json.gz", full_models_data)
            
            # Run conversion
            convert_db.convert()
            
            # Verify SQLite structure
            valid, msg = verify_sqlite_structure("prediction_cache.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            # Verify data
            conn = sqlite3.connect("prediction_cache.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM cache ORDER BY key")
            results = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            # Expected result: full_models takes precedence on key2 and key3
            expected = {
                "key1": "base_value1",
                "key2": "full_models_value2",
                "key3": "full_models_value3",
                "key4": "full_models_value4",
            }
            
            if results != expected:
                print(f"❌ FAIL: Data mismatch")
                print(f"   Expected: {expected}")
                print(f"   Got: {results}")
                return False
            
            print("✅ PASS: Merge with precedence works correctly")
            return True
            
        finally:
            os.chdir(original_dir)


def test_only_base_cache():
    """Test when only base cache is present."""
    print("\n" + "="*60)
    print("TEST 2: Only base cache present")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            base_data = {
                "key1": "value1",
                "key2": "value2",
            }
            
            create_test_cache("prediction_cache.json.gz", base_data)
            
            # Run conversion
            convert_db.convert()
            
            # Verify SQLite structure
            valid, msg = verify_sqlite_structure("prediction_cache.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            # Verify data
            conn = sqlite3.connect("prediction_cache.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM cache ORDER BY key")
            results = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            if results != base_data:
                print(f"❌ FAIL: Data mismatch")
                print(f"   Expected: {base_data}")
                print(f"   Got: {results}")
                return False
            
            print("✅ PASS: Base cache only works correctly")
            return True
            
        finally:
            os.chdir(original_dir)


def test_only_full_models_cache():
    """Test when only full_models cache is present."""
    print("\n" + "="*60)
    print("TEST 3: Only full_models cache present")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            full_models_data = {
                "key1": "value1",
                "key2": "value2",
            }
            
            create_test_cache("prediction_cache_full_models.json.gz", full_models_data)
            
            # Run conversion
            convert_db.convert()
            
            # Verify SQLite structure
            valid, msg = verify_sqlite_structure("prediction_cache.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            # Verify data
            conn = sqlite3.connect("prediction_cache.sqlite")
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM cache ORDER BY key")
            results = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            
            if results != full_models_data:
                print(f"❌ FAIL: Data mismatch")
                print(f"   Expected: {full_models_data}")
                print(f"   Got: {results}")
                return False
            
            print("✅ PASS: Full models cache only works correctly")
            return True
            
        finally:
            os.chdir(original_dir)


def test_neither_cache_present():
    """Test when neither cache is present - should raise error."""
    print("\n" + "="*60)
    print("TEST 4: Neither cache present (should error)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Run conversion - should raise FileNotFoundError
            try:
                convert_db.convert()
                print("❌ FAIL: Should have raised FileNotFoundError")
                return False
            except FileNotFoundError as e:
                if "No cache files found" in str(e):
                    print("✅ PASS: Correctly raised FileNotFoundError")
                    return True
                else:
                    print(f"❌ FAIL: Wrong error message: {e}")
                    return False
            
        finally:
            os.chdir(original_dir)


def test_corrupt_cache_file():
    """Test when cache file exists but is corrupt/empty - should raise error."""
    print("\n" + "="*60)
    print("TEST 5: Corrupt/empty cache file (should error)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create a corrupt cache file (not valid gzip)
            with open("prediction_cache.json.gz", "w") as f:
                f.write("This is not valid gzip data")
            
            # Run conversion - should handle gracefully
            try:
                convert_db.convert()
                print("❌ FAIL: Should have raised ValueError for no valid data")
                return False
            except ValueError as e:
                if "No valid cache data" in str(e):
                    print("✅ PASS: Correctly raised ValueError for corrupt data")
                    return True
                else:
                    print(f"❌ FAIL: Wrong error message: {e}")
                    return False
            except Exception as e:
                print(f"❌ FAIL: Wrong exception type: {type(e).__name__}: {e}")
                return False
            
        finally:
            os.chdir(original_dir)


def test_backward_compatibility():
    """Test that existing consumers can still read the SQLite database."""
    print("\n" + "="*60)
    print("TEST 6: Backward compatibility check")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create a cache with realistic data format
            test_data = {
                "The Balanced Generalist|5|Small (20%)|age,c_charge_degree,race,sex": "0101001101",
                "The Rule-Maker|3|Medium (60%)|days_b_screening_arrest,priors_count,sex": "1010101010",
            }
            
            create_test_cache("prediction_cache.json.gz", test_data)
            
            # Run conversion
            convert_db.convert()
            
            # Verify structure
            valid, msg = verify_sqlite_structure("prediction_cache.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            # Simulate the existing consumer pattern (from verify_cache_integrity.py)
            conn = sqlite3.connect("prediction_cache.sqlite")
            cursor = conn.cursor()
            
            # Test lookup using the pattern from the app
            test_key = "The Balanced Generalist|5|Small (20%)|age,c_charge_degree,race,sex"
            cursor.execute("SELECT value FROM cache WHERE key=?", (test_key,))
            row = cursor.fetchone()
            
            if not row:
                print(f"❌ FAIL: Key not found in database")
                conn.close()
                return False
            
            raw_val = row[0]
            
            # Test that we can parse the value as before
            try:
                if isinstance(raw_val, str):
                    if raw_val.startswith("["):
                        predictions = json.loads(raw_val)
                    else:
                        predictions = [int(c) for c in raw_val]
                else:
                    predictions = raw_val
                
                if predictions != [0, 1, 0, 1, 0, 0, 1, 1, 0, 1]:
                    print(f"❌ FAIL: Prediction parsing incorrect: {predictions}")
                    conn.close()
                    return False
                
            except Exception as e:
                print(f"❌ FAIL: Parsing error: {e}")
                conn.close()
                return False
            
            conn.close()
            print("✅ PASS: Backward compatibility maintained")
            return True
            
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONVERT_DB.PY TEST SUITE")
    print("="*60)
    
    tests = [
        test_both_caches_present,
        test_only_base_cache,
        test_only_full_models_cache,
        test_neither_cache_present,
        test_corrupt_cache_file,
        test_backward_compatibility,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
