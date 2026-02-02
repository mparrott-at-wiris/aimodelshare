"""
Test suite for validating WiDS cache key compatibility between cache artifacts
and the Sustainability model-building app.

Purpose
-------
This test validates that:
1. Cache keys use the expected format: "model_name|complexity|data_size_label|comma_joined_features"
2. All app-selectable options have corresponding cache entries
3. Default configurations are fully covered in the cache

Fixture Management
------------------
This test uses fixture files in tests/fixtures/wids_cache/:
- wids_prediction_cache.json.gz (base cache)
- wids_prediction_cache_full_models.json.gz (full models cache)

To update fixtures:
1. Generate real cache data using precompute_wids_cache.py
2. Copy artifacts to tests/fixtures/wids_cache/ or update fixture creation
3. Ensure fixtures contain representative samples of all key format variations

Test Strategy
-------------
- Loads fixture cache artifacts (gzipped JSON files)
- Converts them to SQLite databases using convert_db_wids.py logic
- Extracts and parses all cache keys
- Compares key components against app configuration
- Reports missing coverage and format mismatches

Cache Key Format
----------------
Expected format: "model_name|complexity|data_size_label|comma_joined_features"
Example: "The Balanced Generalist|2|Small (20%)|building_class,facility_type,floor_area,year_built"

Components:
- model_name: One of MODEL_TYPES keys from the app
- complexity: Integer (1-10 range in app)
- data_size_label: One of DATA_SIZE_MAP keys (e.g., "Small (20%)")
- comma_joined_features: Alphabetically sorted, comma-separated feature names
"""

import os
import sys
import json
import gzip
import sqlite3
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import conversion logic
import convert_db_wids

# Import app configuration (without launching Gradio)
# We need to be careful not to launch the Gradio app, just import constants
sys.path.insert(0, str(Path(__file__).parent.parent / "aimodelshare"))

# Mock os.environ to prevent any test mode side effects
_original_environ = dict(os.environ)


def get_app_config():
    """
    Extract configuration from the sustainability app without launching Gradio.
    
    Returns dict with:
    - MODEL_TYPES: dict of model names to model configs
    - DATA_SIZE_MAP: dict of data size labels to fractions
    - DEFAULT_MODEL: default model name
    - DEFAULT_DATA_SIZE: default data size label
    - DEFAULT_FEATURE_SET: list of default feature names
    - FEATURE_SET_GROUP_1_VALS: list of feature names
    - FEATURE_SET_GROUP_2_VALS: list of feature names
    - FEATURE_SET_GROUP_3_VALS: list of feature names
    """
    # Read the app file and extract constants using regex to avoid import issues
    app_path = Path(__file__).parent.parent / "aimodelshare" / "moral_compass" / "apps" / "sustainability" / "model_building_app_en_sustainability.py"
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract constants by parsing the file
    import re
    import ast
    
    # Parse MODEL_TYPES keys - need to find the top-level dictionary keys only
    # Pattern: "The Model Name": {
    model_types_pattern = r'MODEL_TYPES\s*=\s*\{(.*?)\n\}'
    model_types_match = re.search(model_types_pattern, content, re.DOTALL)
    model_types = {}
    if model_types_match:
        # Extract model names - they are at the start of a line with quotes followed by colon
        # and they typically start with "The"
        model_block = model_types_match.group(1)
        model_names = re.findall(r'^\s*"(The [^"]+)"\s*:', model_block, re.MULTILINE)
        model_types = {name: {} for name in model_names}
    
    # Extract DEFAULT_MODEL
    default_model_match = re.search(r'DEFAULT_MODEL\s*=\s*"([^"]+)"', content)
    default_model = default_model_match.group(1) if default_model_match else None
    
    # Extract DATA_SIZE_MAP
    data_size_map_match = re.search(r'DATA_SIZE_MAP\s*=\s*\{([^}]+)\}', content, re.MULTILINE)
    data_size_map = {}
    if data_size_map_match:
        # Extract keys
        keys_pattern = r'"([^"]+)"\s*:'
        data_sizes = re.findall(keys_pattern, data_size_map_match.group(0))
        data_size_map = {size: 0.0 for size in data_sizes}
    
    # Extract DEFAULT_DATA_SIZE
    default_data_size_match = re.search(r'DEFAULT_DATA_SIZE\s*=\s*"([^"]+)"', content)
    default_data_size = default_data_size_match.group(1) if default_data_size_match else None
    
    # Extract FEATURE_SET_GROUP values
    feature_group_1_match = re.search(r'FEATURE_SET_GROUP_1_VALS\s*=\s*\[([\s\S]*?)\]', content)
    feature_group_1 = []
    if feature_group_1_match:
        # Extract string literals
        feature_group_1 = re.findall(r'"([^"]+)"', feature_group_1_match.group(1))
    
    feature_group_2_match = re.search(r'FEATURE_SET_GROUP_2_VALS\s*=\s*\[([\s\S]*?)\]', content)
    feature_group_2 = []
    if feature_group_2_match:
        feature_group_2 = re.findall(r'"([^"]+)"', feature_group_2_match.group(1))
    
    feature_group_3_match = re.search(r'FEATURE_SET_GROUP_3_VALS\s*=\s*\[([\s\S]*?)\]', content)
    feature_group_3 = []
    if feature_group_3_match:
        feature_group_3 = re.findall(r'"([^"]+)"', feature_group_3_match.group(1))
    
    # Extract DEFAULT_FEATURE_SET reference (it equals FEATURE_SET_GROUP_1_VALS)
    default_feature_set_match = re.search(r'DEFAULT_FEATURE_SET\s*=\s*(\w+)', content)
    default_feature_set = feature_group_1  # Default is group 1
    
    return {
        "MODEL_TYPES": model_types,
        "DATA_SIZE_MAP": data_size_map,
        "DEFAULT_MODEL": default_model,
        "DEFAULT_DATA_SIZE": default_data_size,
        "DEFAULT_FEATURE_SET": default_feature_set,
        "FEATURE_SET_GROUP_1_VALS": feature_group_1,
        "FEATURE_SET_GROUP_2_VALS": feature_group_2,
        "FEATURE_SET_GROUP_3_VALS": feature_group_3,
    }


