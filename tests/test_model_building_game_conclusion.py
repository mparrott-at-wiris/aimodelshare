#!/usr/bin/env python3
"""
Unit tests for Model Building Game conclusion enhancements.

Tests the dynamic conclusion panel with:
- Performance metrics display
- Tier progression visualization
- Ethical reflection content
- First submission score tracking
- Reduced-motion accessibility

Run with: pytest tests/test_model_building_game_conclusion.py -v
"""

import pytest


def test_build_final_conclusion_html_basic():
    """Test that conclusion HTML is generated with all required elements."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    # Test with minimal submissions
    html = build_final_conclusion_html(
        best_score=0.6543,
        submissions=1,
        rank=5,
        first_score=None,
        feature_set=["age", "race"]
    )
    
    # Check for key sections
    assert "Engineering Phase Complete" in html
    assert "Performance Snapshot" in html
    assert "Best Accuracy:" in html
    assert "0.6543" in html
    assert "Rank Achieved:" in html
    assert "#5" in html
    assert "Submissions:" in html
    assert "Tier Progress:" in html
    assert "Strong Predictors Used:" in html
    assert "Ethical Reflection:" in html
    assert "SCROLL DOWN" in html
    assert "Refine Again" in html
    assert "Copy Summary" in html


def test_tier_progression_trainee():
    """Test tier progression for 1 submission (Trainee only)."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7000,
        submissions=1,
        rank=1,
        first_score=None,
        feature_set=[]
    )
    
    # Should show Trainee with checkmark
    assert "Trainee ✅" in html
    # Should not show checkmarks for other tiers
    assert "Junior ✅" not in html
    assert "Senior ✅" not in html
    assert "Lead ✅" not in html


def test_tier_progression_junior():
    """Test tier progression for 2 submissions (Trainee + Junior)."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7200,
        submissions=2,
        rank=1,
        first_score=0.7000,
        feature_set=[]
    )
    
    # Should show Trainee and Junior with checkmarks
    assert "Trainee ✅" in html
    assert "Junior ✅" in html
    # Should not show checkmarks for Senior/Lead
    assert "Senior ✅" not in html
    assert "Lead ✅" not in html


def test_tier_progression_all():
    """Test tier progression for 4+ submissions (all tiers)."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7800,
        submissions=5,
        rank=1,
        first_score=0.7000,
        feature_set=["age", "priors_count"]
    )
    
    # Should show all tiers with checkmarks
    assert "Trainee ✅" in html
    assert "Junior ✅" in html
    assert "Senior ✅" in html
    assert "Lead ✅" in html


def test_improvement_calculation_single_submission():
    """Test improvement shows +0.0000 for first submission."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7000,
        submissions=1,
        rank=1,
        first_score=None,
        feature_set=[]
    )
    
    # Should show improvement as +0.0000
    assert "+0.0000" in html or "0.0000" in html


def test_improvement_calculation_multiple_submissions():
    """Test improvement calculation for multiple submissions."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7500,
        submissions=3,
        rank=1,
        first_score=0.7000,
        feature_set=[]
    )
    
    # Should show improvement as +0.0500
    assert "+0.0500" in html


def test_strong_predictors_none():
    """Test display when no strong predictors are used."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.6500,
        submissions=1,
        rank=1,
        first_score=None,
        feature_set=["race", "sex"]
    )
    
    # Should show 0 strong predictors
    assert "Strong Predictors Used:</b> 0" in html
    assert "None yet" in html


def test_strong_predictors_present():
    """Test display when strong predictors are used."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7800,
        submissions=3,
        rank=1,
        first_score=0.7000,
        feature_set=["age", "length_of_stay", "priors_count", "race"]
    )
    
    # Should show 3 strong predictors (age, length_of_stay, priors_count)
    assert "Strong Predictors Used:</b> 3" in html
    # Check that at least some of the strong predictors are listed
    assert "age" in html or "length_of_stay" in html or "priors_count" in html


def test_tip_message_for_few_submissions():
    """Test that tip message appears for < 2 submissions."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.6500,
        submissions=1,
        rank=1,
        first_score=None,
        feature_set=[]
    )
    
    # Should show tip message
    assert "Tip:" in html
    assert "2–3 submissions" in html


def test_no_tip_message_for_many_submissions():
    """Test that tip message does not appear for >= 2 submissions."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7200,
        submissions=3,
        rank=1,
        first_score=0.7000,
        feature_set=[]
    )
    
    # Should NOT show tip message
    assert "Try at least 2–3 submissions" not in html


def test_rank_display_with_rank():
    """Test rank display when user has a rank."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7500,
        submissions=2,
        rank=3,
        first_score=0.7000,
        feature_set=[]
    )
    
    # Should show rank with # prefix
    assert "Rank Achieved:</b> #3" in html


def test_rank_display_no_rank():
    """Test rank display when user has no rank (rank <= 0)."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.6500,
        submissions=1,
        rank=0,
        first_score=None,
        feature_set=[]
    )
    
    # Should show em dash instead of rank
    assert "Rank Achieved:</b> —" in html


def test_build_conclusion_from_state_wrapper():
    """Test that wrapper function correctly calls build_final_conclusion_html."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        build_conclusion_from_state,
        build_final_conclusion_html
    )
    
    # Both functions should produce identical output
    result1 = build_conclusion_from_state(
        best_score=0.7500,
        submissions=2,
        rank=5,
        first_score=0.7000,
        feature_set=["age", "race"]
    )
    
    result2 = build_final_conclusion_html(
        best_score=0.7500,
        submissions=2,
        rank=5,
        first_score=0.7000,
        feature_set=["age", "race"]
    )
    
    assert result1 == result2


def test_animation_keyframe_present():
    """Test that pulseArrow animation is defined in CSS."""
    # This test reads the file to check for CSS animation
    from pathlib import Path
    
    file_path = Path(__file__).parent.parent / "aimodelshare" / "moral_compass" / "apps" / "model_building_game.py"
    content = file_path.read_text()
    
    # Check for animation keyframe
    assert "@keyframes pulseArrow" in content
    assert "animation:pulseArrow" in content or "animation: pulseArrow" in content


def test_reduced_motion_accessibility():
    """Test that reduced-motion media query is present for accessibility."""
    from pathlib import Path
    
    file_path = Path(__file__).parent.parent / "aimodelshare" / "moral_compass" / "apps" / "model_building_game.py"
    content = file_path.read_text()
    
    # Check for reduced-motion media query
    assert "prefers-reduced-motion" in content
    assert "[style*='pulseArrow']" in content or "pulseArrow" in content


def test_clipboard_copy_button():
    """Test that copy summary button is present with correct onclick handler."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7500,
        submissions=3,
        rank=2,
        first_score=0.7000,
        feature_set=["age"]
    )
    
    # Check for copy button
    assert "Copy Summary" in html
    assert "navigator.clipboard.writeText" in html
    assert "Model Arena Complete" in html


def test_scroll_to_top_button():
    """Test that refine again button is present with scroll to top handler."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    html = build_final_conclusion_html(
        best_score=0.7500,
        submissions=2,
        rank=1,
        first_score=0.7000,
        feature_set=[]
    )
    
    # Check for refine button
    assert "Refine Again" in html
    assert "window.scrollTo" in html
    assert "top:0" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
