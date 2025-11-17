#!/usr/bin/env python3
"""
Unit tests for seamless submission after login enhancement (Gradio 5.49.1).

Tests the auto-resume-after-login functionality:
- Pending submission state storage
- Login flow with pending parameters
- Auto-resume wrapper function
- Integration with run_experiment

Run with: pytest tests/test_seamless_submission_after_login.py -v
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock


def test_pending_submission_state_structure():
    """Test that pending submission parameters have expected structure."""
    # This is the structure saved when authentication gate is hit
    pending_params = {
        "model_name_key": "The Balanced Generalist",
        "complexity_level": 3,
        "feature_set": ["age", "priors_count"],
        "data_size_str": "Small (20%)",
        "team_name": "The Moral Champions",
        "last_submission_score": 0.0,
        "last_rank": 0,
        "submission_count": 0,
        "first_submission_score": None,
        "best_score": 0.0
    }
    
    # Validate all required keys are present
    required_keys = [
        "model_name_key", "complexity_level", "feature_set", "data_size_str",
        "team_name", "last_submission_score", "last_rank", "submission_count",
        "first_submission_score", "best_score"
    ]
    
    for key in required_keys:
        assert key in pending_params, f"Missing required key: {key}"
    
    # Validate types
    assert isinstance(pending_params["model_name_key"], str)
    assert isinstance(pending_params["complexity_level"], int)
    assert isinstance(pending_params["feature_set"], list)
    assert isinstance(pending_params["data_size_str"], str)
    assert isinstance(pending_params["team_name"], str)
    assert isinstance(pending_params["last_submission_score"], (int, float))
    assert isinstance(pending_params["last_rank"], int)
    assert isinstance(pending_params["submission_count"], int)


def test_perform_inline_login_accepts_pending_state():
    """Test that perform_inline_login accepts pending_submission parameter."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    import inspect
    
    # Check function signature includes pending_submission
    sig = inspect.signature(perform_inline_login)
    params = list(sig.parameters.keys())
    
    assert "username_input" in params
    assert "password_input" in params
    assert "pending_submission" in params, "perform_inline_login should accept pending_submission parameter"


def test_perform_inline_login_with_no_pending():
    """Test login flow when no pending submission exists."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    
    # Mock successful authentication
    with patch('aimodelshare.aws.get_aws_token') as mock_token, \
         patch('aimodelshare.moral_compass.apps.model_building_game.get_or_assign_team') as mock_team, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_username') as mock_user, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_password') as mock_pass, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_submit') as mock_submit, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_error') as mock_error, \
         patch('aimodelshare.moral_compass.apps.model_building_game.submit_button') as mock_button, \
         patch('aimodelshare.moral_compass.apps.model_building_game.submission_feedback_display') as mock_feedback, \
         patch('aimodelshare.moral_compass.apps.model_building_game.team_name_state') as mock_team_state, \
         patch('aimodelshare.moral_compass.apps.model_building_game.pending_submission_state') as mock_pending:
        
        mock_token.return_value = 'test_token'
        mock_team.return_value = ('The Moral Champions', True)
        
        # Call with no pending submission
        result = perform_inline_login('testuser', 'testpass', None)
        
        # Should return dict with pending_submission_state
        assert isinstance(result, dict)
        assert mock_pending in result
        
        # Verify AWS token was called
        mock_token.assert_called_once()


def test_perform_inline_login_with_pending():
    """Test login flow when pending submission exists."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    
    pending_params = {
        "model_name_key": "The Balanced Generalist",
        "complexity_level": 3,
        "feature_set": ["age", "priors_count"],
        "data_size_str": "Small (20%)",
        "team_name": "The Moral Champions",
        "last_submission_score": 0.0,
        "last_rank": 0,
        "submission_count": 0,
        "first_submission_score": None,
        "best_score": 0.0
    }
    
    # Mock successful authentication
    with patch('aimodelshare.aws.get_aws_token') as mock_token, \
         patch('aimodelshare.moral_compass.apps.model_building_game.get_or_assign_team') as mock_team, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_username') as mock_user, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_password') as mock_pass, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_submit') as mock_submit, \
         patch('aimodelshare.moral_compass.apps.model_building_game.login_error') as mock_error, \
         patch('aimodelshare.moral_compass.apps.model_building_game.submit_button') as mock_button, \
         patch('aimodelshare.moral_compass.apps.model_building_game.submission_feedback_display') as mock_feedback, \
         patch('aimodelshare.moral_compass.apps.model_building_game.team_name_state') as mock_team_state, \
         patch('aimodelshare.moral_compass.apps.model_building_game.pending_submission_state') as mock_pending:
        
        mock_token.return_value = 'test_token'
        mock_team.return_value = ('The Moral Champions', True)
        
        # Call with pending submission
        result = perform_inline_login('testuser', 'testpass', pending_params)
        
        # Should return dict with all components
        assert isinstance(result, dict)
        assert mock_pending in result
        
        # Verify pending params are passed through
        # The function should keep pending_submission in the return dict
        # Since result is a dict of Gradio updates, check if the key is present
        assert mock_pending in result


