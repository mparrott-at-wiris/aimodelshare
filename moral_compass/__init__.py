"""
Backward compatibility shim for moral_compass package.

This package re-exports all functionality from aimodelshare.moral_compass
to maintain backward compatibility with code that imports from the top-level
moral_compass package.

Usage:
    # Both import paths work identically:
    from moral_compass import MoralcompassApiClient
    from aimodelshare.moral_compass import MoralcompassApiClient
"""

# Re-export everything from aimodelshare.moral_compass
from aimodelshare.moral_compass import (
    __version__,
    MoralcompassApiClient,
    MoralcompassTableMeta,
    MoralcompassUserStats,
    ApiClientError,
    NotFoundError,
    ServerError,
    get_api_base_url,
)

__all__ = [
    "__version__",
    "MoralcompassApiClient",
    "MoralcompassTableMeta",
    "MoralcompassUserStats",
    "ApiClientError",
    "NotFoundError",
    "ServerError",
    "get_api_base_url",
]
