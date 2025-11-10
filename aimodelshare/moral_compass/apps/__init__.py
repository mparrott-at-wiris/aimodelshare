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

# Catalan versions
from .tutorial_ca import create_tutorial_app as create_tutorial_app_ca, launch_tutorial_app as launch_tutorial_app_ca
from .judge_ca import create_judge_app as create_judge_app_ca, launch_judge_app as launch_judge_app_ca
from .ai_consequences_ca import create_ai_consequences_app as create_ai_consequences_app_ca, launch_ai_consequences_app as launch_ai_consequences_app_ca
from .what_is_ai_ca import create_what_is_ai_app as create_what_is_ai_app_ca, launch_what_is_ai_app as launch_what_is_ai_app_ca

# Spanish versions
from .tutorial_es import create_tutorial_app as create_tutorial_app_es, launch_tutorial_app as launch_tutorial_app_es
from .judge_es import create_judge_app as create_judge_app_es, launch_judge_app as launch_judge_app_es
from .ai_consequences_es import create_ai_consequences_app as create_ai_consequences_app_es, launch_ai_consequences_app as launch_ai_consequences_app_es
from .what_is_ai_es import create_what_is_ai_app as create_what_is_ai_app_es, launch_what_is_ai_app as launch_what_is_ai_app_es

__all__ = [
    "create_tutorial_app",
    "launch_tutorial_app",
    "create_judge_app",
    "launch_judge_app",
    "create_ai_consequences_app",
    "launch_ai_consequences_app",
    "create_what_is_ai_app",
    "launch_what_is_ai_app",
    # Catalan versions
    "create_tutorial_app_ca",
    "launch_tutorial_app_ca",
    "create_judge_app_ca",
    "launch_judge_app_ca",
    "create_ai_consequences_app_ca",
    "launch_ai_consequences_app_ca",
    "create_what_is_ai_app_ca",
    "launch_what_is_ai_app_ca",
    # Spanish versions
    "create_tutorial_app_es",
    "launch_tutorial_app_es",
    "create_judge_app_es",
    "launch_judge_app_es",
    "create_ai_consequences_app_es",
    "launch_ai_consequences_app_es",
    "create_what_is_ai_app_es",
    "launch_what_is_ai_app_es",
]
