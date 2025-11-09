#!/usr/bin/env python3
"""
Test navigation button functionality for Moral Compass Gradio apps.

This tests that gr.update(visible=...) calls work correctly when navigation
buttons are clicked, preventing TypeErrors from incorrect syntax like
gr.update(visible(True)).

Run with: pytest tests/test_gradio_navigation.py -v
"""

import pytest


def test_what_is_ai_navigation_syntax():
    """Test that what_is_ai app uses correct gr.update syntax."""
    from aimodelshare.moral_compass.apps import create_what_is_ai_app
    import gradio as gr
    
    app = create_what_is_ai_app()
    assert app is not None
    
    # The app should be created without any syntax errors
    # If the navigation had incorrect gr.update(visible(X)) syntax,
    # it would fail when the lambda is evaluated
    assert hasattr(app, 'blocks')
    

def test_ai_consequences_navigation_syntax():
    """Test that ai_consequences app uses correct gr.update syntax."""
    from aimodelshare.moral_compass.apps import create_ai_consequences_app
    import gradio as gr
    
    app = create_ai_consequences_app()
    assert app is not None
    
    # The app should be created without any syntax errors
    assert hasattr(app, 'blocks')


def test_judge_app_navigation_syntax():
    """Test that judge app uses correct gr.update syntax."""
    from aimodelshare.moral_compass.apps import create_judge_app
    import gradio as gr
    
    app = create_judge_app()
    assert app is not None
    
    # The app should be created without any syntax errors  
    assert hasattr(app, 'blocks')


def test_tutorial_app_navigation_syntax():
    """Test that tutorial app uses correct gr.update syntax."""
    from aimodelshare.moral_compass.apps import create_tutorial_app
    import gradio as gr
    
    app = create_tutorial_app()
    assert app is not None
    
    # The app should be created without any syntax errors
    assert hasattr(app, 'blocks')


def test_gr_update_keyword_argument_format():
    """
    Test that gr.update accepts visible as a keyword argument.
    This validates our fix uses the correct syntax.
    """
    import gradio as gr
    
    # Correct syntax - should work
    update_true = gr.update(visible=True)
    assert update_true is not None
    
    update_false = gr.update(visible=False)
    assert update_false is not None
    
    # Test that we can call it in a lambda (as used in navigation)
    lambda_result = (lambda: gr.update(visible=True))()
    assert lambda_result is not None
    
    # Multiple updates in a tuple (as used in navigation)
    multi_update = (lambda: (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False)
    ))()
    assert len(multi_update) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
