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
        create_tutorial_app, launch_tutorial_app
    )
except Exception:  # noqa: BLE001
    create_tutorial_app = None
    launch_tutorial_app = None

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
    "launch_tutorial_app"
]