class CacheKeyParser:
    """Parse and validate cache key structure."""
    
    EXPECTED_DELIMITER = "|"
    EXPECTED_SEGMENT_COUNT = 4
    FEATURE_DELIMITER = ","
    
    def __init__(self):
        self.parsed_keys: List[Dict] = []
        self.errors: List[str] = []
    
    def parse_key(self, key: str) -> Dict:
        """
        Parse a cache key into its components.
        
        Returns dict with:
        - original: original key string
        - model_name: extracted model name
        - complexity: extracted complexity (as string)
        - data_size: extracted data size label
        - features: list of feature names
        - valid: whether the key has expected structure
        - error: error message if invalid
        """
        segments = key.split(self.EXPECTED_DELIMITER)
        
        result = {
            "original": key,
            "valid": False,
            "error": None,
            "model_name": None,
            "complexity": None,
            "data_size": None,
            "features": None,
        }
        
        if len(segments) != self.EXPECTED_SEGMENT_COUNT:
            result["error"] = f"Expected {self.EXPECTED_SEGMENT_COUNT} segments, got {len(segments)}"
            self.errors.append(f"Key '{key}': {result['error']}")
            return result
        
        model_name, complexity, data_size, features_str = segments
        
        # Parse features
        features = features_str.split(self.FEATURE_DELIMITER) if features_str else []
        
        result.update({
            "valid": True,
            "model_name": model_name,
            "complexity": complexity,
            "data_size": data_size,
            "features": features,
        })
        
        return result
    
    def parse_all_keys(self, keys: List[str]) -> List[Dict]:
        """Parse all keys and return parsed results."""
        self.parsed_keys = [self.parse_key(key) for key in keys]
        return self.parsed_keys
    
    def get_valid_keys(self) -> List[Dict]:
        """Return only valid parsed keys."""
        return [k for k in self.parsed_keys if k["valid"]]
    
    def get_invalid_keys(self) -> List[Dict]:
        """Return only invalid parsed keys."""
        return [k for k in self.parsed_keys if not k["valid"]]


