"""
Lazy export layer for Moral Compass Gradio app factories.

Includes language-specific model building game variants:
- model_building_app_en.py
- model_building_app_ca.py
- model_building_app_es.py

If you rename files to model_building_game_<lang>.py, update _EXPORT_MAP accordingly.
"""

import importlib
import logging

logger = logging.getLogger(__name__)

_EXPORT_MAP = {
    "create_tutorial_app": ("tutorial", "create_tutorial_app"),
    "launch_tutorial_app": ("tutorial", "launch_tutorial_app"),
    "create_judge_app": ("judge", "create_judge_app"),
    "launch_judge_app": ("judge", "launch_judge_app"),
    "create_ai_consequences_app": ("ai_consequences", "create_ai_consequences_app"),
    "launch_ai_consequences_app": ("ai_consequences", "launch_ai_consequences_app"),
    "create_what_is_ai_app": ("what_is_ai", "create_what_is_ai_app"),
    "launch_what_is_ai_app": ("what_is_ai", "launch_what_is_ai_app"),
    # Legacy generic game
    "create_model_building_game_app": ("model_building_game", "create_model_building_game_app"),
    "launch_model_building_game_app": ("model_building_game", "launch_model_building_game_app"),
    # Beginner variant
    "create_model_building_game_beginner_app": ("model_building_game_beginner", "create_model_building_game_beginner_app"),
    "launch_model_building_game_beginner_app": ("model_building_game_beginner", "launch_model_building_game_beginner_app"),
    # Language-specific (adjusted to actual filenames model_building_app_<lang>.py)
    "create_model_building_game_en_app": ("model_building_app_en", "create_model_building_game_en_app"),
    "launch_model_building_game_en_app": ("model_building_app_en", "launch_model_building_game_en_app"),
    "create_model_building_game_ca_app": ("model_building_app_ca", "create_model_building_game_ca_app"),
    "launch_model_building_game_ca_app": ("model_building_app_ca", "launch_model_building_game_ca_app"),
    "create_model_building_game_es_app": ("model_building_app_es", "create_model_building_game_es_app"),
    "launch_model_building_game_es_app": ("model_building_app_es", "launch_model_building_game_es_app"),
    # Other apps
    "create_ethical_revelation_app": ("ethical_revelation", "create_ethical_revelation_app"),
    "launch_ethical_revelation_app": ("ethical_revelation", "launch_ethical_revelation_app"),
    "create_moral_compass_challenge_app": ("moral_compass_challenge", "create_moral_compass_challenge_app"),
    "launch_moral_compass_challenge_app": ("moral_compass_challenge", "launch_moral_compass_challenge_app"),

    # NEW: split Bias Detective into two explicit modules (part1 uses current code;
    # part2 is the temporary placeholder module). Ensure files bias_detective_part1.py
    # and bias_detective_part2.py exist under this package.
    "create_bias_detective_part1_app": ("bias_detective_part1", "create_bias_detective_part1_app"),
    "launch_bias_detective_part1_app": ("bias_detective_part1", "launch_bias_detective_part1_app"),
    "create_bias_detective_part2_app": ("bias_detective_part2", "create_bias_detective_part2_app"),
    "launch_bias_detective_part2_app": ("bias_detective_part2", "launch_bias_detective_part2_app"),

    "create_fairness_fixer_app": ("fairness_fixer", "create_fairness_fixer_app"),
    "launch_fairness_fixer_app": ("fairness_fixer", "launch_fairness_fixer_app"),
    "create_justice_equity_upgrade_app": ("justice_equity_upgrade", "create_justice_equity_upgrade_app"),
    "launch_justice_equity_upgrade_app": ("justice_equity_upgrade", "launch_justice_equity_upgrade_app"),
}

__all__ = list(_EXPORT_MAP.keys())

def __getattr__(name: str):
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
    return sorted({m for (m, _) in _EXPORT_MAP.values()})
