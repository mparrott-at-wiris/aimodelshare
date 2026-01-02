import sqlite3
import os
import sys
import json

# Configuration
DB_PATH = "prediction_cache.sqlite"
SAMPLES_TO_CHECK = 5

def verify_cache_integrity():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file '{DB_PATH}' not found.")
        sys.exit(1)

    print(f"📂 Connected to {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache';")
        if not cursor.fetchone():
            print("❌ Error: 'cache' table not found in database.")
            sys.exit(1)

        # 2. Fetch sample rows
        cursor.execute(f"SELECT key, value FROM cache LIMIT {SAMPLES_TO_CHECK}")
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ Warning: Database is empty.")
            sys.exit(0)

        print(f"🔍 Inspecting {len(rows)} sample entries...\n")

        for i, (key, value) in enumerate(rows):
            print(f"--- Sample {i+1} ---")
            print(f"🔑 Key: {key}")
            print(f"📦 Raw Value Type: {type(value)}")
            print(f"📦 Raw Value Preview: {str(value)[:50]}...")

            # --- APPLICATION PARSING LOGIC SIMULATION ---
            # This mimics exactly what your Gradio app does in 'run_experiment'
            try:
                if isinstance(value, str):
                    # Test for JSON format vs Compact String format
                    if value.startswith("["):
                        print("   ℹ️ Detected JSON format")
                        predictions = json.loads(value)
                    else:
                        print("   ℹ️ Detected Compact String format ('0101...')")
                        predictions = [int(c) for c in value]
                else:
                    predictions = value

                # --- VERIFICATION FOR SUBMIT_MODEL ---
                if not isinstance(predictions, list):
                    print(f"❌ FAIL: Predictions are {type(predictions)}, expected list.")
                    sys.exit(1)
                
                if len(predictions) > 0 and not isinstance(predictions[0], int):
                    print(f"❌ FAIL: Prediction elements are {type(predictions[0])}, expected int.")
                    sys.exit(1)

                print(f"✅ PASS: Successfully parsed into List[int]. Length: {len(predictions)}")

            except Exception as e:
                print(f"❌ FAIL: Parsing raised an exception: {e}")
                sys.exit(1)

        print("\n✅ SUCCESS: Cache data structure matches 'submit_model' expectations.")
        conn.close()

    except Exception as e:
        print(f"❌ Critical DB Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_cache_integrity()
