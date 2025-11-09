"""
Environment detection and launch utilities for Moral Compass apps.

This module provides helper functions to detect the runtime environment
(e.g., Google Colab) and find available ports for launching Gradio apps.
"""
import os
import socket


def in_colab() -> bool:
    """
    Detect if code is running inside Google Colab.
    
    Returns:
        bool: True if running in Colab, False otherwise.
    """
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def get_debug_mode() -> bool:
    """
    Check if debug mode is enabled via environment variable.
    
    Returns:
        bool: True if GRADIO_DEBUG or DEBUG is set, False otherwise.
    """
    return os.getenv("GRADIO_DEBUG", "").lower() in ("1", "true", "yes") or \
           os.getenv("DEBUG", "").lower() in ("1", "true", "yes")


def find_free_port(start_port: int = 7860, max_attempts: int = 100) -> int:
    """
    Find an available port for Gradio to bind to.
    
    Args:
        start_port: Port number to start searching from.
        max_attempts: Maximum number of ports to try.
    
    Returns:
        int: An available port number.
    
    Raises:
        RuntimeError: If no free port is found within max_attempts.
    """
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                # Bind to localhost only for security
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts}")
