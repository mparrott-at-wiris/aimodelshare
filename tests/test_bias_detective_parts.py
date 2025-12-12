"""
Tests for bias_detective_part1 and bias_detective_part2 apps.
Verifies that the apps can be created and navigation features are present.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aimodelshare.moral_compass.apps.bias_detective_part1 import create_bias_detective_part1_app
from aimodelshare.moral_compass.apps.bias_detective_part2 import create_bias_detective_part2_app


def test_part1_app_creation():
    """Test that bias_detective_part1 app can be created successfully."""
    app = create_bias_detective_part1_app()
    assert app is not None, "Part1 app should be created successfully"


def test_part2_app_creation():
    """Test that bias_detective_part2 app can be created successfully."""
    app = create_bias_detective_part2_app()
    assert app is not None, "Part2 app should be created successfully"


def test_part1_has_navigation_css():
    """Test that part1 app includes navigation overlay CSS."""
    from aimodelshare.moral_compass.apps import bias_detective_part1
    
    # Check that the CSS includes the navigation overlay styles
    css_content = bias_detective_part1.css
    assert "#nav-loading-overlay" in css_content, "Part1 should have navigation overlay CSS"
    assert ".nav-spinner" in css_content, "Part1 should have spinner CSS"
    assert "@keyframes nav-spin" in css_content, "Part1 should have spinner animation"


def test_part2_has_navigation_css():
    """Test that part2 app includes navigation overlay CSS."""
    from aimodelshare.moral_compass.apps import bias_detective_part2
    
    # Check that the CSS includes the navigation overlay styles
    css_content = bias_detective_part2.css
    assert "#nav-loading-overlay" in css_content, "Part2 should have navigation overlay CSS"
    assert ".nav-spinner" in css_content, "Part2 should have spinner CSS"
    assert "@keyframes nav-spin" in css_content, "Part2 should have spinner animation"


if __name__ == "__main__":
    test_part1_app_creation()
    test_part2_app_creation()
    test_part1_has_navigation_css()
    test_part2_has_navigation_css()
    print("✓ All tests passed!")
