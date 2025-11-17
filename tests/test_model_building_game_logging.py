#!/usr/bin/env python3
"""
Unit tests for logging functionality in model_building_game.py

Tests that the logging configuration works correctly with debug flags.

Run with: pytest tests/test_model_building_game_logging.py -v
"""

import pytest
import logging
import sys
from unittest.mock import patch, MagicMock
from io import StringIO


def test_configure_logging_exists():
    """Test that configure_logging function is available."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging
    
    assert callable(configure_logging)


def test_configure_logging_debug_false():
    """Test that configure_logging sets WARNING level when debug=False."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Configure with debug=False
    configure_logging(debug=False)
    
    # Check that root logger is set to WARNING level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING


def test_configure_logging_debug_true():
    """Test that configure_logging sets DEBUG level when debug=True."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Configure with debug=True
    configure_logging(debug=True)
    
    # Check that root logger is set to DEBUG level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_configure_logging_q_flag():
    """Test that configure_logging sets DEBUG level when q=True."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Configure with q=True
    configure_logging(q=True)
    
    # Check that root logger is set to DEBUG level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_configure_logging_no_duplicate_handlers():
    """Test that configure_logging doesn't create duplicate handlers."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Call configure_logging multiple times
    configure_logging(debug=True)
    configure_logging(debug=True)
    configure_logging(debug=True)
    
    # Check that there's only one handler
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1


def test_logger_exists():
    """Test that the module-level logger is created."""
    from aimodelshare.moral_compass.apps import model_building_game
    
    assert hasattr(model_building_game, 'logger')
    assert isinstance(model_building_game.logger, logging.Logger)


def test_create_app_with_debug_flag():
    """Test that create_model_building_game_app accepts debug parameter."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Should not raise any errors
    app = create_model_building_game_app(debug=True)
    assert app is not None
    
    # Check logging was configured
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_create_app_with_q_flag():
    """Test that create_model_building_game_app accepts q parameter."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Should not raise any errors
    app = create_model_building_game_app(q=True)
    assert app is not None
    
    # Check logging was configured
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_launch_app_accepts_debug_flag():
    """Test that launch_model_building_game_app signature includes debug parameter."""
    from aimodelshare.moral_compass.apps.model_building_game import launch_model_building_game_app
    import inspect
    
    # Get function signature
    sig = inspect.signature(launch_model_building_game_app)
    
    # Check that debug parameter exists
    assert 'debug' in sig.parameters
    assert 'q' in sig.parameters


def test_launch_app_accepts_q_flag():
    """Test that launch_model_building_game_app signature includes q parameter."""
    from aimodelshare.moral_compass.apps.model_building_game import launch_model_building_game_app
    import inspect
    
    # Get function signature
    sig = inspect.signature(launch_model_building_game_app)
    
    # Check that q parameter exists
    assert 'q' in sig.parameters


def test_logging_output_captured():
    """Test that logging output is properly captured when debug=True."""
    from aimodelshare.moral_compass.apps.model_building_game import configure_logging, logger
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Configure with debug=True
    configure_logging(debug=True)
    
    # Capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    test_logger = logging.getLogger('aimodelshare.moral_compass.apps.model_building_game')
    test_logger.addHandler(handler)
    
    # Log a test message
    test_logger.debug("Test debug message")
    
    # Get output
    output = stream.getvalue()
    
    # Check that message was captured
    assert "Test debug message" in output
    
    # Clean up
    test_logger.removeHandler(handler)


def test_backward_compatibility():
    """Test that create_model_building_game_app can be called without new parameters."""
    from aimodelshare.moral_compass.apps.model_building_game import create_model_building_game_app
    
    # Reset logging
    logging.root.handlers.clear()
    
    # Should work with no parameters (backward compatibility)
    app = create_model_building_game_app()
    assert app is not None
    
    # Should work with only theme parameter (backward compatibility)
    app = create_model_building_game_app(theme_primary_hue="indigo")
    assert app is not None
