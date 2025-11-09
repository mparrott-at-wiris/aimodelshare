"""
Centralized launch utilities and configuration for Moral Compass Gradio apps.

This module provides:
- Queue configuration and attachment
- Unified launch function with proper settings for notebook environments
- Theme singleton for consistent styling
- Demo registration and cleanup
"""
import contextlib
import inspect
import os
from typing import Optional, List, Dict, Any

try:
    import gradio as gr
except ImportError:
    gr = None  # Deferred error until functions actually need Gradio


# Global registry of active demos for cleanup
_active_demos: List["gr.Blocks"] = []

# Shared theme instance
_theme_singleton: Optional["gr.Theme"] = None


def get_theme(primary_hue: str = "indigo") -> "gr.Theme":
    """
    Get or create a shared theme instance.
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")
    global _theme_singleton
    if _theme_singleton is None:
        _theme_singleton = gr.themes.Soft(primary_hue=primary_hue)
    return _theme_singleton


def apply_queue(
    demo: "gr.Blocks",
    default_concurrency_limit: int = 2,
    max_size: int = 32,
    status_update_rate: float = 1.0
) -> "gr.Blocks":
    """
    Attach a queue to the Gradio Blocks instance.

    Gradio 5.x still supports queue(), but parameter names may evolve.
    We attempt a best-effort call; if signature changes, we fail gracefully.
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")

    try:
        # Try the common v4/v5 parameter names.
        demo.queue(
            default_concurrency_limit=default_concurrency_limit,
            max_size=max_size,
            status_update_rate=status_update_rate
        )
    except TypeError:
        # Fallback: call with no kwargs (let Gradio use defaults)
        try:
            demo.queue()
        except Exception:
            # If queue is entirely unsupported or changed drastically, ignore.
            pass
    return demo


def register(demo: "gr.Blocks") -> None:
    """
    Register a demo for later cleanup.
    """
    global _active_demos
    if demo not in _active_demos:
        _active_demos.append(demo)


def close_all_apps() -> None:
    """
    Close all registered Gradio demos (useful for notebook restarts).
    """
    global _active_demos
    for demo in _active_demos:
        try:
            demo.close()
        except Exception:
            pass
    _active_demos.clear()


def _filter_launch_kwargs(demo: "gr.Blocks", launch_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter kwargs to only those supported by the current Gradio version.

    This avoids TypeError when Gradio removes or renames parameters.
    """
    try:
        sig = inspect.signature(demo.launch)
        allowed = set(sig.parameters.keys())
        return {k: v for k, v in launch_kwargs.items() if k in allowed}
    except Exception:
        # Fallback to a conservative subset
        minimal = {"share", "inline", "debug", "height", "width"}
        return {k: v for k, v in launch_kwargs.items() if k in minimal}


def launch_blocks(
    demo: "gr.Blocks",
    height: int = 800,
    width: int | None = None,
    share: bool = False,
    debug: bool = False,
    inline: bool = True,
    prevent_thread_lock: bool = True,
    quiet: bool = True,
    inbrowser: bool | None = None,
    server_port: int | None = None,
    server_name: str | None = None
) -> None:
    """
    Launch a Gradio Blocks instance with notebook-friendly defaults.

    Removed deprecated/unsupported parameters (analytics_enabled, api_open, show_api)
    for Gradio 5.49.1.

    Args:
        demo: The Gradio Blocks instance.
        height: Iframe height (for inline mode in notebooks).
        width: Optional iframe width.
        share: Whether to request a public share link (may be limited in some v5 builds).
        debug: Enable debug logging.
        inline: Render inline in Jupyter/Colab if supported.
        prevent_thread_lock: Allow cell execution to continue after launch.
        quiet: Suppress stdout/stderr during launch if True.
        inbrowser: Open in a browser tab automatically (optional).
        server_port: Specify a port (optional).
        server_name: Specify host name (optional).
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")

    register(demo)

    # Candidate kwargs (prune dynamically)
    launch_kwargs: Dict[str, Any] = {
        "share": share,
        "inline": inline,
        "debug": debug,
        "height": height,
        "width": width,
        "prevent_thread_lock": prevent_thread_lock,
        "inbrowser": inbrowser,
        "server_port": server_port,
        "server_name": server_name,
        # Do NOT include removed kwargs: analytics_enabled, api_open, show_api
    }

    # Remove None values to avoid passing them explicitly
    launch_kwargs = {k: v for k, v in launch_kwargs.items() if v is not None}

    filtered = _filter_launch_kwargs(demo, launch_kwargs)

    if quiet:
        with contextlib.redirect_stdout(open(os.devnull, "w")), \
             contextlib.redirect_stderr(open(os.devnull, "w")):
            demo.launch(**filtered)
    else:
        demo.launch(**filtered)
