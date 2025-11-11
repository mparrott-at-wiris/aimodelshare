#!/usr/bin/env python3
"""
Unit tests for the Gradio slider TypeError fix in model building game apps.

Tests that the safe_int helper function works correctly and protects against
TypeError when Gradio sliders receive None values.

Run with: pytest tests/test_model_building_game_slider_fix.py -v
"""

import pytest


def test_safe_int_with_valid_integer():
    """Test that safe_int handles valid integers correctly."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int(1) == 1
    assert safe_int(5) == 5
    assert safe_int(100) == 100


def test_safe_int_with_none():
    """Test that safe_int returns default when value is None."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int(None) == 1  # default is 1
    assert safe_int(None, 2) == 2  # custom default
    assert safe_int(None, 5) == 5


def test_safe_int_with_string_number():
    """Test that safe_int converts string numbers to int."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int("3") == 3
    assert safe_int("10") == 10


def test_safe_int_with_float():
    """Test that safe_int converts floats to int."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int(3.7) == 3
    assert safe_int(5.2) == 5


def test_safe_int_with_invalid_string():
    """Test that safe_int returns default for invalid strings."""
    from aimodelshare.moral_compass.apps.model_building_game import safe_int
    
    assert safe_int("invalid") == 1
    assert safe_int("abc", 3) == 3


def test_safe_int_beginner_with_valid_integer():
    """Test that safe_int in beginner version handles valid integers correctly."""
    from aimodelshare.moral_compass.apps.model_building_game_beginner import safe_int
    
    assert safe_int(1) == 1
    assert safe_int(3) == 3


def test_safe_int_beginner_with_none():
    """Test that safe_int in beginner version returns default when value is None."""
    from aimodelshare.moral_compass.apps.model_building_game_beginner import safe_int
    
    assert safe_int(None) == 1
    assert safe_int(None, 2) == 2


def test_compute_rank_settings_returns_integers():
    """Test that compute_rank_settings always returns integer values for slider settings."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    # Test with submission_count = 0
    result = compute_rank_settings(0, "The Balanced Generalist", 2, 1, [])
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)
    assert isinstance(result["size_max"], int)
    assert isinstance(result["size_value"], int)
    
    # Test with submission_count = 1
    result = compute_rank_settings(1, "The Rule-Maker", 3, 2, [])
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)
    assert isinstance(result["size_max"], int)
    assert isinstance(result["size_value"], int)
    
    # Test with submission_count = 2
    result = compute_rank_settings(2, "The Deep Pattern-Finder", 5, 5, ["race"])
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)
    assert isinstance(result["size_max"], int)
    assert isinstance(result["size_value"], int)


def test_compute_rank_state_returns_integers():
    """Test that compute_rank_state in beginner version always returns integer values."""
    from aimodelshare.moral_compass.apps.model_building_game_beginner import compute_rank_state
    
    # Test with submissions = 0
    result = compute_rank_state(0, "The Balanced Generalist", 2, "Small (40%)", False)
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)
    
    # Test with submissions = 1
    result = compute_rank_state(1, "The Rule-Maker", 3, "Full (100%)", False)
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)
    
    # Test with submissions = 2+
    result = compute_rank_state(2, "The Deep Pattern-Finder", 3, "Full (100%)", True)
    assert isinstance(result["complexity_max"], int)
    assert isinstance(result["complexity_value"], int)


def test_tune_model_with_safe_int_values():
    """Test that tune_model accepts the output of safe_int."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity, safe_int
    from sklearn.linear_model import LogisticRegression
    
    model = LogisticRegression()
    
    # Test with safe_int coerced values
    tuned = tune_model_complexity(model, safe_int(None, 2))
    assert tuned is not None
    
    tuned = tune_model_complexity(model, safe_int("3"))
    assert tuned is not None


def test_tune_model_beginner_with_safe_int_values():
    """Test that tune_model in beginner version accepts the output of safe_int."""
    from aimodelshare.moral_compass.apps.model_building_game_beginner import tune_model, safe_int
    from sklearn.linear_model import LogisticRegression
    
    model = LogisticRegression()
    
    # Test with safe_int coerced values
    tuned = tune_model(model, safe_int(None, 2))
    assert tuned is not None
    
    tuned = tune_model(model, safe_int("3"))
    assert tuned is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
