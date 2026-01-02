import sqlite3
import os
import sys
import json
import numpy as np
import pandas as pd

# --- NEW IMPORT: For Session -> Token Conversion ---
from aimodelshare.aws import get_token_from_session

# --- 1. CONFIGURATION ---
DB_PATH = "prediction_cache.sqlite"
PLAYGROUND_URL = "https://cf3wdpkg0d.execute-api.us-east-1.amazonaws.com/prod/m"

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
    
    sanitized_features = sorted([str(f) for f in FEATURE_SET_GROUP_1_VALS])
    feature_key = ",".join(sanitized_features)
    cache_key = f"{MODEL_NAME}|{COMPLEXITY}|{DATA_SIZE}|{feature_key}"
    print(f"   ℹ️  Lookup Key: '{cache_key}'")

    cursor = conn.cursor()
    cursor.execute("SELECT value FROM cache WHERE key=?", (cache_key,))
    row = cursor.fetchone()

    if not row:
        print("   ❌ FAIL: Key not found in DB.")
        sys.exit(1)

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
    """Submits the retrieved predictions to the actual AIModelShare playground."""
    print("\n🔬 TEST 2: Live Submission (submit_model)")

    # --- UPDATED IMPORT LOGIC ---
    try:
        from aimodelshare.playground import Competition
    except ImportError as e:
        print(f"   ❌ FAIL: Could not import 'aimodelshare.playground.Competition'.")
        print(f"      Error details: {e}")
        print("      HINT: Check if optional dependencies like 'Jinja2' are installed.")
        sys.exit(1)
    # ----------------------------

    # 1. Initialize Competition
    try:
        playground = Competition(PLAYGROUND_URL)
        print("   ✅ Connected to Playground.")
    except Exception as e:
        print(f"   ❌ FAIL: Could not connect to playground: {e}")
        sys.exit(1)

    # ... (Rest of the function remains the same)

    # --- NEW LOGIC: EXTRACT TOKEN FROM SESSION ID ---
    session_id = os.environ.get("SESSION_ID")
    token = None

    if session_id:
        print(f"   ℹ️  Session ID detected (length: {len(session_id)})")
        try:
            # Replicating logic from the App's _try_session_based_auth
            token = get_token_from_session(session_id)
            if token:
                print("   ✅ SUCCESS: Token extracted from session.")
            else:
                print("   ❌ FAIL: get_token_from_session returned None.")
                sys.exit(1)
        except Exception as e:
            print(f"   ❌ FAIL: Error extracting token: {e}")
            sys.exit(1)
    else:
        print("   ⚠️ WARNING: 'SESSION_ID' secret not found in env. Submitting Anonymously.")

    # ------------------------------------------------

    try:
        playground = Competition(PLAYGROUND_URL)
        print("   ✅ Connected to Playground.")
    except Exception as e:
        print(f"   ❌ FAIL: Could not connect to playground: {e}")
        sys.exit(1)

    description = "CI/CD Integrity Test"
    tags = "test:cache_verification"
    team_name = "The Fairness Finders"

    print("   ℹ️  Submitting predictions to server...")
    
    try:
        # Pass the extracted token here
        result = playground.submit_model(
            model=None, 
            preprocessor=None, 
            prediction_submission=predictions,
            input_dict={'description': description, 'tags': tags},
            custom_metadata={'Team': team_name}, 
            token=token,  # <--- INJECTED HERE
            return_metrics=["accuracy"] 
        )
        
        if isinstance(result, tuple) and len(result) >= 3:
            metrics = result[2]
            if metrics and "accuracy" in metrics:
                acc = metrics["accuracy"]
                print(f"   ✅ SUCCESS: Submission accepted!")
                print(f"   📊 Returned Accuracy: {acc}")
            else:
                print(f"   ❌ FAIL: Metrics dict missing or 'accuracy' key not found: {metrics}")
                sys.exit(1)
        else:
             print(f"   ❌ FAIL: Unexpected return format from submit_model: {result}")
             sys.exit(1)

    except Exception as e:
        print(f"   ❌ FAIL: Submission crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    conn = get_db_connection()
    predictions = test_cache_retrieval(conn)
    conn.close()
    test_live_submission(predictions)
    print("\n--- ✅ ALL SYSTEM CHECKS PASSED ---")
