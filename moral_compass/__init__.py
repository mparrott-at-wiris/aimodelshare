"""
moral_compass - Production-ready Python client for aimodelshare REST API.

This package provides a typed, reliable client for interacting with the
aimodelshare Lambda API, with features including:
- Auto-discovery of API base URL
- HTTP retries with exponential backoff
- Typed dataclasses for responses
- Pagination helpers
- Structured error handling

Example:
    >>> from moral_compass import MoralcompassApiClient
    >>> client = MoralcompassApiClient()  # Auto-discovers API URL
    >>> client.health()
    >>> table = client.create_table("my-table", "My Table")
    >>> for user in client.iter_users("my-table"):
    ...     print(user.username, user.submission_count)
"""

from ._version import __version__
from .config import get_api_base_url, ApiBaseUrlNotFound
from .api_client import (
    MoralcompassApiClient,
    MoralcompassTableMeta,
    MoralcompassUserStats,
    ApiClientError,
    NotFoundError,
    ServerError,
)

__all__ = [
    '__version__',
    'get_api_base_url',
    'ApiBaseUrlNotFound',
    'MoralcompassApiClient',
    'MoralcompassTableMeta',
    'MoralcompassUserStats',
    'ApiClientError',
    'NotFoundError',
    'ServerError',
]
