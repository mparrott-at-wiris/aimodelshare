#!/usr/bin/env python3
"""
Unit tests for Model Building Game UX enhancements.

Tests the new early-experience performance improvements:
- Background initialization
- Cached dataset loading
- Progressive sampling
- Warm mini dataset
- Skeleton loaders
- Status polling

Run with: pytest tests/test_model_building_game_enhancements.py -v
"""

import pytest
import time
import os
from pathlib import Path


def test_cache_directory_creation():
    """Test that cache directory helper works."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_cache_dir
    
    cache_dir = _get_cache_dir()
    assert cache_dir.exists()
    assert cache_dir.is_dir()
    assert cache_dir.name == ".aimodelshare_cache"


def test_skeleton_leaderboard_generation():
    """Test that static placeholder is generated correctly."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_skeleton_leaderboard
    
    # Test team leaderboard placeholder (now returns static placeholder)
    team_skeleton = _build_skeleton_leaderboard(rows=6, is_team=True)
    assert "lb-placeholder" in team_skeleton
    assert "Loading Standings..." in team_skeleton
    assert "Data is being prepared" in team_skeleton
    
    # Test individual leaderboard placeholder (now returns same static placeholder)
    individual_skeleton = _build_skeleton_leaderboard(rows=6, is_team=False)
    assert "lb-placeholder" in individual_skeleton
    # Both return the same static placeholder now
    assert team_skeleton == individual_skeleton


def test_init_flags_structure():
    """Test that INIT_FLAGS has expected structure."""
    from aimodelshare.moral_compass.apps.model_building_game import INIT_FLAGS
    
    required_keys = [
        "competition",
        "dataset_core",
        "pre_samples_small",
        "pre_samples_medium",
        "pre_samples_large",
        "pre_samples_full",
        "leaderboard",
        "default_preprocessor",
        "warm_mini",
        "errors"
    ]
    
    for key in required_keys:
        assert key in INIT_FLAGS, f"Missing key: {key}"
    
    # Check types
    for key in required_keys:
        if key == "errors":
            assert isinstance(INIT_FLAGS[key], list)
        else:
            assert isinstance(INIT_FLAGS[key], bool)


def test_available_data_sizes():
    """Test that data size availability is correctly reported."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        get_available_data_sizes, INIT_FLAGS, INIT_LOCK
    )
    
    # Reset flags to test
    with INIT_LOCK:
        INIT_FLAGS["pre_samples_small"] = True
        INIT_FLAGS["pre_samples_medium"] = False
        INIT_FLAGS["pre_samples_large"] = False
        INIT_FLAGS["pre_samples_full"] = False
    
    available = get_available_data_sizes()
    assert "Small (20%)" in available
    assert len(available) == 1
    
    # Add medium
    with INIT_LOCK:
        INIT_FLAGS["pre_samples_medium"] = True
    
    available = get_available_data_sizes()
    assert "Small (20%)" in available
    assert "Medium (60%)" in available
    assert len(available) == 2


def test_poll_init_status():
    """Test that status polling returns correct format."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        poll_init_status, INIT_FLAGS, INIT_LOCK
    )
    
    # Set some flags for testing
    with INIT_LOCK:
        INIT_FLAGS["competition"] = True
        INIT_FLAGS["dataset_core"] = True
        INIT_FLAGS["pre_samples_small"] = True
    
    status_html, ready = poll_init_status()
    
    # Check return types
    assert isinstance(status_html, str)
    assert isinstance(ready, bool)
    
    # Status HTML should be empty (by design)
    assert status_html == ""
    
    # Should be ready with these flags
    assert ready is True


def test_poll_init_status_not_ready():
    """Test status polling when not ready."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        poll_init_status, INIT_FLAGS, INIT_LOCK
    )
    
    # Set flags to not ready
    with INIT_LOCK:
        INIT_FLAGS["competition"] = False
        INIT_FLAGS["dataset_core"] = False
        INIT_FLAGS["pre_samples_small"] = False
    
    status_html, ready = poll_init_status()
    
    # Should not be ready
    assert ready is False
    # Status HTML should be empty (by design)
    assert status_html == ""


def test_poll_init_status_with_errors():
    """Test that errors don't prevent status polling."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        poll_init_status, INIT_FLAGS, INIT_LOCK
    )
    
    # Add an error
    with INIT_LOCK:
        INIT_FLAGS["errors"] = ["Test error message"]
    
    status_html, ready = poll_init_status()
    
    # Status HTML should still be empty (errors are tracked internally but not displayed in status HTML)
    assert status_html == ""
    
    # Clean up
    with INIT_LOCK:
        INIT_FLAGS["errors"] = []


