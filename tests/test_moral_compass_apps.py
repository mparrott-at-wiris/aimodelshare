#!/usr/bin/env python3
"""
Unit tests for Moral Compass Gradio apps.

Tests that apps can be instantiated without errors.
Does not test actual UI functionality (would require browser testing).

Run with: pytest tests/test_moral_compass_apps.py -v
"""

import pytest


def test_tutorial_app_can_be_created():
    """Test that tutorial app can be instantiated."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    
    app = create_tutorial_app()
    assert app is not None
    # Gradio Blocks objects should have a launch method
    assert hasattr(app, 'launch')


def test_judge_app_can_be_created():
    """Test that judge app can be instantiated."""
    from aimodelshare.moral_compass.apps import create_judge_app
    
    app = create_judge_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_ai_consequences_app_can_be_created():
    """Test that AI consequences app can be instantiated."""
    from aimodelshare.moral_compass.apps import create_ai_consequences_app
    
    app = create_ai_consequences_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_what_is_ai_app_can_be_created():
    """Test that What is AI app can be instantiated."""
    from aimodelshare.moral_compass.apps import create_what_is_ai_app
    
    app = create_what_is_ai_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_all_apps_exported_from_init():
    """Test that all apps are properly exported from __init__.py"""
    from aimodelshare.moral_compass import apps
    
    # Check that all factory functions are available
    assert hasattr(apps, 'create_tutorial_app')
    assert hasattr(apps, 'launch_tutorial_app')
    assert hasattr(apps, 'create_judge_app')
    assert hasattr(apps, 'launch_judge_app')
    assert hasattr(apps, 'create_ai_consequences_app')
    assert hasattr(apps, 'launch_ai_consequences_app')
    assert hasattr(apps, 'create_what_is_ai_app')
    assert hasattr(apps, 'launch_what_is_ai_app')
    assert hasattr(apps, 'create_model_building_game_app')
    assert hasattr(apps, 'launch_model_building_game_app')
    assert hasattr(apps, 'create_model_building_game_beginner_app')
    assert hasattr(apps, 'launch_model_building_game_beginner_app')


def test_judge_app_defendant_profiles():
    """Test that judge app generates defendant profiles correctly."""
    from aimodelshare.moral_compass.apps.judge import _generate_defendant_profiles
    
    profiles = _generate_defendant_profiles()
    
    # Check we have 5 profiles
    assert len(profiles) == 5
    
    # Check each profile has required fields
    for profile in profiles:
        assert 'id' in profile
        assert 'name' in profile
        assert 'age' in profile
        assert 'gender' in profile
        assert 'race' in profile
        assert 'prior_offenses' in profile
        assert 'current_charge' in profile
        assert 'ai_risk' in profile
        assert 'ai_confidence' in profile
        
        # Check risk levels are valid
        assert profile['ai_risk'] in ['High', 'Medium', 'Low']


def test_what_is_ai_predictor():
    """Test that the simple predictor in what_is_ai app works."""
    from aimodelshare.moral_compass.apps.what_is_ai import _create_simple_predictor
    
    predictor = _create_simple_predictor()
    
    # Test with some sample inputs
    result = predictor(25, 2, "Moderate")
    assert isinstance(result, str)
    assert 'Risk' in result
    
    # Test that it returns different results for different inputs
    result_low = predictor(50, 0, "Minor")
    result_high = predictor(20, 5, "Serious")
    
    assert result_low != result_high


def test_apps_with_custom_theme():
    """Test that apps can be created with custom theme colors."""
    from aimodelshare.moral_compass.apps import (
        create_tutorial_app, 
        create_judge_app,
        create_ai_consequences_app,
        create_what_is_ai_app,
        create_model_building_game_app,
        create_model_building_game_beginner_app
    )
    
    # Should not raise any errors
    tutorial = create_tutorial_app(theme_primary_hue="blue")
    assert tutorial is not None
    
    judge = create_judge_app(theme_primary_hue="red")
    assert judge is not None
    
    consequences = create_ai_consequences_app(theme_primary_hue="green")
    assert consequences is not None
    
    ai = create_what_is_ai_app(theme_primary_hue="purple")
    assert ai is not None
    
    model_building_game = create_model_building_game_app(theme_primary_hue="orange")
    assert model_building_game is not None
    
    model_building_game_beginner = create_model_building_game_beginner_app(theme_primary_hue="teal")
    assert model_building_game_beginner is not None


def test_model_building_game_app_can_be_created():
    """Test that model building game app (advanced) can be instantiated."""
    from aimodelshare.moral_compass.apps import create_model_building_game_app
    
    app = create_model_building_game_app()
    assert app is not None
    assert hasattr(app, 'launch')


def test_model_building_game_beginner_app_can_be_created():
    """Test that model building game beginner app can be instantiated."""
    from aimodelshare.moral_compass.apps import create_model_building_game_beginner_app
    
    app = create_model_building_game_beginner_app()
    assert app is not None
    assert hasattr(app, 'launch')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
