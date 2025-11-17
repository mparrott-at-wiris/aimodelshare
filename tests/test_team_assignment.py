#!/usr/bin/env python3
"""
Unit tests for team assignment logic in Model Building Game.

Tests the team persistence and normalization features:
- get_or_assign_team function
- Team recovery from leaderboard with timestamp sorting
- Random team assignment for new users
- Team name normalization (whitespace handling)
- Error handling in team assignment
- Leaderboard highlighting with normalized comparison

Run with: pytest tests/test_team_assignment.py -v
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


def test_get_or_assign_team_new_user():
    """Test that a new user with no leaderboard history gets a random team."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES, playground
    
    # Mock empty leaderboard
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': [],
            'Team': [],
            'accuracy': []
        })
        
        team_name, is_new = get_or_assign_team("new_user_123")
        
        # Should assign a new random team
        assert is_new is True
        assert team_name in TEAM_NAMES
        assert mock_playground.get_leaderboard.called


def test_get_or_assign_team_existing_user():
    """Test that an existing user gets their existing team from leaderboard."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with existing user
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['existing_user', 'other_user'],
            'Team': ['The Moral Champions', 'The Justice League'],
            'accuracy': [0.85, 0.82]
        })
        
        team_name, is_new = get_or_assign_team("existing_user")
        
        # Should return existing team
        assert is_new is False
        assert team_name == 'The Moral Champions'
        assert mock_playground.get_leaderboard.called


def test_get_or_assign_team_user_with_null_team():
    """Test that a user with null team in leaderboard gets a new random team."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES
    
    # Mock leaderboard with user but null team
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['user_with_null_team'],
            'Team': [None],
            'accuracy': [0.75]
        })
        
        team_name, is_new = get_or_assign_team("user_with_null_team")
        
        # Should assign a new random team
        assert is_new is True
        assert team_name in TEAM_NAMES


def test_get_or_assign_team_user_with_empty_team():
    """Test that a user with empty string team gets a new random team."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES
    
    # Mock leaderboard with user but empty team
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['user_with_empty_team'],
            'Team': [''],
            'accuracy': [0.75]
        })
        
        team_name, is_new = get_or_assign_team("user_with_empty_team")
        
        # Should assign a new random team
        assert is_new is True
        assert team_name in TEAM_NAMES


def test_get_or_assign_team_no_team_column():
    """Test that missing Team column in leaderboard triggers fallback."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES
    
    # Mock leaderboard without Team column
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['some_user'],
            'accuracy': [0.80]
        })
        
        team_name, is_new = get_or_assign_team("some_user")
        
        # Should assign a new random team
        assert is_new is True
        assert team_name in TEAM_NAMES


def test_get_or_assign_team_api_error():
    """Test that API errors trigger fallback to random team assignment."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES
    
    # Mock API error
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.side_effect = Exception("API connection failed")
        
        team_name, is_new = get_or_assign_team("any_user")
        
        # Should assign a new random team despite error
        assert is_new is True
        assert team_name in TEAM_NAMES


def test_get_or_assign_team_playground_none():
    """Test that None playground triggers fallback."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team, TEAM_NAMES
    
    # Mock playground as None
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground', None):
        team_name, is_new = get_or_assign_team("user123")
        
        # Should assign a new random team
        assert is_new is True
        assert team_name in TEAM_NAMES


def test_get_or_assign_team_multiple_submissions_same_team():
    """Test that user with multiple submissions gets the most recent team."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with multiple submissions for same user
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['multi_user', 'multi_user', 'multi_user'],
            'Team': ['The Moral Champions', 'The Moral Champions', 'The Moral Champions'],
            'accuracy': [0.80, 0.82, 0.85],
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03']
        })
        
        team_name, is_new = get_or_assign_team("multi_user")
        
        # Should return the existing team
        assert is_new is False
        assert team_name == 'The Moral Champions'


def test_team_names_list_not_empty():
    """Test that TEAM_NAMES is properly defined and not empty."""
    from aimodelshare.moral_compass.apps.model_building_game import TEAM_NAMES
    
    assert isinstance(TEAM_NAMES, list)
    assert len(TEAM_NAMES) > 0
    # Check that all team names are non-empty strings
    for team_name in TEAM_NAMES:
        assert isinstance(team_name, str)
        assert len(team_name) > 0


# ============================================================================
# New Tests for Team Name Normalization and Timestamp-based Recovery
# ============================================================================

def test_normalize_team_name_basic():
    """Test basic team name normalization."""
    from aimodelshare.moral_compass.apps.model_building_game import _normalize_team_name
    
    # Test basic normalization
    assert _normalize_team_name("The Ethical Explorers") == "The Ethical Explorers"
    assert _normalize_team_name("  The Ethical Explorers  ") == "The Ethical Explorers"
    assert _normalize_team_name("The  Moral   Champions") == "The Moral Champions"
    
    # Test empty/None values
    assert _normalize_team_name("") == ""
    assert _normalize_team_name(None) == ""
    assert _normalize_team_name("   ") == ""
    
    # Test with tabs and newlines
    assert _normalize_team_name("The\tEthical\nExplorers") == "The Ethical Explorers"


def test_get_or_assign_team_with_whitespace_variations():
    """Test that team recovery works with whitespace variations in stored data."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with team name that has extra whitespace
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['whitespace_user'],
            'Team': ['  The Ethical Explorers  '],  # Extra whitespace
            'accuracy': [0.85],
            'timestamp': ['2024-01-01']
        })
        
        team_name, is_new = get_or_assign_team("whitespace_user")
        
        # Should return normalized team (whitespace stripped)
        assert is_new is False
        assert team_name == 'The Ethical Explorers'


