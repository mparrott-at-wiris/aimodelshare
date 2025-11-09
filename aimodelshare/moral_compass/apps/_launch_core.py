"""
Centralized launch utilities and configuration for Moral Compass Gradio apps.

This module provides:
- Queue configuration and attachment
- Unified launch function with proper settings for Colab
- Theme singleton for consistent styling
- Demo registration and cleanup
"""
import contextlib
import os
from typing import Optional, List

try:
    import gradio as gr
except ImportError:
    gr = None


# Global registry of active demos for cleanup
_active_demos: List["gr.Blocks"] = []

# Shared theme instance
_theme_singleton: Optional["gr.Theme"] = None


def get_theme(primary_hue: str = "indigo") -> "gr.Theme":
    """
    Get or create a shared theme instance.
    
    Args:
        primary_hue: Primary color hue for the theme.
    
    Returns:
        gr.Theme: A Gradio theme instance.
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
    Attach queue to a Gradio Blocks instance with optimal settings.
    
    Args:
        demo: Gradio Blocks instance to configure.
        default_concurrency_limit: Maximum number of concurrent requests.
        max_size: Maximum queue size.
        status_update_rate: How often to update queue status (seconds).
    
    Returns:
        gr.Blocks: The demo with queue configured.
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")
    
    demo.queue(
        default_concurrency_limit=default_concurrency_limit,
        max_size=max_size,
        status_update_rate=status_update_rate
    )
    return demo


def register(demo: "gr.Blocks") -> None:
    """
    Register a demo for cleanup tracking.
    
    Args:
        demo: Gradio Blocks instance to register.
    """
    global _active_demos
    if demo not in _active_demos:
        _active_demos.append(demo)


def close_all_apps() -> None:
    """
    Close all registered Gradio demos.
    
    This is useful for cleanup in notebook environments where multiple
    demos might be launched in sequence.
    """
    global _active_demos
    for demo in _active_demos:
        try:
            demo.close()
        except Exception:
            pass  # Ignore errors during cleanup
    _active_demos.clear()


def launch_blocks(
    demo: "gr.Blocks",
    height: int = 800,
    share: bool = False,
    debug: bool = False,
    inline: bool = True,
    prevent_thread_lock: bool = True,
    show_api: bool = False,
    quiet: bool = True
) -> None:
    """
    Launch a Gradio Blocks instance with optimal settings for Colab.
    
    This function centralizes the launch logic to ensure consistent behavior
    across all Moral Compass apps. It:
    - Suppresses output if quiet=True
    - Uses inline mode by default (for notebooks)
    - Disables API endpoints
    - Disables analytics
    - Prevents thread locks (allows multiple launches)
    
    Args:
        demo: Gradio Blocks instance to launch.
        height: Height of the iframe in pixels (for inline mode).
        share: Whether to create a public share link.
        debug: Whether to enable debug mode.
        inline: Whether to display inline in notebooks.
        prevent_thread_lock: Whether to prevent thread locking.
        show_api: Whether to show API documentation.
        quiet: Whether to suppress stdout/stderr during launch.
    """
    if gr is None:
        raise ImportError("Gradio is required. Install with `pip install gradio`.")
    
    # Register the demo for cleanup
    register(demo)
    
    # Prepare launch kwargs
    launch_kwargs = {
        "share": share,
        "inline": inline,
        "debug": debug,
        "height": height,
        "prevent_thread_lock": prevent_thread_lock,
        "show_api": show_api,
        # Disable analytics for privacy
        "analytics_enabled": False,
        # Disable API endpoints
        "api_open": False,
    }
    
    # Launch with optional output suppression
    if quiet:
        with contextlib.redirect_stdout(open(os.devnull, 'w')), \
             contextlib.redirect_stderr(open(os.devnull, 'w')):
            demo.launch(**launch_kwargs)
    else:
        demo.launch(**launch_kwargs)
