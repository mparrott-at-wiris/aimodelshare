#!/usr/bin/env python3
"""
Unit tests for Model Complexity Slider Expansion (1-5 to 1-10).

Tests the expansion of complexity slider from 1-5 scale to 1-10 scale:
- tune_model_complexity() hyperparameter mappings
- compute_rank_settings() complexity gating per rank
- Validate all model types handle 10 complexity levels

Run with: pytest tests/test_complexity_slider_expansion.py -v
"""

import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier


def test_tune_model_complexity_logistic_regression_10_levels():
    """Test LogisticRegression complexity tuning across all 10 levels."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    expected_c_values = {
        1: 0.01, 2: 0.025, 3: 0.05, 4: 0.1, 5: 0.25,
        6: 0.5, 7: 1.0, 8: 2.0, 9: 5.0, 10: 10.0
    }
    
    for level, expected_c in expected_c_values.items():
        model = LogisticRegression(max_iter=100, random_state=42)
        tuned = tune_model_complexity(model, level)
        
        assert tuned.C == expected_c, f"Level {level}: expected C={expected_c}, got {tuned.C}"
        assert tuned.max_iter >= 500, f"Level {level}: max_iter should be >= 500, got {tuned.max_iter}"


def test_tune_model_complexity_random_forest_10_levels():
    """Test RandomForestClassifier complexity tuning across all 10 levels."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    expected_depth = {
        1: 3, 2: 5, 3: 7, 4: 9, 5: 11,
        6: 15, 7: 20, 8: 25, 9: None, 10: None
    }
    expected_estimators = {
        1: 20, 2: 30, 3: 40, 4: 60, 5: 80,
        6: 100, 7: 120, 8: 150, 9: 180, 10: 220
    }
    
    for level in range(1, 11):
        model = RandomForestClassifier(random_state=42)
        tuned = tune_model_complexity(model, level)
        
        assert tuned.max_depth == expected_depth[level], \
            f"Level {level}: expected max_depth={expected_depth[level]}, got {tuned.max_depth}"
        assert tuned.n_estimators == expected_estimators[level], \
            f"Level {level}: expected n_estimators={expected_estimators[level]}, got {tuned.n_estimators}"


def test_tune_model_complexity_decision_tree_10_levels():
    """Test DecisionTreeClassifier complexity tuning across all 10 levels."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    expected_depth = {
        1: 2, 2: 3, 3: 4, 4: 5, 5: 6,
        6: 8, 7: 10, 8: 12, 9: 15, 10: None
    }
    
    for level in range(1, 11):
        model = DecisionTreeClassifier(random_state=42)
        tuned = tune_model_complexity(model, level)
        
        assert tuned.max_depth == expected_depth[level], \
            f"Level {level}: expected max_depth={expected_depth[level]}, got {tuned.max_depth}"


def test_tune_model_complexity_kneighbors_10_levels():
    """Test KNeighborsClassifier complexity tuning across all 10 levels."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    expected_neighbors = {
        1: 100, 2: 75, 3: 60, 4: 50, 5: 40,
        6: 30, 7: 25, 8: 15, 9: 7, 10: 3
    }
    
    for level in range(1, 11):
        model = KNeighborsClassifier()
        tuned = tune_model_complexity(model, level)
        
        assert tuned.n_neighbors == expected_neighbors[level], \
            f"Level {level}: expected n_neighbors={expected_neighbors[level]}, got {tuned.n_neighbors}"


def test_compute_rank_settings_trainee_complexity_max_3():
    """Test Trainee rank (submission_count=0) has complexity_max=3."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    settings = compute_rank_settings(
        submission_count=0,
        current_model="The Balanced Generalist",
        current_complexity=5,  # Try to set higher
        current_feature_set=[],
        current_data_size="Small (20%)"
    )
    
    assert settings["complexity_max"] == 3, "Trainee should have complexity_max=3"
    assert settings["complexity_value"] == 3, "Trainee complexity_value should be capped at 3"


def test_compute_rank_settings_junior_complexity_max_6():
    """Test Junior rank (submission_count=1) has complexity_max=6."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    settings = compute_rank_settings(
        submission_count=1,
        current_model="The Balanced Generalist",
        current_complexity=10,  # Try to set higher
        current_feature_set=[],
        current_data_size="Small (20%)"
    )
    
    assert settings["complexity_max"] == 6, "Junior should have complexity_max=6"
    assert settings["complexity_value"] == 6, "Junior complexity_value should be capped at 6"


