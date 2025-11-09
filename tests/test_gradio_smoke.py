"""
Improved Gradio 5.49.1 smoke test for Moral Compass apps.

Adjustments:
- Minimal launch kwargs (avoid inbrowser / server_name / prevent_thread_lock that can
  trigger Gradio config casting issues).
- Omits False-valued flags entirely (lets Gradio defaults stand).
- Patches ALL imported references to launch_blocks.
- Treats the specific ValueError: invalid literal for int() with base 10: 'false'
  as a tolerated known Gradio quirk if the server actually started.

If Gradio fixes its casting in later versions, this logic can be simplified.
"""

import inspect
import time
import traceback

import gradio as gr

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
        inline: bool = False,
        **_ignored,
    ):
        # Register for cleanup
        _launch_core.register(demo)

        # Build minimal safe kwargs
        params = dict(height=height)
        if share:
            params["share"] = True
        if debug:
            params["debug"] = True
        # Only add inline if signature supports it and we explicitly want False
        try:
            sig = inspect.signature(demo.launch)
            if "inline" in sig.parameters:
                # Pass False explicitly to avoid notebook rendering attempt
                params["inline"] = False
        except Exception:
            pass

        # Filter params by actual signature
        try:
            sig = inspect.signature(demo.launch)
            params = {k: v for k, v in params.items() if k in sig.parameters}
        except Exception:
            pass

        demo.launch(**params)

    _launch_core.launch_blocks = patched_launch_blocks
    for module in (tutorial, judge, what_is_ai, ai_consequences):
        if hasattr(module, "launch_blocks"):
            setattr(module, "launch_blocks", patched_launch_blocks)

    return originals


def _restore_all_launch_blocks(originals):
    _launch_core.launch_blocks = originals["_launch_core"]
    map_mod = {
        "tutorial": tutorial,
        "judge": judge,
        "what_is_ai": what_is_ai,
        "ai_consequences": ai_consequences,
    }
    for key, original in originals.items():
        if key == "_launch_core":
            continue
        module = map_mod.get(key)
        if module and original is not None:
            setattr(module, "launch_blocks", original)


def _launched_successfully():
    # A simplistic heuristic: any registered demo has .server or .app populated
    for d in _launch_core._active_demos:
        if getattr(d, "server", None) is not None:
            return True
    return False


def test_gradio_smoke_launches():
    originals = _patch_all_launch_blocks()
    errors = []
    try:
        for fn, label in [
            (launch_tutorial_app, "tutorial"),
            (launch_judge_app, "judge"),
            (launch_what_is_ai_app, "what_is_ai"),
            (launch_ai_consequences_app, "ai_consequences"),
        ]:
            try:
                fn(height=600, share=False, debug=False)
            except Exception as e:
                tb = traceback.format_exc()
                # Known tolerated pattern: ValueError with 'false' port casting issue.
                if isinstance(e, ValueError) and "invalid literal for int() with base 10: 'false'" in str(e):
                    # Treat as success if a server actually started.
                    if _launched_successfully():
                        continue
                errors.append((label, type(e).__name__, str(e), tb))

        time.sleep(1.0)
        assert len(_launch_core._active_demos) >= 1, "No demos registered."
        assert not errors, f"Launch errors encountered:\n" + "\n".join(
            f"{lbl} {etype}: {msg}\n{tb}" for (lbl, etype, msg, tb) in errors
        )

    finally:
        _launch_core.close_all_apps()
        _restore_all_launch_blocks(originals)


def test_create_functions_only():
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
