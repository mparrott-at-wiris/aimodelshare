#!/usr/bin/env python3
"""
Unit tests for KPI card improvements and change detection.

Tests the new functionality:
- _get_user_latest_accuracy() helper
- Enhanced _user_rows_changed() with latest accuracy detection
- Provisional diff display in pending KPI cards

Run with: pytest tests/test_kpi_improvements.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def test_get_user_latest_accuracy_with_timestamps():
    """Test that _get_user_latest_accuracy uses timestamp sorting when available."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_user_latest_accuracy
    
    # Create test data with timestamps
    now = datetime.now()
    df = pd.DataFrame({
        'username': ['user1', 'user1', 'user1', 'user2'],
        'accuracy': [0.75, 0.80, 0.78, 0.85],
        'timestamp': [
            (now - timedelta(hours=2)).isoformat(),
            (now - timedelta(hours=1)).isoformat(),
            now.isoformat(),  # Latest timestamp
            now.isoformat()
        ]
    })
    
    # Should return 0.78 (latest by timestamp, not max)
    result = _get_user_latest_accuracy(df, 'user1')
    assert result is not None
    assert abs(result - 0.78) < 0.0001


def test_get_user_latest_accuracy_without_timestamps():
    """Test that _get_user_latest_accuracy falls back to last row when no timestamps."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_user_latest_accuracy
    
    # Create test data without timestamps
    df = pd.DataFrame({
        'username': ['user1', 'user1', 'user1', 'user2'],
        'accuracy': [0.75, 0.80, 0.78, 0.85]
    })
    
    # Should return 0.78 (last row for user1)
    result = _get_user_latest_accuracy(df, 'user1')
    assert result is not None
    assert abs(result - 0.78) < 0.0001


def test_get_user_latest_accuracy_no_user():
    """Test that _get_user_latest_accuracy returns None for non-existent user."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_user_latest_accuracy
    
    df = pd.DataFrame({
        'username': ['user1', 'user2'],
        'accuracy': [0.75, 0.85]
    })
    
    result = _get_user_latest_accuracy(df, 'user3')
    assert result is None


def test_get_user_latest_accuracy_empty_df():
    """Test that _get_user_latest_accuracy returns None for empty DataFrame."""
    from aimodelshare.moral_compass.apps.model_building_game import _get_user_latest_accuracy
    
    df = pd.DataFrame()
    result = _get_user_latest_accuracy(df, 'user1')
    assert result is None


def test_user_rows_changed_by_latest_accuracy():
    """Test that _user_rows_changed detects changes in latest accuracy (overwrite case)."""
    from aimodelshare.moral_compass.apps.model_building_game import _user_rows_changed
    
    # Create initial leaderboard
    now = datetime.now()
    df_old = pd.DataFrame({
        'username': ['user1'],
        'accuracy': [0.75],
        'timestamp': [now.isoformat()]
    })
    
    # Create updated leaderboard - same row count, same best, but different latest accuracy
    # (simulates backend overwrite)
    df_new = pd.DataFrame({
        'username': ['user1'],
        'accuracy': [0.80],  # Updated accuracy
        'timestamp': [(now + timedelta(seconds=1)).isoformat()]
    })
    
    # Extract old values
    old_row_count = 1
    old_best_score = 0.75
    old_latest_ts = now.timestamp()
    old_latest_score = 0.75
    
    # Should detect change due to different latest accuracy
    changed = _user_rows_changed(
        df_new, 
        'user1', 
        old_row_count, 
        old_best_score, 
        old_latest_ts, 
        old_latest_score
    )
    
    assert changed is True


def test_user_rows_changed_no_change():
    """Test that _user_rows_changed returns False when nothing changed."""
    from aimodelshare.moral_compass.apps.model_building_game import _user_rows_changed
    
    now = datetime.now()
    df = pd.DataFrame({
        'username': ['user1'],
        'accuracy': [0.75],
        'timestamp': [now.isoformat()]
    })
    
    # Same values
    changed = _user_rows_changed(
        df, 
        'user1', 
        1,  # old_row_count
        0.75,  # old_best_score
        now.timestamp(),  # old_latest_ts
        0.75  # old_latest_score
    )
    
    assert changed is False


