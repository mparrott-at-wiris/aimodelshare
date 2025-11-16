#!/usr/bin/env python3
"""
Unit tests for Model Building Game Attempt Limit feature.

Tests the 10-submission limit functionality:
- ATTEMPT_LIMIT constant definition
- Attempt tracker HTML generation
- Early submission check logic
- UI state updates when limit reached
- Conclusion HTML with attempt cap note

Run with: pytest tests/test_attempt_limit.py -v
"""

import pytest


def test_attempt_limit_constant():
    """Test that ATTEMPT_LIMIT constant is defined and equals 10."""
    from aimodelshare.moral_compass.apps.model_building_game import ATTEMPT_LIMIT
    
    assert ATTEMPT_LIMIT == 10
    assert isinstance(ATTEMPT_LIMIT, int)


def test_build_attempts_tracker_html_normal():
    """Test attempts tracker HTML for normal state (< 8 attempts)."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Test with 0 attempts
    html = _build_attempts_tracker_html(0)
    assert "0/10" in html
    assert "📊" in html  # Normal icon
    assert "#f0f9ff" in html  # Blue background
    
    # Test with 5 attempts
    html = _build_attempts_tracker_html(5)
    assert "5/10" in html
    assert "📊" in html
    
    # Test with 7 attempts
    html = _build_attempts_tracker_html(7)
    assert "7/10" in html
    assert "📊" in html


def test_build_attempts_tracker_html_warning():
    """Test attempts tracker HTML for warning state (8-9 attempts)."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Test with 8 attempts (warning threshold)
    html = _build_attempts_tracker_html(8)
    assert "8/10" in html
    assert "⚠️" in html  # Warning icon
    assert "#fef3c7" in html  # Yellow background
    
    # Test with 9 attempts
    html = _build_attempts_tracker_html(9)
    assert "9/10" in html
    assert "⚠️" in html


def test_build_attempts_tracker_html_limit_reached():
    """Test attempts tracker HTML when limit is reached."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Test with 10 attempts (limit reached)
    html = _build_attempts_tracker_html(10)
    assert "10/10" in html
    assert "🛑" in html  # Stop icon
    assert "Limit Reached" in html
    assert "#fef2f2" in html  # Red background
    
    # Test with more than 10 (should still show limit reached)
    html = _build_attempts_tracker_html(11)
    assert "11/10" in html
    assert "🛑" in html
    assert "Limit Reached" in html


def test_build_attempts_tracker_html_custom_limit():
    """Test attempts tracker HTML with custom limit."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Test with custom limit of 5, at 2 attempts (not in warning range yet)
    html = _build_attempts_tracker_html(2, limit=5)
    assert "2/5" in html
    assert "📊" in html
    
    # Test with custom limit of 5, at 3 attempts (within 2 of limit, shows warning)
    html = _build_attempts_tracker_html(3, limit=5)
    assert "3/5" in html
    assert "⚠️" in html  # Warning icon because 3 >= (5-2)
    
    # Test at custom limit
    html = _build_attempts_tracker_html(5, limit=5)
    assert "5/5" in html
    assert "🛑" in html


def test_build_attempts_tracker_html_structure():
    """Test that attempts tracker HTML has correct structure."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    html = _build_attempts_tracker_html(5)
    
    # Check for essential HTML elements
    assert "<div" in html
    assert "style=" in html
    assert "text-align:center" in html
    assert "padding:8px" in html
    assert "border-radius:8px" in html
    assert "</div>" in html
    assert "<p" in html
    assert "</p>" in html


def test_conclusion_html_with_attempt_cap():
    """Test that conclusion HTML includes attempt cap note when limit reached."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        build_final_conclusion_html, ATTEMPT_LIMIT
    )
    
    # Test with limit reached (10 submissions)
    html = build_final_conclusion_html(
        best_score=0.85,
        submissions=10,
        rank=5,
        first_score=0.75,
        feature_set=["age", "priors_count"]
    )
    
    # Should include attempt limit note
    assert "Attempt Limit Reached" in html or "attempt" in html.lower()
    assert str(ATTEMPT_LIMIT) in html
    assert "10" in html  # Should show the limit value


