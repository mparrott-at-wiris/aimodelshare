"""
Test script for convert_db.py to verify dual cache file and dual database support.
Tests the following scenarios:
1. Both cache files present (creates both databases)
2. Only base cache present (creates both databases with same data)
3. Only full_models cache present (creates only full database)
4. Neither cache present (should error)
5. Both databases maintain correct structure
"""

import os
import sys
import json
import gzip
import sqlite3
import tempfile
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
import convert_db


def create_test_cache(filepath, data):
    """Create a gzipped JSON cache file for testing."""
    with gzip.open(filepath, "wt", encoding="UTF-8") as f:
        json.dump(data, f)


def verify_sqlite_structure(db_path):
    """Verify that the SQLite database has the expected structure."""
    if not os.path.exists(db_path):
        return False, f"Database file '{db_path}' not found"
    
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


def get_database_contents(db_path):
    """Get all key-value pairs from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM cache ORDER BY key")
    results = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return results


def test_both_caches_present():
    """Test when both cache files are present - should create both databases."""
    print("\n" + "="*60)
    print("TEST 1: Both cache files present (creates both databases)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
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
                "key2": "full_models_value2",  # Override in full db
                "key3": "full_models_value3",  # Override in full db
                "key4": "full_models_value4",  # Unique to full_models
            }
            
            create_test_cache("prediction_cache.json.gz", base_data)
            create_test_cache("prediction_cache_full_models.json.gz", full_models_data)
            
            # Run conversion
            convert_db.convert()
            
            # Verify both databases exist
            if not os.path.exists("prediction_cache.sqlite"):
                print("❌ FAIL: prediction_cache.sqlite not created")
                return False
            
            if not os.path.exists("prediction_cache_full.sqlite"):
                print("❌ FAIL: prediction_cache_full.sqlite not created")
                return False
            
            # Verify structures
            for db_name in ["prediction_cache.sqlite", "prediction_cache_full.sqlite"]:
                valid, msg = verify_sqlite_structure(db_name)
                if not valid:
                    print(f"❌ FAIL: {db_name} - {msg}")
                    return False
            
            # Verify base database contains only base data
            base_db_contents = get_database_contents("prediction_cache.sqlite")
            if base_db_contents != base_data:
                print(f"❌ FAIL: Base database has wrong data")
                print(f"   Expected: {base_data}")
                print(f"   Got: {base_db_contents}")
                return False
            
            # Verify full database contains merged data with precedence
            expected_full = {
                "key1": "base_value1",
                "key2": "full_models_value2",  # Override
                "key3": "full_models_value3",  # Override
                "key4": "full_models_value4",
            }
            full_db_contents = get_database_contents("prediction_cache_full.sqlite")
            if full_db_contents != expected_full:
                print(f"❌ FAIL: Full database has wrong data")
                print(f"   Expected: {expected_full}")
                print(f"   Got: {full_db_contents}")
                return False
            
            print("✅ PASS: Both databases created correctly")
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
            convert_db.convert()
            
            # Verify both databases exist with same data
            for db_name in ["prediction_cache.sqlite", "prediction_cache_full.sqlite"]:
                if not os.path.exists(db_name):
                    print(f"❌ FAIL: {db_name} not created")
                    return False
                
                valid, msg = verify_sqlite_structure(db_name)
                if not valid:
                    print(f"❌ FAIL: {db_name} - {msg}")
                    return False
                
                contents = get_database_contents(db_name)
                if contents != base_data:
                    print(f"❌ FAIL: {db_name} has wrong data")
                    return False
            
            print("✅ PASS: Both databases created with base data")
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
            convert_db.convert()
            
            # Base database should NOT exist
            if os.path.exists("prediction_cache.sqlite"):
                print("❌ FAIL: prediction_cache.sqlite should not be created")
                return False
            
            # Full database should exist
            if not os.path.exists("prediction_cache_full.sqlite"):
                print("❌ FAIL: prediction_cache_full.sqlite not created")
                return False
            
            valid, msg = verify_sqlite_structure("prediction_cache_full.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            contents = get_database_contents("prediction_cache_full.sqlite")
            if contents != full_models_data:
                print(f"❌ FAIL: Wrong data in full database")
                return False
            
            print("✅ PASS: Only full database created")
            return True
            
        finally:
            os.chdir(original_dir)


def test_neither_cache_present():
    """Test when neither cache is present."""
    print("\n" + "="*60)
    print("TEST 4: Neither cache present (should error)")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
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


def test_backward_compatibility():
    """Test backward compatibility with existing consumers."""
    print("\n" + "="*60)
    print("TEST 5: Backward compatibility check")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            test_data = {
                "The Balanced Generalist|5|Small (20%)|age,c_charge_degree,race,sex": "0101001101",
                "The Rule-Maker|3|Medium (60%)|days_b_screening_arrest,priors_count,sex": "1010101010",
            }
            
            create_test_cache("prediction_cache.json.gz", test_data)
            convert_db.convert()
            
            # Verify base database structure
            valid, msg = verify_sqlite_structure("prediction_cache.sqlite")
            if not valid:
                print(f"❌ FAIL: {msg}")
                return False
            
            # Test existing consumer pattern
            conn = sqlite3.connect("prediction_cache.sqlite")
            cursor = conn.cursor()
            
            test_key = "The Balanced Generalist|5|Small (20%)|age,c_charge_degree,race,sex"
            cursor.execute("SELECT value FROM cache WHERE key=?", (test_key,))
            row = cursor.fetchone()
            
            if not row:
                print(f"❌ FAIL: Key not found")
                conn.close()
                return False
            
            raw_val = row[0]
            
            # Parse value as existing consumers do
            if isinstance(raw_val, str):
                if raw_val.startswith("["):
                    predictions = json.loads(raw_val)
                else:
                    predictions = [int(c) for c in raw_val]
            
            if predictions != [0, 1, 0, 1, 0, 0, 1, 1, 0, 1]:
                print(f"❌ FAIL: Wrong predictions")
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
        test_backward_compatibility,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
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