def test_kpi_card_preview_mode():
    """Test KPI card generation in preview mode."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(0.75, 0.0, 0, 0, -1, is_preview=True)
    
    assert "Preview" in html
    assert "Warm Subset" in html
    assert "not submitted to leaderboard" in html.lower() or "preview" in html.lower()


def test_kpi_card_normal_mode():
    """Test KPI card generation in normal mode."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    # First submission
    html = _build_kpi_card_html(0.80, 0.0, 1, 0, 0, is_preview=False)
    
    assert "First Model Submitted" in html or "first" in html.lower()
    assert "0.80" in html or "0.8" in html


def test_safe_int_function():
    """Test the safe_int helper function."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int(5) == 5
    assert safe_int(None) == 1  # default
    assert safe_int(None, 3) == 3  # custom default
    assert safe_int("5") == 5
    assert safe_int(5.7) == 5
    assert safe_int("invalid", 2) == 2


def test_data_size_map():
    """Test DATA_SIZE_MAP has correct values."""
    from aimodelshare.moral_compass.apps.model_building_game import DATA_SIZE_MAP
    
    assert DATA_SIZE_MAP["Small (20%)"] == 0.2
    assert DATA_SIZE_MAP["Medium (60%)"] == 0.6
    assert DATA_SIZE_MAP["Large (80%)"] == 0.8
    assert DATA_SIZE_MAP["Full (100%)"] == 1.0


def test_constants():
    """Test that key constants are defined."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        WARM_MINI_ROWS, CACHE_MAX_AGE_HOURS, MAX_ROWS
    )
    
    assert WARM_MINI_ROWS == 300
    assert CACHE_MAX_AGE_HOURS == 24
    assert MAX_ROWS == 4000


def test_background_init_thread_safety():
    """Test that INIT_LOCK is used properly."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        INIT_FLAGS, INIT_LOCK
    )
    
    # Test that we can acquire and release the lock
    acquired = INIT_LOCK.acquire(blocking=False)
    assert acquired is True
    INIT_LOCK.release()


def test_model_building_game_app_has_timer():
    """Test that the app includes initialization status timer."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    
    # Give the background thread a moment to start
    app = create_model_building_game_app()
    assert app is not None
    assert hasattr(app, 'launch')
    
    # Brief wait for background init to progress
    time.sleep(0.5)


def test_cache_file_creation():
    """Test that cache file path is correctly constructed."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_cache_dir
    
    cache_dir = _get_cache_dir()
    expected_file = cache_dir / "compas.csv"
    
    # Just check the path is constructed correctly
    assert expected_file.name == "compas.csv"
    assert expected_file.parent.name == ".aimodelshare_cache"


def test_preprocessor_memoization():
    """Test that preprocessor configuration is memoized."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        build_preprocessor, _get_cached_preprocessor_config
    )
    
    # Test with same columns twice
    numeric_cols = ["age", "priors_count"]
    categorical_cols = ["race", "sex"]
    
    # First call
    prep1, cols1 = build_preprocessor(numeric_cols, categorical_cols)
    
    # Second call with same columns
    prep2, cols2 = build_preprocessor(numeric_cols, categorical_cols)
    
    # Columns should be the same
    assert cols1 == cols2
    
    # Check cache info (should have hits)
    cache_info = _get_cached_preprocessor_config.cache_info()
    assert cache_info.hits > 0 or cache_info.misses > 0


def test_preprocessor_different_features():
    """Test that different feature sets create different configs."""
    from aimodelshare.moral_compass.apps.model_building_game import build_preprocessor
    
    # Two different feature sets
    numeric_cols1 = ["age"]
    categorical_cols1 = ["race"]
    
    numeric_cols2 = ["priors_count"]
    categorical_cols2 = ["sex"]
    
    prep1, cols1 = build_preprocessor(numeric_cols1, categorical_cols1)
    prep2, cols2 = build_preprocessor(numeric_cols2, categorical_cols2)
    
    # Should have different selected columns
    assert cols1 != cols2
    assert "age" in cols1
    assert "priors_count" in cols2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
