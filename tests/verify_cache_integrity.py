import sqlite3
import os
import sys
import json
import time
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION (Must match Gradio App exactly) ---
DB_PATH = "prediction_cache.sqlite"
PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m" # From your app code

# Mock Data Constants
MODEL_NAME = "The Balanced Generalist"
COMPLEXITY = 2
DATA_SIZE = "Small (20%)"
FEATURE_SET_GROUP_1_VALS = [
    "juv_fel_count", "juv_misd_count", "juv_other_count", "race", "sex",
    "c_charge_degree", "days_b_screening_arrest"
]

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file '{DB_PATH}' not found.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def test_cache_retrieval(conn):
    """Retrieves prediction list from SQLite using App logic."""
    print("\n🔬 TEST 1: Cache Retrieval")
    
    # 1. Construct Key
    sanitized_features = sorted([str(f) for f in FEATURE_SET_GROUP_1_VALS])
    feature_key = ",".join(sanitized_features)
    cache_key = f"{MODEL_NAME}|{COMPLEXITY}|{DATA_SIZE}|{feature_key}"
    print(f"   ℹ️  Lookup Key: '{cache_key}'")

    # 2. Query
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM cache WHERE key=?", (cache_key,))
    row = cursor.fetchone()

    if not row:
        print("   ❌ FAIL: Key not found in DB.")
        sys.exit(1)

    # 3. Parse
    raw_val = row[0]
    try:
        if isinstance(raw_val, str):
            if raw_val.startswith("["):
                predictions = json.loads(raw_val)
            else:
                predictions = [int(c) for c in raw_val]
        else:
            predictions = raw_val
            
        print(f"   ✅ SUCCESS: Retrieved {len(predictions)} predictions.")
        return predictions
    except Exception as e:
        print(f"   ❌ FAIL: Parsing error: {e}")
        sys.exit(1)

def test_live_submission(predictions):
    """
    Submits the retrieved predictions to the actual AIModelShare playground.
    Mimics the 'submit_model' call in 'run_experiment'.
    """
    print("\n🔬 TEST 2: Live Submission (submit_model)")

    try:
        from aimodelshare.playground import Competition
    except ImportError:
        print("   ❌ FAIL: 'aimodelshare' library not installed.")
        print("      Run: pip install aimodelshare")
        sys.exit(1)

    # 1. Initialize Competition
    try:
        playground = Competition(PLAYGROUND_URL)
        print("   ✅ Connected to Playground.")
    except Exception as e:
        print(f"   ❌ FAIL: Could not connect to playground: {e}")
        sys.exit(1)

    # 2. Prepare Submission Metadata
    # Note: We pass None for model/preprocessor because we are submitting pre-calculated predictions
    description = "CI/CD Integrity Test"
    tags = "test:cache_verification"
    team_name = "Test_Bot"

    print("   ℹ️  Submitting predictions to server...")
    
    try:
        # 3. Call submit_model
        # We assume anonymous submission (token=None) for this test
        # to avoid needing secrets in this specific workflow step.
        result = playground.submit_model(
            model=None, 
            preprocessor=None, 
            prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': team_name}, 
            token=None,
            return_metrics=["accuracy"] 
        )
        
        # 4. Verify Return Structure
        # submit_model returns a tuple: (model_version, training_duration, metrics)
        if isinstance(result, tuple) and len(result) >= 3:
            metrics = result[2]
            if metrics and "accuracy" in metrics:
                acc = metrics["accuracy"]
                print(f"   ✅ SUCCESS: Submission accepted!")
                print(f"   📊 Returned Accuracy: {acc}")
                
                if not isinstance(acc, (int, float)):
                     print(f"   ⚠️ WARNING: Accuracy is {type(acc)}, expected float/int.")
            else:
                print(f"   ❌ FAIL: Metrics dict missing or 'accuracy' key not found: {metrics}")
                sys.exit(1)
        else:
             print(f"   ❌ FAIL: Unexpected return format from submit_model: {result}")
             sys.exit(1)

    except Exception as e:
        print(f"   ❌ FAIL: Submission crashed: {e}")
        sys.exit(1)

def main():
    print("--- 🚀 STARTING LIVE INTEGRATION TEST ---")
    
    # Step 1: Get Data
    conn = get_db_connection()
    predictions = test_cache_retrieval(conn)
    conn.close()

    # Step 2: Submit Data
    test_live_submission(predictions)

    print("\n--- ✅ ALL SYSTEM CHECKS PASSED ---")

if __name__ == "__main__":
    main()
