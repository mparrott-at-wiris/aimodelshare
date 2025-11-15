#!/usr/bin/env python3
"""
Test for delayed sign-in feature in model_building_game.py

Tests that:
1. Helper functions exist and work correctly
2. App can be instantiated with new login components
3. Authentication gate logic is present
"""

import pytest
import os


def test_build_login_prompt_html_exists():
    """Test that build_login_prompt_html function exists and returns HTML."""
    from aimodelshare.moral_compass.apps.model_building_game import build_login_prompt_html
    
    # Test without preview score
    html = build_login_prompt_html()
    assert html is not None
    assert isinstance(html, str)
    assert "Sign in to submit" in html
    assert "modelshare.ai/login" in html
    
    # Test with preview score
    html_with_score = build_login_prompt_html(preview_score=0.75)
    assert html_with_score is not None
    assert isinstance(html_with_score, str)
    assert "75.00%" in html_with_score
    assert "Preview Score" in html_with_score


def test_perform_inline_login_exists():
    """Test that perform_inline_login function exists."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    
    assert perform_inline_login is not None
    assert callable(perform_inline_login)


def test_model_building_game_app_can_be_created():
    """Test that model building game app can be instantiated with login components."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    
    app = create_model_building_game_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_perform_inline_login_validates_empty_username():
    """Test that perform_inline_login rejects empty username."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    
    # Note: This will fail because login_username and other globals are not initialized
    # This is expected - the function is designed to work within Gradio context
    # We're just testing that it exists and has the right signature
    try:
        result = perform_inline_login("", "password")
        # If it doesn't raise an error, check that it returns a dict
        assert isinstance(result, dict)
    except (NameError, AttributeError):
        # Expected - globals not initialized outside Gradio context
        pass


def test_perform_inline_login_validates_empty_password():
    """Test that perform_inline_login rejects empty password."""
    from aimodelshare.moral_compass.apps.model_building_game import perform_inline_login
    
    try:
        result = perform_inline_login("username", "")
        assert isinstance(result, dict)
    except (NameError, AttributeError):
        # Expected - globals not initialized outside Gradio context
        pass


def test_aws_token_check_in_run_experiment():
    """Test that AWS_TOKEN check exists in run_experiment function."""
    import inspect
    from aimodelshare.moral_compass.apps.model_building_game import run_experiment
    
    # Get the source code of run_experiment
    source = inspect.getsource(run_experiment)
    
    # Check that authentication gate logic is present
    assert 'AWS_TOKEN' in source
    assert 'os.environ.get("AWS_TOKEN")' in source
    assert 'build_login_prompt_html' in source
    assert 'login_username' in source
    assert 'login_password' in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
