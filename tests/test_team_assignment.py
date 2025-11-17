#!/usr/bin/env python3
"""
Unit tests for team assignment logic in Model Building Game.

Tests the new team persistence feature:
- get_or_assign_team function
- Team recovery from leaderboard
- Random team assignment for new users
- Error handling in team assignment

Run with: pytest tests/test_team_assignment.py -v
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
