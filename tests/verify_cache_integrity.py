import sqlite3
import os
import sys
import json

# Configuration
DB_PATH = "prediction_cache.sqlite"

# --- MOCK DATA FROM YOUR APP CONFIGURATION ---
# These must match the constants in your Gradio app exactly
MODEL_TYPES = [
    "The Balanced Generalist", 
    "The Rule-Maker", 
    "The 'Nearest Neighbor'", 
    "The Deep Pattern-Finder"
]
DATA_SIZES = ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"]
COMPLEXITY_LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Feature Groups (from your app logic)
FEATURE_SET_GROUP_1_VALS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex",
    "c_charge_degree", "days_b_screening_arrest"
]
DEFAULT_FEATURE_SET = FEATURE_SET_GROUP_1_VALS

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file '{DB_PATH}' not found.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def test_specific_key_construction(conn):
    """
    Tests if constructing a key using APP LOGIC actually finds a row in the DB.
    """
    print("\n🔬 TEST 1: Key Construction & Retrieval")
    
    # 1. Simulate App Logic for Key Construction
    # Logic from run_experiment: 
    # sanitized_features = sorted([str(f) for f in feature_set])
    # feature_key = ",".join(sanitized_features)
    # cache_key = f"{model_name_key}|{complexity_level}|{data_size_str}|{feature_key}"

    model = "The Balanced Generalist"
    complexity = 2
    data_size = "Small (20%)"
    
    # Use the default feature set logic
    feature_set = DEFAULT_FEATURE_SET
    sanitized_features = sorted([str(f) for f in feature_set])
    feature_key = ",".join(sanitized_features)
    
    expected_key = f"{model}|{complexity}|{data_size}|{feature_key}"
    
    print(f"   ℹ️ Constructed Key: '{expected_key}'")

    # 2. Query DB
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM cache WHERE key=?", (expected_key,))
    row = cursor.fetchone()

    if row:
        print("   ✅ SUCCESS: Key found in database.")
        return row[0] # Return value for next test
    else:
        print("   ❌ FAIL: Key NOT found.")
        print("      Possible causes:")
        print("      1. Feature sorting order differs between Cache Builder and App.")
        print("      2. Complexity stored as float (2.0) instead of int (2).")
        print("      3. Spacing in Model Name or Data Size strings.")
        
        # Debug helper: print similar keys
        print("\n      🔎 Closest matches in DB:")
        cursor.execute("SELECT key FROM cache WHERE key LIKE ? LIMIT 3", (f"{model}%",))
        for r in cursor.fetchall():
            print(f"      Found: {r[0]}")
        sys.exit(1)

def test_value_format(value):
    """
    Tests if the retrieved value is formatted correctly for submit_model.
    """
    print("\n🔬 TEST 2: Value Formatting & Parsing")
    
    try:
        # Simulate App Decompression Logic
        if isinstance(value, str):
            if value.startswith("["):
                print("   ℹ️ Format: JSON String")
                predictions = json.loads(value)
            else:
                print("   ℹ️ Format: Compact String")
                predictions = [int(c) for c in value]
        else:
            print(f"   ℹ️ Format: Raw {type(value)}")
            predictions = value

        # Validation
        if not isinstance(predictions, list):
            print(f"   ❌ FAIL: Result is {type(predictions)}, expected list.")
            sys.exit(1)
        
        if len(predictions) == 0:
            print("   ⚠️ WARNING: Prediction list is empty.")
        elif not isinstance(predictions[0], int):
            print(f"   ❌ FAIL: Elements are {type(predictions[0])}, expected int.")
            sys.exit(1)
            
        print(f"   ✅ SUCCESS: Parsed {len(predictions)} predictions correctly.")
        print(f"   Preview: {predictions[:10]}...")

    except Exception as e:
        print(f"   ❌ FAIL: Exception during parsing: {e}")
        sys.exit(1)

def main():
    print("--- 🚀 STARTING INTEGRITY TEST ---")
    conn = get_db_connection()
    
    # Run Tests
    value = test_specific_key_construction(conn)
    test_value_format(value)
    
    conn.close()
    print("\n--- ✅ ALL TESTS PASSED ---")

if __name__ == "__main__":
    main()