def test_get_or_assign_team_timestamp_sorting():
    """Test that the most recent team is returned when user has multiple submissions."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with multiple submissions - different timestamps
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['multi_user', 'multi_user', 'multi_user'],
            'Team': ['Old Team 1', 'Old Team 2', 'Most Recent Team'],
            'accuracy': [0.80, 0.82, 0.85],
            'timestamp': ['2024-01-01', '2024-01-02', '2024-01-03']  # Most recent last
        })
        
        team_name, is_new = get_or_assign_team("multi_user")
        
        # Should return the most recent team (timestamp 2024-01-03)
        assert is_new is False
        assert team_name == 'Most Recent Team'


def test_get_or_assign_team_timestamp_sorting_out_of_order():
    """Test timestamp sorting when data is not in chronological order."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with timestamps out of order
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['user_ooo', 'user_ooo', 'user_ooo'],
            'Team': ['Middle Team', 'Oldest Team', 'Newest Team'],
            'accuracy': [0.82, 0.80, 0.85],
            'timestamp': ['2024-01-02', '2024-01-01', '2024-01-03']  # Out of order
        })
        
        team_name, is_new = get_or_assign_team("user_ooo")
        
        # Should return the newest team (timestamp 2024-01-03) despite order
        assert is_new is False
        assert team_name == 'Newest Team'


def test_get_or_assign_team_no_timestamp_column():
    """Test fallback behavior when timestamp column is missing."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard without timestamp column (old data format)
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['legacy_user', 'legacy_user'],
            'Team': ['Team A', 'Team B'],
            'accuracy': [0.80, 0.85]
            # No timestamp column
        })
        
        team_name, is_new = get_or_assign_team("legacy_user")
        
        # Should still return a team (first one found, since no sorting possible)
        assert is_new is False
        assert team_name in ['Team A', 'Team B']


def test_get_or_assign_team_invalid_timestamp():
    """Test resilient handling of invalid timestamp data."""
    from aimodelshare.moral_compass.apps.model_building_game import get_or_assign_team
    
    # Mock leaderboard with invalid timestamp values
    with patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['invalid_ts_user', 'invalid_ts_user'],
            'Team': ['Team X', 'Team Y'],
            'accuracy': [0.80, 0.85],
            'timestamp': ['invalid_date', 'also_invalid']
        })
        
        team_name, is_new = get_or_assign_team("invalid_ts_user")
        
        # Should still return a team despite invalid timestamps
        assert is_new is False
        assert team_name in ['Team X', 'Team Y']


def test_build_team_html_normalized_highlighting():
    """Test that team highlighting works with normalized, case-insensitive comparison."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_team_html
    
    # Create team summary with slightly different formatting
    team_summary = pd.DataFrame({
        'Team': ['The Ethical Explorers', 'The Moral Champions', 'The Justice League'],
        'Best_Score': [0.85, 0.82, 0.80],
        'Avg_Score': [0.83, 0.81, 0.79],
        'Submissions': [5, 4, 3]
    })
    team_summary.index = [1, 2, 3]
    
    # User's team has extra whitespace
    html = _build_team_html(team_summary, "  The Ethical Explorers  ")
    
    # Should highlight the correct row despite whitespace difference
    assert "user-row-highlight" in html
    assert "The Ethical Explorers" in html


def test_build_team_html_case_insensitive():
    """Test that highlighting is case-insensitive."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_team_html
    
    team_summary = pd.DataFrame({
        'Team': ['the ethical explorers', 'The Moral Champions'],  # lowercase
        'Best_Score': [0.85, 0.82],
        'Avg_Score': [0.83, 0.81],
        'Submissions': [5, 4]
    })
    team_summary.index = [1, 2]
    
    # User's team is in different case
    html = _build_team_html(team_summary, "The Ethical Explorers")
    
    # Should still highlight despite case difference
    assert "user-row-highlight" in html


def test_normalized_team_in_environment():
    """Test that normalized team names are stored in environment."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    import os
    
    # Mock the AWS token retrieval (imported inside perform_inline_login) and leaderboard
    with patch('aimodelshare.aws.get_aws_token') as mock_token, \
         patch('aimodelshare.moral_compass.apps.model_building_game.playground') as mock_playground:
        
        mock_token.return_value = "fake_token"
        mock_playground.get_leaderboard.return_value = pd.DataFrame({
            'username': ['test_user'],
            'Team': ['  The Moral Champions  '],  # Extra whitespace
            'accuracy': [0.85],
            'timestamp': ['2024-01-01']
        })
        
        # Perform login
        result = perform_inline_login("test_user", "test_password")
        
        # Check that environment variable is normalized
        assert os.environ.get("TEAM_NAME") == "The Moral Champions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
