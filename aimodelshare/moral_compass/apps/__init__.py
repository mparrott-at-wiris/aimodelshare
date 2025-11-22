"""
Lazy export layer for Moral Compass Gradio app factories.

Previously this module eagerly imported all app modules, causing Cloud Run
startup failures if any heavy dependency (pandas, scikit-learn, aimodelshare)
was missing or slow. We now do on-demand (lazy) imports.

Public factories & launch helpers are resolved dynamically via __getattr__.

Usage:
from aimodelshare.moral_compass.apps.tutorial import create_tutorial_app
(or) from aimodelshare.moral_compass.apps import create_tutorial_app  # lazy
"""

import importlib
import logging

logger = logging.getLogger(__name__)

# Map exported attribute -> (module_name, symbol)
_EXPORT_MAP = {
    "create_tutorial_app": ("tutorial", "create_tutorial_app"),
    "launch_tutorial_app": ("tutorial", "launch_tutorial_app"),
    "create_judge_app": ("judge", "create_judge_app"),
    "launch_judge_app": ("judge", "launch_judge_app"),
    "create_ai_consequences_app": ("ai_consequences", "create_ai_consequences_app"),
    "launch_ai_consequences_app": ("ai_consequences", "launch_ai_consequences_app"),
    "create_what_is_ai_app": ("what_is_ai", "create_what_is_ai_app"),
    "launch_what_is_ai_app": ("what_is_ai", "launch_what_is_ai_app"),
    "create_model_building_game_app": ("model_building_game", "create_model_building_game_app"),
    "launch_model_building_game_app": ("model_building_game", "launch_model_building_game_app"),
    "create_model_building_game_beginner_app": ("model_building_game_beginner", "create_model_building_game_beginner_app"),
    "launch_model_building_game_beginner_app": ("model_building_game_beginner", "launch_model_building_game_beginner_app"),
    "create_ethical_revelation_app": ("ethical_revelation", "create_ethical_revelation_app"),
    "launch_ethical_revelation_app": ("ethical_revelation", "launch_ethical_revelation_app"),
    "create_moral_compass_challenge_app": ("moral_compass_challenge", "create_moral_compass_challenge_app"),
    "launch_moral_compass_challenge_app": ("moral_compass_challenge", "launch_moral_compass_challenge_app"),
    "create_bias_detective_app": ("bias_detective", "create_bias_detective_app"),
    "launch_bias_detective_app": ("bias_detective", "launch_bias_detective_app"),
    "create_fairness_fixer_app": ("fairness_fixer", "create_fairness_fixer_app"),
    "launch_fairness_fixer_app": ("fairness_fixer", "launch_fairness_fixer_app"),
    "create_justice_equity_upgrade_app": ("justice_equity_upgrade", "create_justice_equity_upgrade_app"),
    "launch_justice_equity_upgrade_app": ("justice_equity_upgrade", "launch_justice_equity_upgrade_app"),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str):
    """Dynamically import requested factory/launcher."""
    if name not in _EXPORT_MAP:
        raise AttributeError(f"Module '{__name__}' has no attribute '{name}'")

    mod_name, symbol = _EXPORT_MAP[name]
    try:
        module = importlib.import_module(f".{mod_name}", __name__)
    except Exception as e:
        logger.error(f"Failed importing app module '{mod_name}' for symbol '{name}': {e}")
        raise
    try:
        return getattr(module, symbol)
    except AttributeError as e:
        logger.error(f"Symbol '{symbol}' not found in module '{mod_name}': {e}")
        raise


def list_available_apps():
    """Utility: return list of logical app names (for diagnostics)."""
    return sorted({m for (m, _) in _EXPORT_MAP.values()})
