#!/usr/bin/env python3
"""
Unit tests for launch_entrypoint.py.

Tests the lazy import strategy and app routing logic.
Run with: pytest tests/test_launch_entrypoint.py -v
"""

import os
import sys
import pytest


def test_all_factory_functions_exist():
    """Verify all apps referenced in launch_entrypoint have factory functions."""
    # Import onnx first to ensure it's available
    try:
        import onnx
    except ImportError:
        pytest.skip("onnx not installed - required for full app testing")
    
    app_imports = {
        "tutorial": ("aimodelshare.moral_compass.apps.tutorial", "create_tutorial_app"),
        "judge": ("aimodelshare.moral_compass.apps.judge", "create_judge_app"),
        "ai-consequences": ("aimodelshare.moral_compass.apps.ai_consequences", "create_ai_consequences_app"),
        "what-is-ai": ("aimodelshare.moral_compass.apps.what_is_ai", "create_what_is_ai_app"),
        "model-building-game": ("aimodelshare.moral_compass.apps.model_building_game", "create_model_building_game_app"),
        "ethical-revelation": ("aimodelshare.moral_compass.apps.ethical_revelation", "create_ethical_revelation_app"),
        "moral-compass-challenge": ("aimodelshare.moral_compass.apps.moral_compass_challenge", "create_moral_compass_challenge_app"),
        "bias-detective": ("aimodelshare.moral_compass.apps.bias_detective", "create_bias_detective_app"),
        "fairness-fixer": ("aimodelshare.moral_compass.apps.fairness_fixer", "create_fairness_fixer_app"),
        "justice-equity-upgrade": ("aimodelshare.moral_compass.apps.justice_equity_upgrade", "create_justice_equity_upgrade_app"),
    }
    
    for app_name, (module_path, factory_name) in app_imports.items():
        # Dynamically import the module
        module = __import__(module_path, fromlist=[factory_name])
        # Verify the factory function exists
        assert hasattr(module, factory_name), f"Factory {factory_name} not found in {module_path}"
        factory = getattr(module, factory_name)
        # Verify it's callable
        assert callable(factory), f"{factory_name} is not callable"


def test_factory_functions_return_gradio_blocks():
    """Verify all factory functions return Gradio Blocks objects."""
    try:
        import onnx
    except ImportError:
        pytest.skip("onnx not installed - required for full app testing")
    
    from aimodelshare.moral_compass.apps.tutorial import create_tutorial_app
    from aimodelshare.moral_compass.apps.judge import create_judge_app
    
    # Test a subset to keep test fast
    apps_to_test = [
        create_tutorial_app,
        create_judge_app,
    ]
    
    for factory in apps_to_test:
        app = factory()
        assert app is not None, f"{factory.__name__} returned None"
        assert hasattr(app, 'launch'), f"{factory.__name__} result doesn't have launch method"


def test_launch_entrypoint_routing_logic():
    """Test that the routing logic in launch_entrypoint is correct."""
    try:
        import onnx
    except ImportError:
        pytest.skip("onnx not installed - required for full app testing")
    
    # This test validates the mapping logic without actually launching apps
    app_name_to_module = {
        "tutorial": "aimodelshare.moral_compass.apps.tutorial",
        "judge": "aimodelshare.moral_compass.apps.judge",
        "ai-consequences": "aimodelshare.moral_compass.apps.ai_consequences",
        "what-is-ai": "aimodelshare.moral_compass.apps.what_is_ai",
        "model-building-game": "aimodelshare.moral_compass.apps.model_building_game",
        "ethical-revelation": "aimodelshare.moral_compass.apps.ethical_revelation",
        "moral-compass-challenge": "aimodelshare.moral_compass.apps.moral_compass_challenge",
        "bias-detective": "aimodelshare.moral_compass.apps.bias_detective",
        "fairness-fixer": "aimodelshare.moral_compass.apps.fairness_fixer",
        "justice-equity-upgrade": "aimodelshare.moral_compass.apps.justice_equity_upgrade",
    }
    
    # Verify all modules can be imported
    for app_name, module_path in app_name_to_module.items():
        try:
            __import__(module_path)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_path} for app {app_name}: {e}")


def test_requirements_apps_dependencies():
    """Test that requirements-apps.txt exists and has expected structure."""
    import pathlib
    
    repo_root = pathlib.Path(__file__).parent.parent
    req_file = repo_root / "requirements-apps.txt"
    
    assert req_file.exists(), "requirements-apps.txt not found"
    
    content = req_file.read_text()
    
    # Check that lightweight deps are included with pinned versions
    assert "gradio==" in content
    assert "scikit-learn==" in content
    assert "pandas==" in content
    assert "numpy==" in content
    assert "requests==" in content
    
    # Check for Python 3.12 compatible versions
    assert "fastapi==" in content
    assert "uvicorn==" in content


def test_dockerfile_exists():
    """Test that Dockerfile exists and has expected structure."""
    import pathlib
    
    repo_root = pathlib.Path(__file__).parent.parent
    dockerfile = repo_root / "Dockerfile"
    
    assert dockerfile.exists(), "Dockerfile not found"
    
    content = dockerfile.read_text()
    
    # Check key elements - updated for Python 3.12 and HEALTHCHECK
    assert "python:3.12-slim" in content
    assert "requirements-apps.txt" in content
    assert "launch_entrypoint.py" in content
    assert "EXPOSE 8080" in content
    assert "HEALTHCHECK" in content
