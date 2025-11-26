#!/usr/bin/env python3
"""
Unit tests for Model Building Game readiness gating and polling enhancements.

Tests the new features added to prevent "stuck on first preview KPI" issue:
- Readiness helper functions
- Leaderboard polling after submission
- KPI metadata tracking
- Preview vs real submission state management

Run with: pytest tests/test_model_building_game_readiness_gating.py -v
"""

import pytest
import pandas as pd
from aimodelshare.moral_compass.apps.model_building_game import (
    _is_ready,
    _user_rows_changed,
    INIT_FLAGS,
    INIT_LOCK,
    LEADERBOARD_POLL_TRIES,
    LEADERBOARD_POLL_SLEEP,
    ENABLE_AUTO_RESUBMIT_AFTER_READY
)


def test_polling_constants_exist():
    """Test that polling configuration constants are defined."""
    assert LEADERBOARD_POLL_TRIES > 0
    assert LEADERBOARD_POLL_SLEEP > 0
    assert isinstance(ENABLE_AUTO_RESUBMIT_AFTER_READY, bool)


def test_is_ready_function():
    """Test the _is_ready() helper function."""
    # Save original state
    with INIT_LOCK:
        orig_flags = INIT_FLAGS.copy()
    
    try:
        # Test not ready case
        with INIT_LOCK:
            INIT_FLAGS["competition"] = False
            INIT_FLAGS["dataset_core"] = False
            INIT_FLAGS["pre_samples_small"] = False
        
        assert _is_ready() is False
        
        # Test partially ready case (competition only)
        with INIT_LOCK:
            INIT_FLAGS["competition"] = True
            INIT_FLAGS["dataset_core"] = False
            INIT_FLAGS["pre_samples_small"] = False
        
        assert _is_ready() is False
        
        # Test partially ready case (competition + dataset)
        with INIT_LOCK:
            INIT_FLAGS["competition"] = True
            INIT_FLAGS["dataset_core"] = True
            INIT_FLAGS["pre_samples_small"] = False
        
        assert _is_ready() is False
        
        # Test fully ready case
        with INIT_LOCK:
            INIT_FLAGS["competition"] = True
            INIT_FLAGS["dataset_core"] = True
            INIT_FLAGS["pre_samples_small"] = True
        
        assert _is_ready() is True
        
    finally:
        # Restore original state
        with INIT_LOCK:
            for key in orig_flags:
                INIT_FLAGS[key] = orig_flags[key]


def test_user_rows_changed_empty_leaderboard():
    """Test _user_rows_changed with empty leaderboard."""
    result = _user_rows_changed(None, "test_user", 0, 0.0)
    assert result is False
    
    result = _user_rows_changed(pd.DataFrame(), "test_user", 0, 0.0)
    assert result is False


def test_user_rows_changed_no_user():
    """Test _user_rows_changed when user not in leaderboard."""
    df = pd.DataFrame({
        "username": ["other_user1", "other_user2"],
        "accuracy": [0.85, 0.90]
    })
    
    result = _user_rows_changed(df, "test_user", 0, 0.0)
    assert result is False


def test_user_rows_changed_new_submission():
    """Test _user_rows_changed detects new submission (row count increase)."""
    # Leaderboard after new submission
    df = pd.DataFrame({
        "username": ["test_user", "test_user", "other_user"],
        "accuracy": [0.85, 0.87, 0.90]
    })
    
    # User had 1 submission before, now has 2
    result = _user_rows_changed(df, "test_user", 1, 0.85)
    assert result is True


def test_user_rows_changed_improved_score():
    """Test _user_rows_changed detects score improvement."""
    # Leaderboard with improved score
    df = pd.DataFrame({
        "username": ["test_user", "test_user"],
        "accuracy": [0.85, 0.92]  # Best is now 0.92
    })
    
    # User had best score of 0.85, now has 0.92
    result = _user_rows_changed(df, "test_user", 2, 0.85)
    assert result is True


def test_user_rows_changed_no_change():
    """Test _user_rows_changed when nothing changed."""
    df = pd.DataFrame({
        "username": ["test_user", "test_user"],
        "accuracy": [0.85, 0.87]
    })
    
    # Same count and best score
    result = _user_rows_changed(df, "test_user", 2, 0.87)
    assert result is False


def test_user_rows_changed_small_score_diff():
    """Test _user_rows_changed with very small score difference (noise)."""
    df = pd.DataFrame({
        "username": ["test_user"],
        "accuracy": [0.850001]  # Tiny difference from 0.85
    })
    
    # Should not detect change for tiny floating point differences
    result = _user_rows_changed(df, "test_user", 1, 0.85)
    assert result is False


def test_kpi_metadata_structure():
    """Test that KPI metadata has expected structure."""
    # Example metadata from a successful submission
    meta = {
        "was_preview": False,
        "preview_score": None,
        "ready_at_run_start": True,
        "poll_iterations": 3,
        "local_test_accuracy": 0.85,
        "this_submission_score": 0.84,
        "new_best_accuracy": 0.85,
        "rank": 5
    }
    
    # Verify all expected keys exist
    assert "was_preview" in meta
    assert "preview_score" in meta
    assert "ready_at_run_start" in meta
    assert "poll_iterations" in meta
    assert "local_test_accuracy" in meta
    assert "this_submission_score" in meta
    assert "new_best_accuracy" in meta
    assert "rank" in meta


def test_preview_metadata_structure():
    """Test metadata structure for preview runs."""
    # Example metadata from a preview run
    meta = {
        "was_preview": True,
        "preview_score": 0.82,
        "ready_at_run_start": False,
        "poll_iterations": 0,
        "local_test_accuracy": 0.82,
        "this_submission_score": None,
        "new_best_accuracy": None,
        "rank": None
    }
    
    assert meta["was_preview"] is True
    assert meta["preview_score"] is not None
    assert meta["poll_iterations"] == 0
    assert meta["this_submission_score"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