def test_conclusion_html_without_attempt_cap():
    """Test that conclusion HTML doesn't show attempt cap note when under limit."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    # Test with submissions under limit (5 submissions)
    html = build_final_conclusion_html(
        best_score=0.85,
        submissions=5,
        rank=5,
        first_score=0.75,
        feature_set=["age", "priors_count"]
    )
    
    # Should NOT include attempt limit reached note
    # (May still mention attempts in other contexts, but not "Limit Reached")
    assert "Limit Reached" not in html


def test_conclusion_html_shows_submission_count_with_limit():
    """Test that conclusion shows X/10 format when limit is reached."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        build_final_conclusion_html, ATTEMPT_LIMIT
    )
    
    # Test with limit reached
    html = build_final_conclusion_html(
        best_score=0.85,
        submissions=ATTEMPT_LIMIT,
        rank=5,
        first_score=0.75,
        feature_set=["age"]
    )
    
    # Should show submission count with limit notation
    # The format is: "Submissions: 10 / 10" in the list
    assert f"{ATTEMPT_LIMIT}" in html  # Shows the number


def test_attempt_limit_global_declared():
    """Test that attempts_tracker_display is declared as a global variable."""
    from aimodelshare.moral_compass.apps.model_building_game import attempts_tracker_display
    
    # Should be None initially (before app creation)
    assert attempts_tracker_display is None


def test_attempt_limit_constant_usage():
    """Test that ATTEMPT_LIMIT is used consistently in code."""
    from aimodelshare.moral_compass.apps.model_building_game import (
        ATTEMPT_LIMIT,
        _build_attempts_tracker_html
    )
    
    # The default limit in tracker should use ATTEMPT_LIMIT
    # When called without explicit limit, should use the constant
    html = _build_attempts_tracker_html(5)
    assert "5/10" in html  # Implicitly using ATTEMPT_LIMIT=10
    
    # Verify constant is accessible
    assert ATTEMPT_LIMIT > 0


def test_attempts_tracker_color_coding():
    """Test that color coding changes appropriately as limit approaches."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Normal state - blue
    html_normal = _build_attempts_tracker_html(5)
    assert "#f0f9ff" in html_normal  # Blue background
    assert "#0369a1" in html_normal  # Blue text
    
    # Warning state - yellow/orange
    html_warning = _build_attempts_tracker_html(8)
    assert "#fef3c7" in html_warning  # Yellow background
    assert "#92400e" in html_warning  # Orange text
    
    # Limit reached - red
    html_limit = _build_attempts_tracker_html(10)
    assert "#fef2f2" in html_limit  # Red background
    assert "#991b1b" in html_limit  # Red text


def test_attempts_tracker_icons():
    """Test that appropriate icons are used for different states."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Normal state - chart icon
    html_normal = _build_attempts_tracker_html(5)
    assert "📊" in html_normal
    
    # Warning state - warning icon
    html_warning = _build_attempts_tracker_html(8)
    assert "⚠️" in html_warning
    
    # Limit reached - stop icon
    html_limit = _build_attempts_tracker_html(10)
    assert "🛑" in html_limit


def test_conclusion_html_docstring():
    """Test that build_final_conclusion_html has proper docstring."""
    from aimodelshare.moral_compass.apps.model_building_game import build_final_conclusion_html
    
    # Check that function has a docstring
    assert build_final_conclusion_html.__doc__ is not None
    assert len(build_final_conclusion_html.__doc__) > 0
    
    # Check for key documentation elements
    doc = build_final_conclusion_html.__doc__
    assert "Args:" in doc or "Parameters:" in doc or "best_score" in doc
    assert "Returns:" in doc or "str" in doc


def test_attempts_tracker_helper_docstring():
    """Test that _build_attempts_tracker_html has proper docstring."""
    from aimodelshare.moral_compass.apps.model_building_game import _build_attempts_tracker_html
    
    # Check that function has a docstring
    assert _build_attempts_tracker_html.__doc__ is not None
    assert len(_build_attempts_tracker_html.__doc__) > 0
    
    # Check for key documentation elements
    doc = _build_attempts_tracker_html.__doc__
    assert "current_count" in doc or "Args:" in doc
    assert "Returns:" in doc or "HTML" in doc


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
