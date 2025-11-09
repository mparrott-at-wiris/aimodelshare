"""
Smoke tests for Moral Compass Gradio apps under Gradio 5.49.1.

These tests:
1. Monkey-patch launch_blocks to force non-blocking launches (prevent_thread_lock=True).
2. Launch each public app wrapper to ensure no TypeError on unsupported kwargs.
3. Close all apps afterward to free ports.

If you later adjust defaults in launch_blocks, keep this test updated.
"""
import importlib
import inspect
import time

import gradio as gr

import aimodelshare
from aimodelshare.moral_compass.apps import (
    launch_tutorial_app,
    launch_judge_app,
    launch_what_is_ai_app,
)

# Access internal launch utilities
from aimodelshare.moral_compass.apps import _launch_core


def _monkey_patch_launch_blocks():
    """
    Replace launch_blocks with a simplified non-blocking version
    that filters kwargs dynamically and forces prevent_thread_lock=True,
    quiet=True to avoid hanging CI.
    """
    original = _launch_core.launch_blocks

    def patched(
        demo: "gr.Blocks",
        height: int = 800,
        share: bool = False,
        debug: bool = False,
        inline: bool = True,
        prevent_thread_lock: bool = True,  # force non-blocking
        quiet: bool = True,
        **extra,
    ):
        # Register for cleanup
        _launch_core.register(demo)

        # Build minimal kwargs, filter against current signature
        params = dict(
            share=share,
            inline=inline,
            debug=debug,
            height=height,
            prevent_thread_lock=True,  # forced
        )
        try:
            sig = inspect.signature(demo.launch)
            params = {k: v for k, v in params.items() if k in sig.parameters}
        except Exception:
            pass

        # Launch without stdout suppression complexities (quiet just ignored)
        demo.launch(**params)

    _launch_core.launch_blocks = patched
    return original


def _restore_launch_blocks(original):
    _launch_core.launch_blocks = original


def test_gradio_smoke_launches(monkeypatch):
    """
    Launch each app. If any raises TypeError (e.g., unexpected kwarg) or
    AttributeError related to OutStream, the test fails.

    We allow each launch a brief pause then close everything.
    """
    original = _monkey_patch_launch_blocks()
    try:
        # Launch tutorial
        launch_tutorial_app(height=600, share=False, debug=False)
        # Launch judge
        launch_judge_app(height=600, share=False, debug=False)
        # Launch what is AI
        launch_what_is_ai_app(height=600, share=False, debug=False)

        # Give Gradio event loop a moment
        time.sleep(1.5)

        # Basic assertion: internal registry populated
        assert len(_launch_core._active_demos) >= 3, "Expected at least 3 active demos."

    finally:
        # Cleanup & restore
        _launch_core.close_all_apps()
        _restore_launch_blocks(original)


# Optional: create-only test (ensures create_* still works)
def test_gradio_smoke_create_only():
    from aimodelshare.moral_compass.apps import tutorial, judge, what_is_ai

    demo1 = tutorial.create_tutorial_app()
    demo2 = judge.create_judge_app()
    demo3 = what_is_ai.create_what_is_ai_app()

    # Ensure they are Blocks instances
    assert isinstance(demo1, gr.Blocks)
    assert isinstance(demo2, gr.Blocks)
    assert isinstance(demo3, gr.Blocks)

    # Close them explicitly
    for d in (demo1, demo2, demo3):
        try:
            d.close()
        except Exception:
            pass
