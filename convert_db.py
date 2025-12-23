import gzip
import json
import sqlite3
import os

CACHE_FILE = "prediction_cache.json.gz"
DB_FILE = "prediction_cache.sqlite"

def convert():
    if not os.path.exists(CACHE_FILE):
        print(f"❌ {CACHE_FILE} not found. Skipping conversion.")
        return

    print(f"📖 Reading {CACHE_FILE} (this may take 15s)...")
    try:
        with gzip.open(CACHE_FILE, "rt", encoding="UTF-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    print(f"📦 Converting {len(data)} models to SQLite...")
    
    # Create DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create table with an index on the 'key' for super-fast lookups
    cursor.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
    
    # Bulk insert
    items = [(k, v) for k, v in data.items()]
    cursor.executemany("INSERT OR IGNORE INTO cache (key, value) VALUES (?, ?)", items)
    
    conn.commit()
    
    # Create Index explicitly (though PRIMARY KEY implies it) to ensure speed
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON cache (key)")
    
    conn.close()
    print(f"✅ Success! Created {DB_FILE}")

if __name__ == "__main__":
    convert()
