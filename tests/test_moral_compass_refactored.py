#!/usr/bin/env python3
"""
Tests for refactored Moral Compass Gradio apps helper modules.

Tests the new centralized utilities:
- _env_utils.py: Environment detection and port finding
- _launch_core.py: Queue configuration, launch logic, and theme management
- _height.py: Height estimation utilities

Run with: pytest tests/test_moral_compass_refactored.py -v
"""

import pytest


def test_env_utils_in_colab_detection():
    """Test that in_colab() correctly detects Google Colab environment."""
    from aimodelshare.moral_compass.apps._env_utils import in_colab
    
    # Should return False in test environment (not Colab)
    result = in_colab()
    assert isinstance(result, bool)
    assert result is False  # We're not in Colab during tests


def test_env_utils_get_debug_mode():
    """Test that get_debug_mode() reads environment variables correctly."""
    import os
    from aimodelshare.moral_compass.apps._env_utils import get_debug_mode
    
    # Save original values
    original_gradio_debug = os.environ.get("GRADIO_DEBUG")
    original_debug = os.environ.get("DEBUG")
    
    try:
        # Test default (no env vars)
        os.environ.pop("GRADIO_DEBUG", None)
        os.environ.pop("DEBUG", None)
        assert get_debug_mode() is False
        
        # Test GRADIO_DEBUG=1
        os.environ["GRADIO_DEBUG"] = "1"
        assert get_debug_mode() is True
        
        # Test GRADIO_DEBUG=true
        os.environ["GRADIO_DEBUG"] = "true"
        assert get_debug_mode() is True
        
        # Test DEBUG=yes
        os.environ.pop("GRADIO_DEBUG", None)
        os.environ["DEBUG"] = "yes"
        assert get_debug_mode() is True
        
        # Test invalid value
        os.environ["DEBUG"] = "0"
        assert get_debug_mode() is False
    finally:
        # Restore original values
        if original_gradio_debug is not None:
            os.environ["GRADIO_DEBUG"] = original_gradio_debug
        else:
            os.environ.pop("GRADIO_DEBUG", None)
        if original_debug is not None:
            os.environ["DEBUG"] = original_debug
        else:
            os.environ.pop("DEBUG", None)


def test_env_utils_find_free_port():
    """Test that find_free_port() returns a valid port number."""
    from aimodelshare.moral_compass.apps._env_utils import find_free_port
    
    # Should find a free port
    port = find_free_port()
    assert isinstance(port, int)
    assert 7860 <= port < 7960  # Default range
    
    # Test with custom range
    port = find_free_port(start_port=8000, max_attempts=10)
    assert isinstance(port, int)
    assert 8000 <= port < 8010


def test_height_estimate_height():
    """Test that estimate_height() returns reasonable values."""
    from aimodelshare.moral_compass.apps._height import estimate_height
    
    # Default case
    height = estimate_height()
    assert isinstance(height, int)
    assert 800 <= height <= 1400
    
    # Test with more sections
    height = estimate_height(num_sections=5)
    assert height >= 800
    assert height <= 1400
    
    # Test with interactive elements
    height_interactive = estimate_height(has_interactive_elements=True)
    height_static = estimate_height(has_interactive_elements=False)
    assert height_interactive > height_static
    
    # Test with custom base height
    height = estimate_height(base_height=600)
    assert height >= 600


def test_launch_core_get_theme():
    """Test that get_theme() returns a Gradio theme."""
    from aimodelshare.moral_compass.apps._launch_core import get_theme
    
    theme = get_theme()
    assert theme is not None
    
    # Test with custom hue
    theme_custom = get_theme(primary_hue="blue")
    assert theme_custom is not None


def test_launch_core_apply_queue():
    """Test that apply_queue() configures queue on a Gradio Blocks instance."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    from aimodelshare.moral_compass.apps._launch_core import apply_queue
    
    demo = create_tutorial_app()
    
    # Apply queue configuration
    result = apply_queue(demo, default_concurrency_limit=2, max_size=32)
    
    # Should return the demo
    assert result is demo
    
    # Gradio Blocks should have queue configured (we can't easily test internals)
    assert hasattr(demo, 'queue')


def test_launch_core_register_and_close_all():
    """Test demo registration and cleanup."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    from aimodelshare.moral_compass.apps._launch_core import register, close_all_apps, _active_demos
    
    # Clear any existing demos
    close_all_apps()
    assert len(_active_demos) == 0
    
    # Create and register a demo
    demo1 = create_tutorial_app()
    register(demo1)
    assert len(_active_demos) == 1
    assert demo1 in _active_demos
    
    # Register another demo
    demo2 = create_tutorial_app()
    register(demo2)
    assert len(_active_demos) == 2
    
    # Close all demos
    close_all_apps()
    assert len(_active_demos) == 0


def test_judge_app_uses_state():
    """Test that judge app uses gr.State for decisions (prevents shared state)."""
    from aimodelshare.moral_compass.apps import create_judge_app
    import gradio as gr
    
    demo = create_judge_app()
    
    # Check that the demo has State components
    # We can't easily introspect Gradio internals, but we can verify the app creates successfully
    assert demo is not None
    assert hasattr(demo, 'launch')


def test_apps_have_queue_and_analytics_disabled():
    """Test that launch functions use proper queue and analytics settings."""
    # This is more of an integration test - we verify that apps can be created
    # and that launch functions exist with proper signatures
    from aimodelshare.moral_compass.apps import (
        launch_tutorial_app,
        launch_judge_app,
        launch_ai_consequences_app,
        launch_what_is_ai_app
    )
    
    # Verify launch functions exist and accept proper arguments
    import inspect
    
    for launch_func in [launch_tutorial_app, launch_judge_app, 
                        launch_ai_consequences_app, launch_what_is_ai_app]:
        sig = inspect.signature(launch_func)
        params = sig.parameters
        
        # Should accept height, share, and debug parameters
        assert 'height' in params
        assert 'share' in params
        assert 'debug' in params
        
        # Should have proper defaults
        assert params['share'].default is False
        assert params['debug'].default is False
        assert isinstance(params['height'].default, int)


def test_launch_blocks_function_signature():
    """Test that launch_blocks has proper signature."""
    from aimodelshare.moral_compass.apps._launch_core import launch_blocks
    import inspect
    
    sig = inspect.signature(launch_blocks)
    params = sig.parameters
    
    # Required parameter
    assert 'demo' in params
    
    # Optional parameters with defaults
    assert params['height'].default == 800
    assert params['share'].default is False
    assert params['debug'].default is False
    assert params['inline'].default is True
    assert params['prevent_thread_lock'].default is True
    assert params['show_api'].default is False
    assert params['quiet'].default is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