def test_compute_rank_settings_senior_complexity_max_8():
    """Test Senior rank (submission_count=2) has complexity_max=8."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    settings = compute_rank_settings(
        submission_count=2,
        current_model="The Balanced Generalist",
        current_complexity=10,  # Try to set higher
        current_feature_set=[],
        current_data_size="Small (20%)"
    )
    
    assert settings["complexity_max"] == 8, "Senior should have complexity_max=8"
    assert settings["complexity_value"] == 8, "Senior complexity_value should be capped at 8"


def test_compute_rank_settings_lead_complexity_max_10():
    """Test Lead rank (submission_count>=3) has complexity_max=10."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    for count in [3, 4, 5, 10]:
        settings = compute_rank_settings(
            submission_count=count,
            current_model="The Balanced Generalist",
            current_complexity=10,
            current_feature_set=[],
            current_data_size="Small (20%)"
        )
        
        assert settings["complexity_max"] == 10, f"Lead (count={count}) should have complexity_max=10"
        assert settings["complexity_value"] == 10, f"Lead (count={count}) complexity_value should be 10"


def test_tune_model_complexity_handles_unknown_level():
    """Test that tune_model_complexity handles unknown levels gracefully."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    # Test with level outside 1-10 range
    model = LogisticRegression(max_iter=100, random_state=42)
    tuned = tune_model_complexity(model, 15)
    
    # Should fallback to default (1.0 for LogisticRegression)
    assert tuned.C == 1.0, "Unknown level should fallback to default C=1.0"


def test_complexity_slider_preserves_value_within_rank_limit():
    """Test that complexity values are preserved when within rank limits."""
    from aimodelshare.moral_compass.apps.model_building_game import compute_rank_settings
    
    # Trainee with complexity=2 (within max=3)
    settings = compute_rank_settings(0, "The Balanced Generalist", 2, [], "Small (20%)")
    assert settings["complexity_value"] == 2, "Should preserve complexity=2 for Trainee"
    
    # Junior with complexity=5 (within max=6)
    settings = compute_rank_settings(1, "The Balanced Generalist", 5, [], "Small (20%)")
    assert settings["complexity_value"] == 5, "Should preserve complexity=5 for Junior"
    
    # Senior with complexity=7 (within max=8)
    settings = compute_rank_settings(2, "The Balanced Generalist", 7, [], "Small (20%)")
    assert settings["complexity_value"] == 7, "Should preserve complexity=7 for Senior"


def test_all_models_can_be_tuned_to_level_10():
    """Test that all model types can be successfully tuned to level 10."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    models = [
        LogisticRegression(max_iter=100, random_state=42),
        RandomForestClassifier(random_state=42),
        DecisionTreeClassifier(random_state=42),
        KNeighborsClassifier()
    ]
    
    for model in models:
        tuned = tune_model_complexity(model, 10)
        assert tuned is not None, f"Level 10 tuning failed for {type(model).__name__}"


def test_logistic_regression_max_iter_increased():
    """Test that LogisticRegression max_iter is properly increased to at least 500."""
    from aimodelshare.moral_compass.apps.model_building_game import tune_model_complexity
    
    # Test with initially low max_iter
    model = LogisticRegression(max_iter=50, random_state=42)
    tuned = tune_model_complexity(model, 5)
    
    assert tuned.max_iter >= 500, f"max_iter should be >= 500, got {tuned.max_iter}"
    
    # Test with already high max_iter (should preserve higher value)
    model = LogisticRegression(max_iter=1000, random_state=42)
    tuned = tune_model_complexity(model, 5)
    
    assert tuned.max_iter >= 500, f"max_iter should remain >= 500, got {tuned.max_iter}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
