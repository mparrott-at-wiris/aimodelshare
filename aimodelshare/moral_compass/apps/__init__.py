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
from .model_building_game import create_model_building_game_app, launch_model_building_game_app
from .model_building_game_beginner import create_model_building_game_beginner_app, launch_model_building_game_beginner_app
from .ethical_revelation import create_ethical_revelation_app, launch_ethical_revelation_app
from .moral_compass_challenge import create_moral_compass_challenge_app, launch_moral_compass_challenge_app
from .bias_detective import create_bias_detective_app, launch_bias_detective_app
from .fairness_fixer import create_fairness_fixer_app, launch_fairness_fixer_app
from .justice_equity_upgrade import create_justice_equity_upgrade_app, launch_justice_equity_upgrade_app

__all__ = [
    "create_tutorial_app",
    "launch_tutorial_app",
    "create_judge_app",
    "launch_judge_app",
    "create_ai_consequences_app",
    "launch_ai_consequences_app",
    "create_what_is_ai_app",
    "launch_what_is_ai_app",
    "create_model_building_game_app",
    "launch_model_building_game_app",
    "create_model_building_game_beginner_app",
    "launch_model_building_game_beginner_app",
    "create_ethical_revelation_app",
    "launch_ethical_revelation_app",
    "create_moral_compass_challenge_app",
    "launch_moral_compass_challenge_app",
    "create_bias_detective_app",
    "launch_bias_detective_app",
    "create_fairness_fixer_app",
    "launch_fairness_fixer_app",
    "create_justice_equity_upgrade_app",
    "launch_justice_equity_upgrade_app"
]
