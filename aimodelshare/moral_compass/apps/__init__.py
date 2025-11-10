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
from .judge import create_judge_app, launch_judge_app
from .ai_consequences import create_ai_consequences_app, launch_ai_consequences_app
from .what_is_ai import create_what_is_ai_app, launch_what_is_ai_app
from .ai_lead_engineer import create_ai_lead_engineer_app, launch_ai_lead_engineer_app

__all__ = [
    "create_tutorial_app",
    "launch_tutorial_app",
    "create_judge_app",
    "launch_judge_app",
    "create_ai_consequences_app",
    "launch_ai_consequences_app",
    "create_what_is_ai_app",
    "launch_what_is_ai_app",
    "create_ai_lead_engineer_app",
    "launch_ai_lead_engineer_app",
]