def test_user_rows_changed_by_count():
    """Test that _user_rows_changed detects row count increase."""
    from aimodelshare.moral_compass.apps.model_building_game import _user_rows_changed
    
    now = datetime.now()
    df = pd.DataFrame({
        'username': ['user1', 'user1'],
        'accuracy': [0.75, 0.80],
        'timestamp': [now.isoformat(), (now + timedelta(seconds=1)).isoformat()]
    })
    
    # Old state had 1 row, new has 2
    changed = _user_rows_changed(
        df, 
        'user1', 
        1,  # old_row_count
        0.75,  # old_best_score
        now.timestamp(),  # old_latest_ts
        0.75  # old_latest_score
    )
    
    assert changed is True


def test_user_rows_changed_by_best_score():
    """Test that _user_rows_changed detects best score improvement."""
    from aimodelshare.moral_compass.apps.model_building_game import _user_rows_changed
    
    now = datetime.now()
    df = pd.DataFrame({
        'username': ['user1', 'user1'],
        'accuracy': [0.75, 0.85],  # New best: 0.85
        'timestamp': [now.isoformat(), (now + timedelta(seconds=1)).isoformat()]
    })
    
    changed = _user_rows_changed(
        df, 
        'user1', 
        2,  # old_row_count (same)
        0.80,  # old_best_score (now improved to 0.85)
        now.timestamp(),
        0.75
    )
    
    assert changed is True


def test_build_kpi_card_pending_with_provisional_diff_increase():
    """Test that pending KPI card shows provisional increase diff."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(
        new_score=0.80,  # Local test accuracy (new)
        last_score=0.75,  # Last submission score (old)
        new_rank=0,
        last_rank=0,
        submission_count=0,
        is_preview=False,
        is_pending=True,
        local_test_accuracy=0.80
    )
    
    # Should contain pending title
    assert "⏳ Submission Processing" in html
    
    # Should show the accuracy
    assert "80.00%" in html
    
    # Should show provisional increase
    assert "+5.00" in html or "+5" in html
    assert "⬆️" in html
    assert "(Provisional)" in html
    
    # Should show pending rank
    assert "Pending" in html
    assert "Calculating rank" in html


def test_build_kpi_card_pending_with_provisional_diff_decrease():
    """Test that pending KPI card shows provisional decrease diff."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(
        new_score=0.70,  # Local test accuracy (new)
        last_score=0.75,  # Last submission score (old)
        new_rank=0,
        last_rank=0,
        submission_count=0,
        is_preview=False,
        is_pending=True,
        local_test_accuracy=0.70
    )
    
    # Should show provisional decrease
    assert "-5.00" in html or "-5" in html
    assert "⬇️" in html
    assert "(Provisional)" in html


def test_build_kpi_card_pending_with_provisional_diff_no_change():
    """Test that pending KPI card shows 'No Change' when scores match."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(
        new_score=0.75,  # Same as last
        last_score=0.75,
        new_rank=0,
        last_rank=0,
        submission_count=0,
        is_preview=False,
        is_pending=True,
        local_test_accuracy=0.75
    )
    
    # Should show no change
    assert "No Change" in html
    assert "↔" in html
    assert "(Provisional)" in html


def test_build_kpi_card_pending_no_last_score():
    """Test that pending KPI card handles missing last score gracefully."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(
        new_score=0.75,
        last_score=None,  # No previous score
        new_rank=0,
        last_rank=0,
        submission_count=0,
        is_preview=False,
        is_pending=True,
        local_test_accuracy=0.75
    )
    
    # Should show accuracy but no diff (just pending message)
    assert "75.00%" in html
    assert "Pending leaderboard update" in html
    # When no last score, should NOT show provisional diff
    # (it only shows "Pending leaderboard update..." without provisional annotation)
    assert "(Provisional)" not in html


def test_build_kpi_card_success_shows_diff():
    """Test that success KPI card shows actual diff (not provisional)."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_kpi_card_html
    
    html = _build_kpi_card_html(
        new_score=0.80,
        last_score=0.75,
        new_rank=3,
        last_rank=5,
        submission_count=1,
        is_preview=False,
        is_pending=False,
        local_test_accuracy=None
    )
    
    # Should show increase
    assert "+5.00" in html or "+5" in html
    assert "⬆️" in html
    
    # Should NOT be provisional
    assert "(Provisional)" not in html
    
    # Should show rank improvement
    assert "#3" in html
    assert "Moved up" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
