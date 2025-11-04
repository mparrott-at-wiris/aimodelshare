"""
UI application factory exports for Moral Compass challenge.

This subpackage contains Gradio (and potentially other UI) apps that
support interactive learning flows around the Justice & Equity Challenge.

Design goals:
- Keep API and challenge logic separate from presentation/UI
- Provide factory-style functions that return Gradio Blocks instances
- Allow notebooks to launch apps with a single import and call
"""
from .tutorial import create_tutorial_app, launch_tutorial_app

__all__ = [
    "create_tutorial_app",
    "launch_tutorial_app",
]