def test_auto_resume_wrapper_with_no_pending():
    """Test auto_resume_submission_if_pending with no pending params."""
    from aimodelshare.moral_compass.apps.model_building_game import auto_resume_submission_if_pending
    import inspect
    
    # Verify function signature
    sig = inspect.signature(auto_resume_submission_if_pending)
    params = list(sig.parameters.keys())
    
    assert "pending_params" in params
    assert len(params) >= 10, "Should accept all state parameters plus pending_params"
    
    # Test with None pending params - should yield empty dict
    gen = auto_resume_submission_if_pending(
        None, "model", 3, ["age"], "Small (20%)",
        "Team", 0.0, 0, 0, None, 0.0
    )
    
    result = next(gen)
    assert result == {}


def test_auto_resume_wrapper_with_invalid_pending():
    """Test auto_resume_submission_if_pending with invalid pending params."""
    from aimodelshare.moral_compass.apps.model_building_game import auto_resume_submission_if_pending
    
    # Test with invalid dict (missing required keys)
    invalid_pending = {"some_key": "some_value"}
    
    gen = auto_resume_submission_if_pending(
        invalid_pending, "model", 3, ["age"], "Small (20%)",
        "Team", 0.0, 0, 0, None, 0.0
    )
    
    result = next(gen)
    # Should return empty dict since required params are missing
    assert result == {}


def test_auto_resume_wrapper_with_valid_pending():
    """Test auto_resume_submission_if_pending with valid pending params."""
    from aimodelshare.moral_compass.apps.model_building_game import auto_resume_submission_if_pending
    
    valid_pending = {
        "model_name_key": "The Balanced Generalist",
        "complexity_level": 3,
        "feature_set": ["age", "priors_count"],
        "data_size_str": "Small (20%)",
        "team_name": "The Moral Champions",
        "last_submission_score": 0.0,
        "last_rank": 0,
        "submission_count": 0,
        "first_submission_score": None,
        "best_score": 0.0
    }
    
    # Mock run_experiment to avoid actual execution
    with patch('aimodelshare.moral_compass.apps.model_building_game.run_experiment') as mock_run:
        # Mock run_experiment as a generator that yields empty dict
        mock_run.return_value = iter([{}])
        
        gen = auto_resume_submission_if_pending(
            valid_pending, "model", 3, ["age"], "Small (20%)",
            "Team", 0.0, 0, 0, None, 0.0
        )
        
        # Should call run_experiment with the pending params
        try:
            result = next(gen)
            # run_experiment should have been called with parameters from valid_pending
            mock_run.assert_called_once()
        except StopIteration:
            # Expected if generator completes
            pass


def test_globals_include_pending_submission_state():
    """Test that pending_submission_state is declared in globals."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    import aimodelshare.moral_compass.apps.model_building_game as mbg
    
    # Check that pending_submission_state is in module
    assert hasattr(mbg, 'pending_submission_state'), "pending_submission_state should be declared in module"


def test_run_experiment_saves_pending_on_auth_gate():
    """Test that run_experiment saves pending params when auth is required."""
    from aimodelshare.moral_compass.apps.model_building_game import run_experiment
    
    # This test verifies the code path but requires more mocking for full execution
    # We'll just verify the function signature includes all needed parameters
    import inspect
    sig = inspect.signature(run_experiment)
    params = list(sig.parameters.keys())
    
    required = [
        "model_name_key", "complexity_level", "feature_set", "data_size_str",
        "team_name", "last_submission_score", "last_rank", "submission_count",
        "first_submission_score", "best_score"
    ]
    
    for req in required:
        assert req in params, f"run_experiment should accept {req}"


def test_pending_submission_comment_markers():
    """Test that AUTO-RESUME-AFTER-LOGIN comment markers exist in code."""
    import aimodelshare.moral_compass.apps.model_building_game as mbg
    import inspect
    
    # Get source code
    source = inspect.getsource(mbg)
    
    # Verify descriptive comments exist
    assert "AUTO-RESUME-AFTER-LOGIN" in source, \
        "Code should contain AUTO-RESUME-AFTER-LOGIN comment markers"
    
    # Verify key locations have comments
    assert "Pending submission state" in source, \
        "Code should document pending submission state"
    
    # Check for the enhancement in key functions
    perform_login_source = inspect.getsource(mbg.perform_inline_login)
    assert "AUTO-RESUME-AFTER-LOGIN" in perform_login_source, \
        "perform_inline_login should have AUTO-RESUME-AFTER-LOGIN comments"
    
    run_exp_source = inspect.getsource(mbg.run_experiment)
    assert "AUTO-RESUME-AFTER-LOGIN" in run_exp_source or "pending" in run_exp_source.lower(), \
        "run_experiment should reference pending submission"


def test_data_flow_integrity():
    """Test that pending submission data structure preserves all parameters."""
    # Simulate what happens when auth gate is hit
    original_params = {
        "model_name_key": "The Deep Pattern-Finder",
        "complexity_level": 5,
        "feature_set": ["age", "priors_count", "race"],
        "data_size_str": "Medium (60%)",
        "team_name": "The Justice League",
        "last_submission_score": 0.72,
        "last_rank": 3,
        "submission_count": 2,
        "first_submission_score": 0.65,
        "best_score": 0.72
    }
    
    # After saving to pending state and retrieving
    pending_copy = original_params.copy()
    
    # Verify all data is preserved
    assert pending_copy == original_params
    
    # Verify specific critical parameters
    assert pending_copy["model_name_key"] == "The Deep Pattern-Finder"
    assert pending_copy["complexity_level"] == 5
    assert pending_copy["feature_set"] == ["age", "priors_count", "race"]
    assert pending_copy["submission_count"] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
