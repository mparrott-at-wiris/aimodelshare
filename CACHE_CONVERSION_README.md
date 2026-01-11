# Prediction Cache Conversion Documentation

## Overview

The `convert_db.py` script and the Dockerfile have been updated to support dual prediction cache files and create two separate SQLite databases.

## Supported Cache Files

The system now supports two cache files:

1. **`prediction_cache.json.gz`** - Base cache file (original)
2. **`prediction_cache_full_models.json.gz`** - Full models cache file

## Output Databases

The conversion process creates **two separate SQLite databases**:

1. **`prediction_cache.sqlite`** - Contains ONLY data from `prediction_cache.json.gz` (original behavior preserved)
2. **`prediction_cache_full.sqlite`** - Contains merged data from both cache files (with full_models taking precedence on conflicts)

## Behavior

### Cache File Presence

The conversion process handles the following scenarios:

- ✅ **Both files present**: Creates both databases
  - `prediction_cache.sqlite` with base cache only
  - `prediction_cache_full.sqlite` with merged data (full_models takes precedence)
- ✅ **Only base cache present**: Creates both databases with same data from base cache
- ✅ **Only full_models cache present**: Creates only `prediction_cache_full.sqlite`
- ❌ **Neither file present**: Raises `FileNotFoundError` with clear error message

### Database Creation Strategy

**Database 1: `prediction_cache.sqlite`**
- Created ONLY when `prediction_cache.json.gz` is present
- Contains exclusively data from the base cache
- Preserves original behavior for backward compatibility
- Existing consumers continue to work unchanged

**Database 2: `prediction_cache_full.sqlite`**
- Always created when at least one cache file is present
- Merge strategy when both caches exist:
  1. Start with base cache data
  2. Add/override with full_models cache data
  3. Full_models keys take precedence on conflicts
- When only one cache exists, contains that cache's data

## Database Structure

Both SQLite databases have **identical structure** for compatibility:

```sql
CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

This ensures existing consumers can use either database without modifications.

## Usage

### Docker Build

The Dockerfile automatically handles cache conversion during build:

```dockerfile
# Copy converter script
COPY convert_db.py .

# Copy available cache files (wildcard supports both files)
COPY prediction_cache*.json.gz ./

# Run conversion and cleanup
RUN echo "=== Starting Cache Conversion ===" && \
    python convert_db.py && \
    echo "=== Cleaning up cache files ===" && \
    rm -f prediction_cache.json.gz prediction_cache_full_models.json.gz && \
    echo "=== Cache conversion complete ==="
```

**Note**: At least one cache file must be present in the build context, or the Docker build will fail at the COPY step.

### Manual Conversion

You can also run the converter manually:

```bash
python convert_db.py
```

The script provides detailed status messages:

```
============================================================
🔄 CACHE CONVERSION TO SQLITE
============================================================

📋 Cache File Status:
   • prediction_cache.json.gz: ✅ Found
   • prediction_cache_full_models.json.gz: ✅ Found
📖 Reading prediction_cache.json.gz (this may take 15s)...
   ✅ Loaded 1000 entries from prediction_cache.json.gz

📦 Base cache loaded: 1000 entries
📖 Reading prediction_cache_full_models.json.gz (this may take 15s)...
   ✅ Loaded 500 entries from prediction_cache_full_models.json.gz

📦 Full models cache loaded: 500 entries

============================================================
DATABASE 1: Original Base Cache
============================================================

💾 Converting to SQLite database: prediction_cache.sqlite
✅ Success! Created prediction_cache.sqlite with 1000 entries
   • Source: prediction_cache.json.gz only
   • Table structure: cache(key TEXT PRIMARY KEY, value TEXT)

============================================================
DATABASE 2: Combined Full Cache
============================================================
   • Added 1000 entries from base cache
   • Added 500 entries from full_models cache
   • Merged with precedence: 50 keys from full_models override base

📊 Combined Cache Summary:
   • Total unique entries: 1450

💾 Converting to SQLite database: prediction_cache_full.sqlite
✅ Success! Created prediction_cache_full.sqlite with 1450 entries
   • Source: merged from both caches (full_models takes precedence)
   • Table structure: cache(key TEXT PRIMARY KEY, value TEXT)
============================================================
✅ CONVERSION COMPLETE
============================================================
Created databases:
   • prediction_cache.sqlite - Original base cache (1000 entries)
   • prediction_cache_full.sqlite - Combined cache (1450 entries)
============================================================
```

## Testing

A comprehensive test suite is available at `tests/test_convert_db.py`:

```bash
python tests/test_convert_db.py
```

The test suite covers:

1. ✅ Both cache files present (creates both databases with proper merge)
2. ✅ Only base cache present (creates both databases with same data)
3. ✅ Only full_models cache present (creates only full database)
4. ✅ Neither cache present (error handling)
5. ✅ Backward compatibility with existing consumers using base database

## Cache Key Format

Cache keys follow this format:

```
{model_name}|{complexity}|{data_size}|{sorted_features}
```

Example:
```
The Balanced Generalist|5|Small (20%)|age,c_charge_degree,race,sex
```

## Backward Compatibility

The implementation maintains full backward compatibility:

- **Original database** (`prediction_cache.sqlite`) contains only base cache data, exactly as before
- The SQLite table structure is identical in both databases
- Single cache file usage works exactly as before
- Query patterns remain the same
- Existing consumers using `prediction_cache.sqlite` continue to work unchanged
- **New feature**: Applications can optionally use `prediction_cache_full.sqlite` for access to merged/full model data

## Troubleshooting

### Error: "Neither cache file found"

**Cause**: No cache files (`.json.gz`) are present in the working directory.

**Solution**: Ensure at least one of the following files exists:
- `prediction_cache.json.gz`
- `prediction_cache_full_models.json.gz`

### Docker build fails at COPY step

**Cause**: No cache files matching `prediction_cache*.json.gz` in build context.

**Solution**: Place at least one cache file in the repository root before building:
```bash
# Generate base cache
python precompute_cache.py

# Or generate full models cache
python precompute_full_models_cache.py
```

## Performance

- File loading uses gzip compression for efficient storage
- SQLite provides fast key-value lookups with indexed primary key
- Merge operation is efficient (O(n) where n = total entries)
- Memory-efficient: processes one cache at a time

## Future Enhancements

Possible future improvements:
- Support for additional cache sources
- Configurable merge strategies
- Incremental cache updates
- Cache validation and integrity checks
