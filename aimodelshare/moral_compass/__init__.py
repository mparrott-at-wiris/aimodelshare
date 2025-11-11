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
        create_model_building_game_beginner_app, launch_model_building_game_beginner_app
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
    "launch_model_building_game_beginner_app"
]
