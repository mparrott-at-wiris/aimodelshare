#!/usr/bin/env python3
"""
Unit tests for the Gradio slider TypeError fix in model building game apps.

Tests that the safe_int helper function works correctly and protects against
TypeError when Gradio sliders receive None values.

Run with: pytest tests/test_model_building_game_slider_fix.py -v
"""

import pytest
import sys
import importlib.util


# Helper to extract and test safe_int without importing full module
def get_safe_int_from_file(filepath):
    """Extract safe_int function from a Python file without full import."""
    spec = importlib.util.spec_from_file_location("temp_module", filepath)
    module = importlib.util.module_from_spec(spec)
    
    # Execute only the safe_int function by extracting its code
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find and execute just the safe_int function
    lines = content.split('\n')
    in_safe_int = False
    safe_int_lines = []
    indent_level = 0
    
    for line in lines:
        if 'def safe_int(value, default=1):' in line:
            in_safe_int = True
            indent_level = len(line) - len(line.lstrip())
            safe_int_lines.append(line)
        elif in_safe_int:
            current_indent = len(line) - len(line.lstrip())
            # Stop if we reach a non-indented line or another function
            if line.strip() and current_indent <= indent_level and not line.strip().startswith('#'):
                break
            safe_int_lines.append(line)
    
    # Execute the function definition
    exec('\n'.join(safe_int_lines), module.__dict__)
    return module.safe_int


def test_safe_int_with_valid_integer():
    """Test that safe_int handles valid integers correctly."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int(1) == 1
    assert safe_int(5) == 5
    assert safe_int(100) == 100


def test_safe_int_with_none():
    """Test that safe_int returns default when value is None."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int(None) == 1  # default is 1
    assert safe_int(None, 2) == 2  # custom default
    assert safe_int(None, 5) == 5


def test_safe_int_with_string_number():
    """Test that safe_int converts string numbers to int."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int("3") == 3
    assert safe_int("10") == 10


def test_safe_int_with_float():
    """Test that safe_int converts floats to int."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int(3.7) == 3
    assert safe_int(5.2) == 5


def test_safe_int_with_invalid_string():
    """Test that safe_int returns default for invalid strings."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int("invalid") == 1
    assert safe_int("abc", 3) == 3


def test_safe_int_beginner_with_valid_integer():
    """Test that safe_int in beginner version handles valid integers correctly."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game_beginner.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int(1) == 1
    assert safe_int(3) == 3


def test_safe_int_beginner_with_none():
    """Test that safe_int in beginner version returns default when value is None."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game_beginner.py')
    safe_int = get_safe_int_from_file(filepath)
    
    assert safe_int(None) == 1
    assert safe_int(None, 2) == 2



def test_safe_int_edge_cases():
    """Test edge cases for safe_int."""
    import os
    filepath = os.path.join(os.path.dirname(__file__), '..', 'aimodelshare', 'moral_compass', 'apps', 'model_building_game.py')
    safe_int = get_safe_int_from_file(filepath)
    
    # Test with zero
    assert safe_int(0) == 0
    
    # Test with negative
    assert safe_int(-5) == -5
    
    # Test with empty string
    assert safe_int("", 10) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
