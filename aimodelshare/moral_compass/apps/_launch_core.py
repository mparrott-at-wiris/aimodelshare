"""
Centralized launch utilities and configuration for Moral Compass Gradio apps.
"""
import contextlib
import inspect
import os
import sys
from typing import Optional, List, Dict, Any

try:
    import gradio as gr
except ImportError:
    gr = None

_active_demos: List["gr.Blocks"] = []
_theme_singleton: Optional["gr.Theme"] = None


def get_theme(primary_hue: str = "indigo") -> "gr.Theme":
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")
    global _theme_singleton
    if _theme_singleton is None:
        _theme_singleton = gr.themes.Soft(primary_hue=primary_hue)
    return _theme_singleton


def apply_queue(demo: "gr.Blocks",
                default_concurrency_limit: int = 2,
                max_size: int = 32,
                status_update_rate: float = 1.0) -> "gr.Blocks":
    if gr is None:
        raise ImportError("Gradio is required.")
    try:
        demo.queue(default_concurrency_limit=default_concurrency_limit,
                   max_size=max_size,
                   status_update_rate=status_update_rate)
    except TypeError:
        try:
            demo.queue()
        except Exception:
            pass
    return demo


def register(demo: "gr.Blocks") -> None:
    if demo not in _active_demos:
        _active_demos.append(demo)


def close_all_apps() -> None:
    for demo in _active_demos:
        try:
            demo.close()
        except Exception:
            pass
    _active_demos.clear()


def _filter_launch_kwargs(demo: "gr.Blocks", launch_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    try:
        sig = inspect.signature(demo.launch)
        allowed = set(sig.parameters.keys())
        return {k: v for k, v in launch_kwargs.items() if k in allowed}
    except Exception:
        return {k: v for k, v in launch_kwargs.items() if k in {"share", "inline", "debug", "height"}}


def _ensure_watch_fd_thread():
    """
    Workaround for environments where OutStream lacks watch_fd_thread attribute.
    Adds a dummy thread object with a no-op join() to avoid AttributeError in ipykernel close().
    """
    class _DummyThread:
        def join(self): pass
    for stream in (sys.stdout, sys.stderr):
        if type(stream).__name__ == "OutStream" and not hasattr(stream, "watch_fd_thread"):
            stream.watch_fd_thread = _DummyThread()
            # Prevent attempts to start watching
            if not hasattr(stream, "_should_watch"):
                stream._should_watch = False


def launch_blocks(
    demo: "gr.Blocks",
    height: int = 800,
    share: bool = False,
    debug: bool = False,
    inline: bool = True,
    prevent_thread_lock: bool = False,  # changed default to False for stability
    quiet: bool = False,                # changed default to False to avoid stream issues
    inbrowser: bool | None = None,
    server_port: int | None = None,
    server_name: str | None = None,
    width: int | None = None
) -> None:
    """
    Launch Gradio Blocks with Gradio 5.49.1 compatibility.

    Adjusted defaults:
      prevent_thread_lock=False for notebook stability.
      quiet=False to avoid OutStream close attribute errors.
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")

    register(demo)
    _ensure_watch_fd_thread()

    launch_kwargs: Dict[str, Any] = {
        "share": share,
        "inline": inline,
        "debug": debug,
        "height": height,
        "prevent_thread_lock": prevent_thread_lock,
        "inbrowser": inbrowser,
        "server_port": server_port,
        "server_name": server_name,
        "width": width,
    }
    launch_kwargs = {k: v for k, v in launch_kwargs.items() if v is not None}
    filtered = _filter_launch_kwargs(demo, launch_kwargs)

    if quiet:
        # Only suppress if OutStream has the needed attribute, otherwise skip suppression
        if hasattr(sys.stdout, "watch_fd_thread"):
            with contextlib.redirect_stdout(open(os.devnull, "w")), \
                 contextlib.redirect_stderr(open(os.devnull, "w")):
                demo.launch(**filtered)
        else:
            demo.launch(**filtered)
    else:
        demo.launch(**filtered)
