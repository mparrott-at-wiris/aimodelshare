"""
Smoke tests for Moral Compass Gradio apps under Gradio 5.49.1.

This test ensures that each launch_* wrapper can execute without raising
TypeError (unexpected kwargs) or AttributeError in a non-notebook CI environment.

Key points:
- We monkey patch ALL references to launch_blocks (including those imported
  into individual app modules) because they were imported by name at module import time.
- We force inline=False (notebook rendering isn't needed in CI) and
  prevent_thread_lock=True (non-blocking).
- We immediately close each demo after a short wait.
"""

import inspect
import time
import importlib

import gradio as gr

# Import the apps package root to access modules
from aimodelshare.moral_compass.apps import (
    tutorial,
    judge,
    what_is_ai,
    ai_consequences,
    _launch_core,
    launch_tutorial_app,
    launch_judge_app,
    launch_what_is_ai_app,
    launch_ai_consequences_app,
)


def _patch_all_launch_blocks():
    """
    Monkey-patch launch_blocks everywhere:
    - In _launch_core
    - In already-imported app modules where launch_blocks was imported directly

    Returns the originals so they can be restored.
    """
    originals = {
        "_launch_core": _launch_core.launch_blocks,
        "tutorial": getattr(tutorial, "launch_blocks", None),
        "judge": getattr(judge, "launch_blocks", None),
        "what_is_ai": getattr(what_is_ai, "launch_blocks", None),
        "ai_consequences": getattr(ai_consequences, "launch_blocks", None),
    }

    def patched_launch_blocks(
        demo: "gr.Blocks",
        height: int = 800,
        share: bool = False,
        debug: bool = False,
        inline: bool = False,          # Force False for CI
        prevent_thread_lock: bool = True,
        quiet: bool = True,
        inbrowser: bool | None = False,
        server_port: int | None = None,
        server_name: str | None = "127.0.0.1",
        width: int | None = None,
        **extra,
    ):
        # Register demo so close_all_apps can clean it
        _launch_core.register(demo)

        # Build minimal kwargs and filter by signature
        params = dict(
            share=share,
            inline=inline,
            debug=debug,
            height=height,
            prevent_thread_lock=prevent_thread_lock,
            inbrowser=inbrowser,
            server_port=server_port,
            server_name=server_name,
            width=width,
        )
        params = {k: v for k, v in params.items() if v is not None}

        try:
            sig = inspect.signature(demo.launch)
            params = {k: v for k, v in params.items() if k in sig.parameters}
        except Exception:
            pass

        # Launch
        demo.launch(**params)

    # Patch _launch_core canonical
    _launch_core.launch_blocks = patched_launch_blocks

    # Patch modules that imported launch_blocks directly (if present)
    for module in (tutorial, judge, what_is_ai, ai_consequences):
        if hasattr(module, "launch_blocks"):
            setattr(module, "launch_blocks", patched_launch_blocks)

    return originals


def _restore_all_launch_blocks(originals):
    _launch_core.launch_blocks = originals["_launch_core"]
    for mod_name, original in originals.items():
        if mod_name == "_launch_core":
            continue
        module = {
            "tutorial": tutorial,
            "judge": judge,
            "what_is_ai": what_is_ai,
            "ai_consequences": ai_consequences,
        }.get(mod_name)
        if module and original is not None:
            setattr(module, "launch_blocks", original)


def test_gradio_smoke_launches():
    originals = _patch_all_launch_blocks()
    errors = []
    try:
        # Launch each app wrapper
        for fn, label in [
            (launch_tutorial_app, "tutorial"),
            (launch_judge_app, "judge"),
            (launch_what_is_ai_app, "what_is_ai"),
            (launch_ai_consequences_app, "ai_consequences"),
        ]:
            try:
                fn(height=600, share=False, debug=False)
            except Exception as e:
                errors.append((label, type(e).__name__, str(e)))

        # Allow any background startup to settle
        time.sleep(2.0)

        # Basic verification
        assert len(_launch_core._active_demos) >= 1, "No demos registered."
        assert not errors, f"Launch errors encountered: {errors}"

    finally:
        # Cleanup
        _launch_core.close_all_apps()
        _restore_all_launch_blocks(originals)


def test_create_functions_only():
    """
    Ensure create_* functions return Blocks instances without launching.
    """
    demo1 = tutorial.create_tutorial_app()
    demo2 = judge.create_judge_app()
    demo3 = what_is_ai.create_what_is_ai_app()
    demo4 = ai_consequences.create_ai_consequences_app()

    for d in (demo1, demo2, demo3, demo4):
        assert isinstance(d, gr.Blocks)
        try:
            d.close()
        except Exception:
            pass
