#!/usr/bin/env python3
"""
Tests for Bias Detective combined score and zero-score tied-last ranking.

These tests verify that:
1. _calculate_combined_score computes correctly
2. _enforce_zero_tied_last_rank enforces last-place semantics when combined score and ethical progress are both zero
3. _compute_user_stats applies zero-score enforcement correctly
4. Team ranks are based on average accuracy (not max)

Run with: pytest tests/test_bias_detective_combined_score.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

# Import functions to test
from aimodelshare.moral_compass.apps.bias_detective import (
    _calculate_combined_score,
    _enforce_zero_tied_last_rank,
    _compute_user_stats,
    _user_stats_cache,
)


def test_calculate_combined_score():
    """Test _calculate_combined_score helper function."""
    # Test basic calculation
    # combined = accuracy × (ethical_progress_pct / 100) × 100
    # ethical_progress_pct = (tasks_completed / max_points) × 100
    
    # Case 1: accuracy=0.92, tasks_completed=10, max_points=21
    # ethical_progress_pct = (10/21) * 100 = 47.619...
    # combined = 0.92 * (47.619/100) * 100 = 43.81...
    result1 = _calculate_combined_score(0.92, 10, 21)
    assert abs(result1 - 43.81) < 0.1, f"Expected ~43.81, got {result1}"
    
    # Case 2: Zero tasks completed
    result2 = _calculate_combined_score(0.92, 0, 21)
    assert result2 == 0.0, f"Expected 0.0 with zero tasks, got {result2}"
    
    # Case 3: All tasks completed
    result3 = _calculate_combined_score(0.92, 21, 21)
    assert abs(result3 - 92.0) < 0.1, f"Expected 92.0 with all tasks, got {result3}"
    
    # Case 4: Max points is zero (edge case)
    result4 = _calculate_combined_score(0.92, 5, 0)
    assert result4 == 0.0, f"Expected 0.0 with max_points=0, got {result4}"
    
    # Case 5: Tasks exceed max (should cap at 100%)
    result5 = _calculate_combined_score(0.92, 25, 21)
    assert abs(result5 - 92.0) < 0.1, f"Expected 92.0 (capped), got {result5}"


def test_enforce_zero_tied_last_rank_both_zero():
    """Test _enforce_zero_tied_last_rank when both combined and ethical progress are zero."""
    # When combined score and ethical progress are both zero, should enforce tied-last
    user_rank, team_rank = _enforce_zero_tied_last_rank(
        combined_score=0.0,
        ethical_progress_pct=0.0,
        user_rank=None,
        team_rank=None,
        total_individuals=10,
        total_teams=5
    )
    
    assert user_rank == 10, f"Expected user_rank=10 (last place), got {user_rank}"
    assert team_rank == 5, f"Expected team_rank=5 (last place), got {team_rank}"


def test_enforce_zero_tied_last_rank_non_zero_combined():
    """Test _enforce_zero_tied_last_rank when combined score is non-zero."""
    # When combined score is non-zero, should NOT enforce tied-last
    user_rank, team_rank = _enforce_zero_tied_last_rank(
        combined_score=43.81,
        ethical_progress_pct=47.6,
        user_rank=3,
        team_rank=2,
        total_individuals=10,
        total_teams=5
    )
    
    # Ranks should remain unchanged
    assert user_rank == 3, f"Expected user_rank=3 (unchanged), got {user_rank}"
    assert team_rank == 2, f"Expected team_rank=2 (unchanged), got {team_rank}"


def test_enforce_zero_tied_last_rank_non_zero_ethical():
    """Test _enforce_zero_tied_last_rank when ethical progress is non-zero."""
    # When ethical progress is non-zero, should NOT enforce tied-last
    # even if combined score is zero (can happen with zero accuracy)
    user_rank, team_rank = _enforce_zero_tied_last_rank(
        combined_score=0.0,
        ethical_progress_pct=47.6,
        user_rank=3,
        team_rank=2,
        total_individuals=10,
        total_teams=5
    )
    
    # Ranks should remain unchanged
    assert user_rank == 3, f"Expected user_rank=3 (unchanged), got {user_rank}"
    assert team_rank == 2, f"Expected team_rank=2 (unchanged), got {team_rank}"


def test_compute_user_stats_uses_average_for_team_rank():
    """Test that _compute_user_stats uses average accuracy for team ranking."""
    # Mock leaderboard data with multiple teams
    mock_df = pd.DataFrame([
        {"username": "alice", "accuracy": 0.95, "Team": "Team A"},
        {"username": "bob", "accuracy": 0.85, "Team": "Team A"},
        {"username": "charlie", "accuracy": 0.90, "Team": "Team B"},
        {"username": "dave", "accuracy": 0.80, "Team": "Team B"},
    ])
    
    # Team A average: (0.95 + 0.85) / 2 = 0.90
    # Team B average: (0.90 + 0.80) / 2 = 0.85
    # So Team A should rank #1
    
    with patch('aimodelshare.moral_compass.apps.bias_detective._fetch_leaderboard') as mock_fetch:
        mock_fetch.return_value = mock_df
        
        stats = _compute_user_stats("bob", "fake-token")
        
        # Bob is on Team A, which should rank #1
        assert stats["team_name"] == "Team A"
        assert stats["team_rank"] == 1, f"Expected team_rank=1 for Team A, got {stats['team_rank']}"


def test_compute_user_stats_applies_zero_score_enforcement():
    """Test that _compute_user_stats applies zero-score tied-last enforcement."""
    # Clear cache to avoid flakiness
    _user_stats_cache.clear()
    
    # Mock leaderboard with multiple users
    mock_df = pd.DataFrame([
        {"username": "alice", "accuracy": 0.95, "Team": "Team A"},
        {"username": "bob", "accuracy": 0.85, "Team": "Team B"},
        {"username": "charlie", "accuracy": 0.92, "Team": "Team C"},
    ])
    
    with patch('aimodelshare.moral_compass.apps.bias_detective._fetch_leaderboard') as mock_fetch:
        with patch('aimodelshare.moral_compass.apps.bias_detective.random.choice', return_value="Team B"):
            mock_fetch.return_value = mock_df
            
            # For a new user with 0 tasks completed, the zero-score guard should apply
            # in _compute_user_stats since it assumes tasks_completed=0
            stats = _compute_user_stats("bob", "fake-token")
            
            # With zero tasks completed, combined score = 0.85 * 0 * 100 = 0
            # Zero-score guard should set rank to last place (total_individuals)
            assert stats["rank"] == stats["total_individuals"], \
                f"Expected rank={stats['total_individuals']} (tied-last) for zero tasks, got {stats['rank']}"
            assert stats["total_individuals"] == 3
            assert stats["total_teams"] == 3


def test_compute_user_stats_counts_total_individuals_and_teams():
    """Test that _compute_user_stats correctly counts total individuals and teams."""
    # Mock leaderboard with specific counts
    mock_df = pd.DataFrame([
        {"username": "user1", "accuracy": 0.95, "Team": "Team A"},
        {"username": "user2", "accuracy": 0.90, "Team": "Team A"},
        {"username": "user3", "accuracy": 0.85, "Team": "Team B"},
        {"username": "user4", "accuracy": 0.80, "Team": "Team C"},
        {"username": "user5", "accuracy": 0.75, "Team": "Team C"},
    ])
    
    with patch('aimodelshare.moral_compass.apps.bias_detective._fetch_leaderboard') as mock_fetch:
        mock_fetch.return_value = mock_df
        
        stats = _compute_user_stats("user3", "fake-token")
        
        assert stats["total_individuals"] == 5, f"Expected 5 individuals, got {stats['total_individuals']}"
        assert stats["total_teams"] == 3, f"Expected 3 teams, got {stats['total_teams']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
