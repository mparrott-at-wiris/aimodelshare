"""
aimodelshare.moral_compass - Production-ready client for moral_compass REST API

Key change (Nov 2025):
- Removed eager importing of Gradio app factories to prevent accidental side-effect
  launches (e.g., tutorial app starting during container boot).
- Added lazy attribute resolution for create_* and launch_* symbols that proxies to
  aimodelshare.moral_compass.apps without importing all app modules up front.
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

# NOTE:
# We deliberately do NOT import the Gradio app factory functions here.
# Importing them previously caused each app module to load; because tutorial.py
# launched its app at import time, every Cloud Run service showed the tutorial.
#
# Access patterns now:
#   from aimodelshare.moral_compass import apps
#   factory = apps.create_judge_app()
# OR (still supported via __getattr__):
#   from aimodelshare.moral_compass import create_judge_app
#
# The __getattr__ below defers to the lazy loader in apps.__getattr__.

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
    # App factories intentionally excluded from static __all__ to avoid eager import.
]


def __getattr__(name: str):
    """
    Lazily expose app factory / launcher functions without triggering eager imports.

    This delegates resolution for names beginning with 'create_' or 'launch_' to the
    aimodelshare.moral_compass.apps lazy export layer.

    Raises:
        AttributeError if the symbol is not recognized.
    """
    if name.startswith(("create_", "launch_")):
        try:
            from . import apps  # Local import to avoid loading all apps prematurely
            return getattr(apps, name)
        except AttributeError as e:
            raise AttributeError(
                f"'{name}' not found in moral_compass.apps lazy export map."
            ) from e
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
