# Prediction Cache Conversion Documentation

## Overview

The `convert_db.py` script and the Dockerfile have been updated to support dual prediction cache files. This allows for more flexible cache management and merging of different cache sources.

## Supported Cache Files

The system now supports two cache files:

1. **`prediction_cache.json.gz`** - Base cache file (original)
2. **`prediction_cache_full_models.json.gz`** - Full models cache file (new)

## Behavior

### Cache File Presence

The conversion process handles the following scenarios:

- ✅ **Both files present**: Loads and merges both caches with full_models taking precedence on key conflicts
- ✅ **Only base cache present**: Processes as before (backward compatible)
- ✅ **Only full_models cache present**: Processes only the full_models cache
- ❌ **Neither file present**: Raises `FileNotFoundError` with clear error message

### Merge Strategy

When both cache files are present:

1. Base cache is loaded first
2. Full models cache is loaded second
3. Keys from full_models **override** keys from base cache
4. The resulting merged cache is written to SQLite

This ensures that full_models predictions take precedence over base predictions for any overlapping keys.

## Database Structure

The SQLite database structure remains **unchanged** for backward compatibility:

```sql
CREATE TABLE cache (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

This ensures existing consumers continue to work without modifications.

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
   ℹ️  Merged with precedence: 50 keys from full_models override base

📊 Merge Summary:
   • Total unique entries: 1450
   • Merge strategy: full_models takes precedence on conflicts

💾 Converting to SQLite database: prediction_cache.sqlite
✅ Success! Created prediction_cache.sqlite with 1450 entries
   • Table structure: cache(key TEXT PRIMARY KEY, value TEXT)
============================================================
```

## Testing

A comprehensive test suite is available at `tests/test_convert_db.py`:

```bash
python tests/test_convert_db.py
```

The test suite covers:

1. ✅ Both cache files present (merge with precedence)
2. ✅ Only base cache present
3. ✅ Only full_models cache present
4. ✅ Neither cache present (error handling)
5. ✅ Backward compatibility with existing consumers

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

- Existing consumers using `prediction_cache.sqlite` continue to work unchanged
- The SQLite table structure is identical
- Single cache file usage works exactly as before
- Query patterns remain the same

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
