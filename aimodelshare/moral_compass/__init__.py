"""
aimodelshare.moral_compass - Production-ready client for moral_compass REST API
"""
from ._version import __version__
from .api_client import (
    MoralcompassApiClient,
    MoralcompassTableMeta,
    MoralcompassUserStats,
    ApiClientError,
    NotFoundError,
    ServerError,
)
from .config import get_api_base_url, get_aws_region
from .challenge import ChallengeManager, JusticeAndEquityChallenge

# Optional UI helpers (Gradio may be an optional dependency)
try:
    from .apps import (
        create_tutorial_app, launch_tutorial_app,
        create_judge_app, launch_judge_app,
        create_ai_consequences_app, launch_ai_consequences_app,
        create_what_is_ai_app, launch_what_is_ai_app,
        create_model_building_game_app, launch_model_building_game_app,
        create_model_building_game_beginner_app, launch_model_building_game_beginner_app,
        # Language-specific games
        create_model_building_game_en_app, launch_model_building_game_en_app,
        create_model_building_game_ca_app, launch_model_building_game_ca_app,
        create_model_building_game_es_app, launch_model_building_game_es_app,
        # Final language-specific games
        create_model_building_game_en_final_app, launch_model_building_game_en_final_app,
        create_model_building_game_es_final_app, launch_model_building_game_es_final_app,
        create_model_building_game_ca_final_app, launch_model_building_game_ca_final_app,
        # Bias Detective split + language variants
        create_bias_detective_part1_app, launch_bias_detective_part1_app,
        create_bias_detective_part2_app, launch_bias_detective_part2_app,
        create_bias_detective_en_app, launch_bias_detective_en_app,
        create_bias_detective_es_app, launch_bias_detective_es_app,
        create_bias_detective_ca_app, launch_bias_detective_ca_app,
        # Fairness Fixer (generic + language variants) — NEW
        create_fairness_fixer_app, launch_fairness_fixer_app,
        create_fairness_fixer_en_app, launch_fairness_fixer_en_app,
        create_fairness_fixer_es_app, launch_fairness_fixer_es_app,
        create_fairness_fixer_ca_app, launch_fairness_fixer_ca_app,
        # Justice & Equity Upgrade (generic + language variants) — NEW
        create_justice_equity_upgrade_app, launch_justice_equity_upgrade_app,
        create_justice_equity_upgrade_en_app, launch_justice_equity_upgrade_en_app,
        create_justice_equity_upgrade_es_app, launch_justice_equity_upgrade_es_app,
        create_justice_equity_upgrade_ca_app, launch_justice_equity_upgrade_ca_app,
    )
except Exception:  # noqa: BLE001
    # Fallback if Gradio apps have an issue (e.g., Gradio not installed)
    create_tutorial_app = None
    launch_tutorial_app = None
    create_judge_app = None
    launch_judge_app = None
    create_ai_consequences_app = None
    launch_ai_consequences_app = None
    create_what_is_ai_app = None
    launch_what_is_ai_app = None
    create_model_building_game_app = None
    launch_model_building_game_app = None
    create_model_building_game_beginner_app = None
    launch_model_building_game_beginner_app = None
    # Language-specific games
    create_model_building_game_en_app = None
    launch_model_building_game_en_app = None
    create_model_building_game_ca_app = None
    launch_model_building_game_ca_app = None
    create_model_building_game_es_app = None
    launch_model_building_game_es_app = None
    # Final language-specific games
    create_model_building_game_en_final_app = None
    launch_model_building_game_en_final_app = None
    create_model_building_game_es_final_app = None
    launch_model_building_game_es_final_app = None
    create_model_building_game_ca_final_app = None
    launch_model_building_game_ca_final_app = None
    # Bias Detective split + language variants
    create_bias_detective_part1_app = None
    launch_bias_detective_part1_app = None
    create_bias_detective_part2_app = None
    launch_bias_detective_part2_app = None
    create_bias_detective_en_app = None
    launch_bias_detective_en_app = None
    create_bias_detective_es_app = None
    launch_bias_detective_es_app = None
    create_bias_detective_ca_app = None
    launch_bias_detective_ca_app = None
    # Fairness Fixer — NEW
    create_fairness_fixer_app = None
    launch_fairness_fixer_app = None
    create_fairness_fixer_en_app = None
    launch_fairness_fixer_en_app = None
    create_fairness_fixer_es_app = None
    launch_fairness_fixer_es_app = None
    create_fairness_fixer_ca_app = None
    launch_fairness_fixer_ca_app = None
    # Justice & Equity Upgrade — NEW
    create_justice_equity_upgrade_app = None
    launch_justice_equity_upgrade_app = None
    create_justice_equity_upgrade_en_app = None
    launch_justice_equity_upgrade_en_app = None
    create_justice_equity_upgrade_es_app = None
    launch_justice_equity_upgrade_es_app = None
    create_justice_equity_upgrade_ca_app = None
    launch_justice_equity_upgrade_ca_app = None

__all__ = [
    "__version__",
    "MoralcompassApiClient",
    "MoralcompassTableMeta",
    "MoralcompassUserStats",
    "ApiClientError",
    "NotFoundError",
    "ServerError",
    "get_api_base_url",
    "get_aws_region",
    "ChallengeManager",
    "JusticeAndEquityChallenge",
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
    # Games
    "create_model_building_game_en_app",
    "launch_model_building_game_en_app",
    "create_model_building_game_ca_app",
    "launch_model_building_game_ca_app",
    "create_model_building_game_es_app",
    "launch_model_building_game_es_app",
    "create_model_building_game_en_final_app",
    "launch_model_building_game_en_final_app",
    "create_model_building_game_es_final_app",
    "launch_model_building_game_es_final_app",
    "create_model_building_game_ca_final_app",
    "launch_model_building_game_ca_final_app",
    # Bias Detective
    "create_bias_detective_part1_app",
    "launch_bias_detective_part1_app",
    "create_bias_detective_part2_app",
    "launch_bias_detective_part2_app",
    "create_bias_detective_en_app",
    "launch_bias_detective_en_app",
    "create_bias_detective_es_app",
    "launch_bias_detective_es_app",
    "create_bias_detective_ca_app",
    "launch_bias_detective_ca_app",
    # Fairness Fixer — NEW
    "create_fairness_fixer_app",
    "launch_fairness_fixer_app",
    "create_fairness_fixer_en_app",
    "launch_fairness_fixer_en_app",
    "create_fairness_fixer_es_app",
    "launch_fairness_fixer_es_app",
    "create_fairness_fixer_ca_app",
    "launch_fairness_fixer_ca_app",
    # Justice & Equity Upgrade — NEW
    "create_justice_equity_upgrade_app",
    "launch_justice_equity_upgrade_app",
    "create_justice_equity_upgrade_en_app",
    "launch_justice_equity_upgrade_en_app",
    "create_justice_equity_upgrade_es_app",
    "launch_justice_equity_upgrade_es_app",
    "create_justice_equity_upgrade_ca_app",
    "launch_justice_equity_upgrade_ca_app",
]
