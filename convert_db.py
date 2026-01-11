import gzip
import json
import sqlite3
import os

CACHE_FILE = "prediction_cache.json.gz"
CACHE_FILE_FULL_MODELS = "prediction_cache_full_models.json.gz"
DB_FILE = "prediction_cache.sqlite"

def load_cache_file(filepath):
    """Load a single gzipped JSON cache file and return the data dictionary."""
    if not os.path.exists(filepath):
        return None
    
    print(f"📖 Reading {filepath} (this may take 15s)...")
    try:
        with gzip.open(filepath, "rt", encoding="UTF-8") as f:
            data = json.load(f)
        print(f"   ✅ Loaded {len(data)} entries from {filepath}")
        return data
    except Exception as e:
        print(f"   ❌ Error reading {filepath}: {e}")
        return None

def convert():
    print("=" * 60)
    print("🔄 CACHE CONVERSION TO SQLITE")
    print("=" * 60)
    
    # Check for cache files
    base_exists = os.path.exists(CACHE_FILE)
    full_models_exists = os.path.exists(CACHE_FILE_FULL_MODELS)
    
    print(f"\n📋 Cache File Status:")
    print(f"   • {CACHE_FILE}: {'✅ Found' if base_exists else '❌ Not Found'}")
    print(f"   • {CACHE_FILE_FULL_MODELS}: {'✅ Found' if full_models_exists else '❌ Not Found'}")
    
    # Error if neither is found
    if not base_exists and not full_models_exists:
        print(f"\n❌ ERROR: Neither cache file found. At least one is required.")
        print(f"   Expected: {CACHE_FILE} or {CACHE_FILE_FULL_MODELS}")
        raise FileNotFoundError("No cache files found for conversion")
    
    # Load available cache files
    merged_data = {}
    
    # Load base cache first (if present)
    if base_exists:
        base_data = load_cache_file(CACHE_FILE)
        if base_data:
            merged_data.update(base_data)
            print(f"\n📦 Base cache loaded: {len(base_data)} entries")
    
    # Load full_models cache (if present) - this takes precedence
    if full_models_exists:
        full_models_data = load_cache_file(CACHE_FILE_FULL_MODELS)
        if full_models_data:
            # Count conflicts for reporting
            conflicts = sum(1 for k in full_models_data if k in merged_data)
            merged_data.update(full_models_data)
            print(f"\n📦 Full models cache loaded: {len(full_models_data)} entries")
            if conflicts > 0 and base_exists:
                print(f"   ℹ️  Merged with precedence: {conflicts} keys from full_models override base")
    
    # Final summary
    total_entries = len(merged_data)
    print(f"\n📊 Merge Summary:")
    print(f"   • Total unique entries: {total_entries}")
    if base_exists and full_models_exists:
        print(f"   • Merge strategy: full_models takes precedence on conflicts")
    elif base_exists:
        print(f"   • Source: base cache only")
    else:
        print(f"   • Source: full_models cache only")
    
    # Create SQLite database
    print(f"\n💾 Converting to SQLite database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create table with an index on the 'key' for super-fast lookups
    cursor.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
    
    # Bulk insert
    items = [(k, v) for k, v in merged_data.items()]
    cursor.executemany("INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", items)
    
    conn.commit()
    
    # Create Index explicitly (though PRIMARY KEY implies it) to ensure speed
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON cache (key)")
    
    conn.close()
    print(f"✅ Success! Created {DB_FILE} with {total_entries} entries")
    print(f"   • Table structure: cache(key TEXT PRIMARY KEY, value TEXT)")
    print("=" * 60)

if __name__ == "__main__":
    convert()
