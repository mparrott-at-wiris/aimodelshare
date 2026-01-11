import gzip
import json
import sqlite3
import os

CACHE_FILE = "prediction_cache.json.gz"
CACHE_FILE_FULL_MODELS = "prediction_cache_full_models.json.gz"
DB_FILE = "prediction_cache.sqlite"
DB_FILE_FULL = "prediction_cache_full.sqlite"

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
    except (gzip.BadGzipFile, OSError) as e:
        print(f"   ❌ Error reading {filepath}: Invalid gzip file")
        return None
    except json.JSONDecodeError as e:
        print(f"   ❌ Error reading {filepath}: Invalid JSON format")
        return None
    except UnicodeDecodeError as e:
        print(f"   ❌ Error reading {filepath}: Invalid character encoding")
        return None
    except Exception as e:
        print(f"   ❌ Error reading {filepath}: {e}")
        return None

def create_database(db_path, data, description):
    """Create a SQLite database from the provided data dictionary."""
    print(f"\n💾 Converting to SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table with an index on the 'key' for super-fast lookups
    cursor.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
    
    # Bulk insert
    items = [(k, v) for k, v in data.items()]
    cursor.executemany("INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", items)
    
    conn.commit()
    
    # Create Index explicitly (though PRIMARY KEY implies it) to ensure speed
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON cache (key)")
    
    conn.close()
    print(f"✅ Success! Created {db_path} with {len(data)} entries")
    print(f"   • {description}")
    print(f"   • Table structure: cache(key TEXT PRIMARY KEY, value TEXT)")

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
    
    # Load base cache
    base_data = None
    if base_exists:
        base_data = load_cache_file(CACHE_FILE)
        if base_data is not None:
            print(f"\n📦 Base cache loaded: {len(base_data)} entries")
        else:
            print(f"\n⚠️  Warning: Failed to load {CACHE_FILE}")
    
    # Load full_models cache
    full_models_data = None
    if full_models_exists:
        full_models_data = load_cache_file(CACHE_FILE_FULL_MODELS)
        if full_models_data is not None:
            print(f"\n📦 Full models cache loaded: {len(full_models_data)} entries")
        else:
            print(f"\n⚠️  Warning: Failed to load {CACHE_FILE_FULL_MODELS}")
    
    # Validate that we have at least some data
    if base_data is None and full_models_data is None:
        print(f"\n❌ ERROR: No valid cache data found.")
        print(f"   Cache files exist but failed to load or are empty.")
        raise ValueError("No valid cache data available for conversion")
    
    print(f"\n{'=' * 60}")
    print("DATABASE 1: Original Base Cache")
    print("=" * 60)
    
    # Create original database from base cache only
    if base_data is not None:
        create_database(DB_FILE, base_data, "Source: prediction_cache.json.gz only")
    else:
        print(f"⚠️  Skipping {DB_FILE} - no base cache data available")
    
    print(f"\n{'=' * 60}")
    print("DATABASE 2: Combined Full Cache")
    print("=" * 60)
    
    # Create combined database with merge logic
    merged_data = {}
    
    # Start with base cache (if available)
    if base_data is not None:
        merged_data.update(base_data)
        print(f"   • Added {len(base_data)} entries from base cache")
    
    # Add/override with full_models cache (if available)
    if full_models_data is not None:
        conflicts = sum(1 for k in full_models_data if k in merged_data)
        merged_data.update(full_models_data)
        print(f"   • Added {len(full_models_data)} entries from full_models cache")
        if conflicts > 0 and base_data is not None:
            print(f"   • Merged with precedence: {conflicts} keys from full_models override base")
    
    # Determine description
    if base_data is not None and full_models_data is not None:
        description = "Source: merged from both caches (full_models takes precedence)"
    elif base_data is not None:
        description = "Source: prediction_cache.json.gz only"
    else:
        description = "Source: prediction_cache_full_models.json.gz only"
    
    print(f"\n📊 Combined Cache Summary:")
    print(f"   • Total unique entries: {len(merged_data)}")
    
    create_database(DB_FILE_FULL, merged_data, description)
    
    print("=" * 60)
    print("✅ CONVERSION COMPLETE")
    print("=" * 60)
    print(f"Created databases:")
    if base_data is not None:
        print(f"   • {DB_FILE} - Original base cache ({len(base_data)} entries)")
    print(f"   • {DB_FILE_FULL} - Combined cache ({len(merged_data)} entries)")
    print("=" * 60)

if __name__ == "__main__":
    convert()
