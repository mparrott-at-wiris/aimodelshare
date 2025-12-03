#!/usr/bin/env python3
"""
Integration tests for Bias Detective rank computation from Moral Compass API.

These tests verify that:
1. Ranks are computed from moralCompassScore, not playground leaderboard
2. Ranks update dynamically as tasksCompleted increases
3. Team ranks are computed correctly from teamName grouping

Run with: pytest tests/test_bias_detective_rank_integration.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from aimodelshare.moral_compass.apps.mc_integration_helpers import (
    get_user_ranks,
    fetch_cached_users,
    _leaderboard_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear leaderboard cache before each test."""
    _leaderboard_cache.clear()
    yield
    _leaderboard_cache.clear()


def test_get_user_ranks_computes_from_moral_compass_score():
    """Test that get_user_ranks computes ranks based on moralCompassScore."""
    
    # Mock API response with multiple users
    mock_users = [
        {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10},
        {"username": "bob", "moralCompassScore": 0.85, "submissionCount": 1, "totalCount": 8},
        {"username": "charlie", "moralCompassScore": 0.75, "submissionCount": 1, "totalCount": 6},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        # Get ranks for bob
        result = get_user_ranks("bob", table_id="test-table")
        
        # bob should be rank 2 (after alice)
        assert result["individual_rank"] == 2
        assert result["moral_compass_score"] == 0.85
        assert result["team_rank"] is None  # No team specified


def test_get_user_ranks_updates_when_score_increases():
    """Test that ranks change when a user's moralCompassScore increases."""
    
    # Initial state: bob has lower score than alice
    mock_users_before = [
        {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10},
        {"username": "bob", "moralCompassScore": 0.85, "submissionCount": 1, "totalCount": 8},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users_before, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        # Get bob's rank before update
        result_before = get_user_ranks("bob", table_id="test-table")
        assert result_before["individual_rank"] == 2
        
        # Clear cache to simulate new fetch
        _leaderboard_cache.clear()
        
        # After bob completes more tasks, his score increases
        mock_users_after = [
            {"username": "bob", "moralCompassScore": 0.98, "submissionCount": 2, "totalCount": 12},
            {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10},
        ]
        mock_client.list_users.return_value = {"users": mock_users_after, "lastKey": None}
        
        # Get bob's rank after update
        result_after = get_user_ranks("bob", table_id="test-table")
        assert result_after["individual_rank"] == 1  # bob is now rank 1


def test_get_user_ranks_computes_team_rank():
    """Test that team ranks are computed correctly from teamName grouping."""
    
    # Mock API response with team entries (prefix: team:)
    mock_users = [
        {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10, "teamName": "Team A"},
        {"username": "bob", "moralCompassScore": 0.85, "submissionCount": 1, "totalCount": 8, "teamName": "Team B"},
        {"username": "team:Team A", "moralCompassScore": 0.92, "submissionCount": 1, "totalCount": 9},
        {"username": "team:Team B", "moralCompassScore": 0.88, "submissionCount": 1, "totalCount": 8},
        {"username": "team:Team C", "moralCompassScore": 0.80, "submissionCount": 1, "totalCount": 7},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        # Get ranks for bob with team name
        result = get_user_ranks("bob", table_id="test-table", team_name="Team B")
        
        # bob should be rank 2 individually (after alice)
        assert result["individual_rank"] == 2
        
        # Team B should be rank 2 (after Team A)
        assert result["team_rank"] == 2


def test_get_user_ranks_handles_missing_user():
    """Test that get_user_ranks handles missing user gracefully."""
    
    mock_users = [
        {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        # Get ranks for non-existent user
        result = get_user_ranks("nonexistent", table_id="test-table")
        
        assert result["individual_rank"] is None
        assert result["moral_compass_score"] is None
        assert result["team_rank"] is None


def test_fetch_cached_users_uses_moral_compass_score():
    """Test that fetch_cached_users properly extracts moralCompassScore from API."""
    
    mock_users = [
        {
            "username": "alice",
            "moralCompassScore": 0.95,
            "submissionCount": 1,
            "totalCount": 10,
            "teamName": "Team A"
        },
        {
            "username": "bob",
            "moralCompassScore": 0.85,
            "submissionCount": 1,
            "totalCount": 8,
        },
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        users = fetch_cached_users("test-table", ttl=5)
        
        assert len(users) == 2
        assert users[0]["username"] == "alice"
        assert users[0]["moralCompassScore"] == 0.95
        assert users[0]["teamName"] == "Team A"
        assert users[1]["username"] == "bob"
        assert users[1]["moralCompassScore"] == 0.85
        assert users[1]["teamName"] is None


def test_fetch_cached_users_handles_missing_moral_compass_score():
    """Test that fetch_cached_users falls back to totalCount if moralCompassScore is missing."""
    
    # Old API response format without moralCompassScore
    mock_users = [
        {"username": "alice", "submissionCount": 1, "totalCount": 10},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        users = fetch_cached_users("test-table", ttl=5)
        
        assert len(users) == 1
        assert users[0]["username"] == "alice"
        assert users[0]["moralCompassScore"] == 10  # Fallback to totalCount


def test_fetch_cached_users_caching():
    """Test that fetch_cached_users properly caches results."""
    
    mock_users = [
        {"username": "alice", "moralCompassScore": 0.95, "submissionCount": 1, "totalCount": 10},
    ]
    
    with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_users.return_value = {"users": mock_users, "lastKey": None}
        mock_client_class.return_value = mock_client
        
        # First call should fetch from API
        users1 = fetch_cached_users("test-table", ttl=30)
        assert mock_client.list_users.call_count == 1
        
        # Second call should use cache
        users2 = fetch_cached_users("test-table", ttl=30)
        assert mock_client.list_users.call_count == 1  # Still 1, didn't fetch again
        
        assert users1 == users2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