class CoverageTester:
    """Test coverage of app options in cache keys."""
    
    def __init__(self, parsed_keys: List[Dict], app_config: Dict):
        self.parsed_keys = parsed_keys
        self.app_config = app_config
        self.coverage_report: Dict = {}
    
    def analyze_coverage(self) -> Dict:
        """
        Analyze coverage of all app options.
        
        Returns dict with coverage results for:
        - models
        - data_sizes
        - feature_sets
        - defaults
        """
        # Extract unique values from parsed keys
        models_in_cache = set(k["model_name"] for k in self.parsed_keys if k["valid"])
        data_sizes_in_cache = set(k["data_size"] for k in self.parsed_keys if k["valid"])
        complexities_in_cache = set(k["complexity"] for k in self.parsed_keys if k["valid"])
        
        # Feature sets - need to compare as sorted tuples
        feature_sets_in_cache = set(
            tuple(sorted(k["features"])) for k in self.parsed_keys if k["valid"]
        )
        
        # App expectations
        models_in_app = set(self.app_config["MODEL_TYPES"].keys())
        data_sizes_in_app = set(self.app_config["DATA_SIZE_MAP"].keys())
        
        # Feature set groups
        feature_group_1 = tuple(sorted(self.app_config["FEATURE_SET_GROUP_1_VALS"]))
        feature_group_2 = tuple(sorted(self.app_config["FEATURE_SET_GROUP_2_VALS"]))
        feature_group_3 = tuple(sorted(self.app_config["FEATURE_SET_GROUP_3_VALS"]))
        default_features = tuple(sorted(self.app_config["DEFAULT_FEATURE_SET"]))
        
        # Check coverage
        self.coverage_report = {
            "models": {
                "in_app": models_in_app,
                "in_cache": models_in_cache,
                "covered": models_in_cache & models_in_app,
                "missing": models_in_app - models_in_cache,
                "extra": models_in_cache - models_in_app,
            },
            "data_sizes": {
                "in_app": data_sizes_in_app,
                "in_cache": data_sizes_in_cache,
                "covered": data_sizes_in_cache & data_sizes_in_app,
                "missing": data_sizes_in_app - data_sizes_in_cache,
                "extra": data_sizes_in_cache - data_sizes_in_app,
            },
            "complexities": {
                "in_cache": complexities_in_cache,
                "min": min(int(c) for c in complexities_in_cache) if complexities_in_cache else None,
                "max": max(int(c) for c in complexities_in_cache) if complexities_in_cache else None,
            },
            "feature_sets": {
                "in_cache": feature_sets_in_cache,
                "default_covered": default_features in feature_sets_in_cache,
                "group_1_covered": feature_group_1 in feature_sets_in_cache,
                "group_2_covered": any(set(feature_group_2).issubset(set(fs)) for fs in feature_sets_in_cache),
                "group_3_covered": any(set(feature_group_3).issubset(set(fs)) for fs in feature_sets_in_cache),
            },
            "defaults": {
                "default_model": self.app_config["DEFAULT_MODEL"],
                "default_data_size": self.app_config["DEFAULT_DATA_SIZE"],
                "default_features": default_features,
                "default_model_covered": self.app_config["DEFAULT_MODEL"] in models_in_cache,
                "default_data_size_covered": self.app_config["DEFAULT_DATA_SIZE"] in data_sizes_in_cache,
                "default_features_covered": default_features in feature_sets_in_cache,
            }
        }
        
        return self.coverage_report
    
    def get_missing_defaults(self) -> List[str]:
        """Return list of missing default configurations."""
        missing = []
        
        defaults = self.coverage_report["defaults"]
        
        if not defaults["default_model_covered"]:
            missing.append(f"Default model '{defaults['default_model']}' not found in cache")
        
        if not defaults["default_data_size_covered"]:
            missing.append(f"Default data size '{defaults['default_data_size']}' not found in cache")
        
        if not defaults["default_features_covered"]:
            features_str = ",".join(sorted(defaults["default_features"]))
            missing.append(f"Default feature set not found in cache: {features_str}")
        
        return missing
    
    def format_coverage_report(self) -> str:
        """Format coverage report as a readable string."""
        lines = []
        lines.append("=" * 80)
        lines.append("COVERAGE REPORT")
        lines.append("=" * 80)
        
        # Models
        lines.append("\nMODELS:")
        lines.append(f"  App defines: {len(self.coverage_report['models']['in_app'])} models")
        lines.append(f"  Cache contains: {len(self.coverage_report['models']['in_cache'])} models")
        lines.append(f"  Covered: {len(self.coverage_report['models']['covered'])} / {len(self.coverage_report['models']['in_app'])}")
        
        if self.coverage_report['models']['missing']:
            lines.append("\n  ⚠️  Missing from cache:")
            for model in sorted(self.coverage_report['models']['missing']):
                lines.append(f"    - {model}")
        
        if self.coverage_report['models']['extra']:
            lines.append("\n  ⚠️  In cache but not in app:")
            for model in sorted(self.coverage_report['models']['extra']):
                lines.append(f"    - {model}")
        
        # Data Sizes
        lines.append("\nDATA SIZES:")
        lines.append(f"  App defines: {len(self.coverage_report['data_sizes']['in_app'])} sizes")
        lines.append(f"  Cache contains: {len(self.coverage_report['data_sizes']['in_cache'])} sizes")
        lines.append(f"  Covered: {len(self.coverage_report['data_sizes']['covered'])} / {len(self.coverage_report['data_sizes']['in_app'])}")
        
        if self.coverage_report['data_sizes']['missing']:
            lines.append("\n  ⚠️  Missing from cache:")
            for size in sorted(self.coverage_report['data_sizes']['missing']):
                lines.append(f"    - {size}")
        
        # Complexities
        lines.append("\nCOMPLEXITY LEVELS:")
        comp = self.coverage_report['complexities']
        if comp['min'] is not None and comp['max'] is not None:
            lines.append(f"  Range in cache: {comp['min']} - {comp['max']}")
            lines.append(f"  Unique values: {len(comp['in_cache'])}")
        
        # Feature Sets
        lines.append("\nFEATURE SETS:")
        fs = self.coverage_report['feature_sets']
        lines.append(f"  Unique feature sets in cache: {len(fs['in_cache'])}")
        lines.append(f"  Default features covered: {'✓' if fs['default_covered'] else '✗'}")
        lines.append(f"  Group 1 (basic) covered: {'✓' if fs['group_1_covered'] else '✗'}")
        lines.append(f"  Group 2 (intermediate) covered: {'✓' if fs['group_2_covered'] else '✗'}")
        lines.append(f"  Group 3 (advanced) covered: {'✓' if fs['group_3_covered'] else '✗'}")
        
        # Defaults
        lines.append("\nDEFAULT CONFIGURATION:")
        defaults = self.coverage_report['defaults']
        lines.append(f"  Default model: {defaults['default_model']} {'✓' if defaults['default_model_covered'] else '✗'}")
        lines.append(f"  Default data size: {defaults['default_data_size']} {'✓' if defaults['default_data_size_covered'] else '✗'}")
        lines.append(f"  Default features: {'✓' if defaults['default_features_covered'] else '✗'}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


@pytest.fixture
def fixture_dir():
    """Return path to fixture directory."""
    return Path(__file__).parent / "fixtures" / "wids_cache"


@pytest.fixture
def temp_conversion_dir():
    """Create a temporary directory for database conversion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def app_config():
    """Load app configuration."""
    return get_app_config()


@pytest.fixture
def converted_databases(fixture_dir, temp_conversion_dir):
    """
    Convert fixture cache files to SQLite databases.
    
    Returns tuple of (base_db_path, full_db_path, keys_from_base, keys_from_full)
    """
    # Copy fixture files to temp directory
    import shutil
    
    base_cache_src = fixture_dir / "wids_prediction_cache.json.gz"
    full_cache_src = fixture_dir / "wids_prediction_cache_full_models.json.gz"
    
    base_cache_dst = temp_conversion_dir / "wids_prediction_cache.json.gz"
    full_cache_dst = temp_conversion_dir / "wids_prediction_cache_full_models.json.gz"
    
    if base_cache_src.exists():
        shutil.copy(base_cache_src, base_cache_dst)
    
    if full_cache_src.exists():
        shutil.copy(full_cache_src, full_cache_dst)
    
    # Change to temp directory for conversion
    original_dir = os.getcwd()
    os.chdir(temp_conversion_dir)
    
    try:
        # Run conversion
        convert_db_wids.convert()
        
        # Extract keys from databases
        base_db_path = temp_conversion_dir / "prediction_cache.sqlite"
        full_db_path = temp_conversion_dir / "prediction_cache_full.sqlite"
        
        keys_from_base = []
        keys_from_full = []
        
        if base_db_path.exists():
            conn = sqlite3.connect(str(base_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM cache")
            keys_from_base = [row[0] for row in cursor.fetchall()]
            conn.close()
        
        if full_db_path.exists():
            conn = sqlite3.connect(str(full_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM cache")
            keys_from_full = [row[0] for row in cursor.fetchall()]
            conn.close()
        
        return base_db_path, full_db_path, keys_from_base, keys_from_full
    
    finally:
        os.chdir(original_dir)


def test_fixture_files_exist(fixture_dir):
    """Test that fixture files exist and are readable."""
    base_cache = fixture_dir / "wids_prediction_cache.json.gz"
    full_cache = fixture_dir / "wids_prediction_cache_full_models.json.gz"
    
    assert base_cache.exists(), f"Base cache fixture not found: {base_cache}"
    assert full_cache.exists(), f"Full models cache fixture not found: {full_cache}"
    
    # Test that files are valid gzipped JSON
    with gzip.open(base_cache, "rt", encoding="UTF-8") as f:
        base_data = json.load(f)
    
    with gzip.open(full_cache, "rt", encoding="UTF-8") as f:
        full_data = json.load(f)
    
    assert isinstance(base_data, dict), "Base cache should be a dictionary"
    assert isinstance(full_data, dict), "Full models cache should be a dictionary"
    assert len(base_data) > 0, "Base cache should not be empty"
    assert len(full_data) > 0, "Full models cache should not be empty"
    
    print(f"\n✓ Base cache fixture: {len(base_data)} entries")
    print(f"✓ Full models cache fixture: {len(full_data)} entries")


def test_conversion_creates_databases(converted_databases):
    """Test that conversion creates both SQLite databases."""
    base_db_path, full_db_path, keys_from_base, keys_from_full = converted_databases
    
    assert base_db_path.exists(), "Base database was not created"
    assert full_db_path.exists(), "Full database was not created"
    
    assert len(keys_from_base) > 0, "Base database has no keys"
    assert len(keys_from_full) > 0, "Full database has no keys"
    
    print(f"\n✓ Base database: {len(keys_from_base)} keys")
    print(f"✓ Full database: {len(keys_from_full)} keys")


def test_cache_key_structure(converted_databases):
    """
    Test that all cache keys have the expected structure.
    
    Expected format: "model_name|complexity|data_size_label|comma_joined_features"
    """
    _, _, keys_from_base, keys_from_full = converted_databases
    
    # Combine keys from both databases
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parser.parse_all_keys(all_keys)
    
    invalid_keys = parser.get_invalid_keys()
    
    if invalid_keys:
        error_msg = f"Found {len(invalid_keys)} keys with invalid structure:\n"
        for k in invalid_keys:
            error_msg += f"  - {k['original']}: {k['error']}\n"
        pytest.fail(error_msg)
    
    print(f"\n✓ All {len(all_keys)} keys have valid structure")


def test_cache_key_delimiter(converted_databases):
    """Test that all keys use the expected delimiter."""
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    expected_delimiter = "|"
    wrong_delimiter_keys = []
    
    for key in all_keys:
        if expected_delimiter not in key:
            wrong_delimiter_keys.append(key)
    
    if wrong_delimiter_keys:
        error_msg = f"Found {len(wrong_delimiter_keys)} keys without expected delimiter '{expected_delimiter}':\n"
        for k in wrong_delimiter_keys[:5]:  # Show first 5
            error_msg += f"  - {k}\n"
        pytest.fail(error_msg)
    
    print(f"\n✓ All keys use delimiter '{expected_delimiter}'")


def test_model_coverage(converted_databases, app_config):
    """Test that cache covers all models defined in the app."""
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parsed_keys = parser.parse_all_keys(all_keys)
    valid_keys = parser.get_valid_keys()
    
    tester = CoverageTester(valid_keys, app_config)
    coverage = tester.analyze_coverage()
    
    print("\n" + tester.format_coverage_report())
    
    missing_models = coverage["models"]["missing"]
    
    if missing_models:
        error_msg = f"Cache is missing {len(missing_models)} model(s) defined in app:\n"
        for model in sorted(missing_models):
            error_msg += f"  - {model}\n"
        pytest.fail(error_msg)
    
    print(f"\n✓ All {len(coverage['models']['in_app'])} app models are covered in cache")


def test_data_size_coverage(converted_databases, app_config):
    """Test that cache covers all data sizes defined in the app."""
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parsed_keys = parser.parse_all_keys(all_keys)
    valid_keys = parser.get_valid_keys()
    
    tester = CoverageTester(valid_keys, app_config)
    coverage = tester.analyze_coverage()
    
    missing_sizes = coverage["data_sizes"]["missing"]
    
    if missing_sizes:
        error_msg = f"Cache is missing {len(missing_sizes)} data size(s) defined in app:\n"
        for size in sorted(missing_sizes):
            error_msg += f"  - {size}\n"
        pytest.fail(error_msg)
    
    print(f"\n✓ All {len(coverage['data_sizes']['in_app'])} app data sizes are covered in cache")


def test_default_configuration_coverage(converted_databases, app_config):
    """
    Test that cache covers the default configuration.
    
    This is critical - users must be able to submit with default settings.
    """
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parsed_keys = parser.parse_all_keys(all_keys)
    valid_keys = parser.get_valid_keys()
    
    tester = CoverageTester(valid_keys, app_config)
    coverage = tester.analyze_coverage()
    
    missing_defaults = tester.get_missing_defaults()
    
    if missing_defaults:
        error_msg = "Cache is missing default configuration(s):\n"
        for missing in missing_defaults:
            error_msg += f"  - {missing}\n"
        error_msg += "\nDefault configuration must be fully covered to allow first-time users to submit."
        pytest.fail(error_msg)
    
    print("\n✓ Default configuration is fully covered in cache")


def test_feature_set_format(converted_databases):
    """Test that feature sets in keys are properly formatted (comma-separated, sorted)."""
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parsed_keys = parser.parse_all_keys(all_keys)
    valid_keys = parser.get_valid_keys()
    
    issues = []
    
    for key in valid_keys:
        features = key["features"]
        
        # Check for empty features
        if not features:
            issues.append(f"Key has empty feature set: {key['original']}")
            continue
        
        # Check for proper sorting (should be alphabetically sorted)
        sorted_features = sorted(features)
        if features != sorted_features:
            issues.append(
                f"Key features not sorted: {key['original']}\n"
                f"  Current: {','.join(features)}\n"
                f"  Expected: {','.join(sorted_features)}"
            )
    
    if issues:
        error_msg = f"Found {len(issues)} issue(s) with feature set formatting:\n"
        for issue in issues[:5]:  # Show first 5
            error_msg += f"  - {issue}\n"
        pytest.fail(error_msg)
    
    print(f"\n✓ All feature sets are properly formatted (comma-separated, sorted)")


def test_complexity_range(converted_databases):
    """Test that complexity values are in a reasonable range."""
    _, _, keys_from_base, keys_from_full = converted_databases
    
    all_keys = list(set(keys_from_base + keys_from_full))
    
    parser = CacheKeyParser()
    parsed_keys = parser.parse_all_keys(all_keys)
    valid_keys = parser.get_valid_keys()
    
    # Extract complexity values
    complexities = []
    for key in valid_keys:
        try:
            complexity = int(key["complexity"])
            complexities.append(complexity)
        except ValueError:
            pytest.fail(f"Non-integer complexity in key: {key['original']}")
    
    min_complexity = min(complexities)
    max_complexity = max(complexities)
    
    # App uses 1-10 range (after rank unlocking)
    # But default starts at 2, so we expect at least that range
    assert min_complexity >= 1, f"Complexity too low: {min_complexity}"
    assert max_complexity <= 10, f"Complexity too high: {max_complexity}"
    
    print(f"\n✓ Complexity range: {min_complexity} - {max_complexity} (expected 1-10)")


def test_real_vs_fixture_indication():
    """
    Test that clearly indicates whether real artifacts or fixtures were used.
    
    This is informational only - helps understand test context.
    """
    fixture_dir = Path(__file__).parent / "fixtures" / "wids_cache"
    real_artifacts_dir = Path(__file__).parent.parent
    
    real_base = real_artifacts_dir / "wids_prediction_cache.json.gz"
    real_full = real_artifacts_dir / "wids_prediction_cache_full_models.json.gz"
    
    fixture_base = fixture_dir / "wids_prediction_cache.json.gz"
    fixture_full = fixture_dir / "wids_prediction_cache_full_models.json.gz"
    
    using_real_artifacts = real_base.exists() or real_full.exists()
    using_fixtures = fixture_base.exists() or fixture_full.exists()
    
    print("\n" + "=" * 80)
    print("TEST DATA SOURCE")
    print("=" * 80)
    
    if using_real_artifacts:
        print("⚠️  Real cache artifacts found in repository root:")
        if real_base.exists():
            print(f"  ✓ {real_base}")
        if real_full.exists():
            print(f"  ✓ {real_full}")
        print("\n  NOTE: This test uses FIXTURES, not real artifacts.")
        print("        To test against real artifacts, update the test to load from repo root.")
    
    if using_fixtures:
        print("\n✓ Using test fixtures:")
        if fixture_base.exists():
            print(f"  ✓ {fixture_base}")
        if fixture_full.exists():
            print(f"  ✓ {fixture_full}")
    
    print("=" * 80)
    
    assert using_fixtures, "No test fixtures found - test cannot run"


if __name__ == "__main__":
    # Allow running as a script for debugging
    pytest.main([__file__, "-v", "-s"])
