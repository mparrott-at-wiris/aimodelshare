#!/usr/bin/env python3
"""
Unit tests to verify white background CSS override in Moral Compass apps.

Tests that all apps have the forced light background CSS to prevent dark mode issues.

Run with: pytest tests/test_white_background_css.py -v
"""

import pytest


def test_tutorial_app_has_white_background_css():
    """Test that tutorial app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    
    app = create_tutorial_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_judge_app_has_white_background_css():
    """Test that judge app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_judge_app
    
    app = create_judge_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_ai_consequences_app_has_white_background_css():
    """Test that AI consequences app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_ai_consequences_app
    
    app = create_ai_consequences_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_what_is_ai_app_has_white_background_css():
    """Test that What is AI app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_what_is_ai_app
    
    app = create_what_is_ai_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_ethical_revelation_app_has_white_background_css():
    """Test that Ethical Revelation app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_ethical_revelation_app
    
    app = create_ethical_revelation_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_moral_compass_challenge_app_has_white_background_css():
    """Test that Moral Compass Challenge app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_moral_compass_challenge_app
    
    app = create_moral_compass_challenge_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_model_building_game_app_has_white_background_css():
    """Test that model building game app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_model_building_game_app
    
    app = create_model_building_game_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_model_building_game_beginner_app_has_white_background_css():
    """Test that model building game beginner app has the white background CSS override."""
    from aimodelshare.moral_compass.apps import create_model_building_game_beginner_app
    
    app = create_model_building_game_beginner_app()
    assert app is not None
    assert hasattr(app, 'css')
    assert "Global forced light background overrides" in app.css
    assert "background:#ffffff !important" in app.css
    assert "color-scheme: light" in app.css


def test_css_override_has_all_required_selectors():
    """Test that CSS override includes all required selectors and properties."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    
    app = create_tutorial_app()
    css = app.css
    
    # Check for HTML/body selectors
    assert "html, body, .gradio-container" in css
    
    # Check for dark mode neutralization
    assert "body.dark" in css or "html.dark" in css
    assert 'body[class*="dark"]' in css or 'html[class*="dark"]' in css
    
    # Check for root color-scheme
    assert ":root" in css
    assert "color-scheme: light" in css
    
    # Check for CSS variables override
    assert "--color-background-primary" in css
    assert "--color-background-secondary" in css
    assert "--color-background-tertiary" in css


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
