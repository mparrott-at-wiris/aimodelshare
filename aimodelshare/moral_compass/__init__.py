"""
aimodelshare.moral_compass - Production-ready client for moral_compass REST API

This submodule provides a client for interacting with the moral_compass API
with support for pagination, retries, and structured exceptions.

Example usage:
    from aimodelshare.moral_compass import MoralcompassApiClient
    
    client = MoralcompassApiClient()
    
    # Create a table
    client.create_table("my-table", "My Display Name")
    
    # List tables with pagination
    for table in client.iter_tables():
        print(f"Table: {table.table_id} - {table.display_name}")
    
    # Get specific table
    table = client.get_table("my-table")
    
    # Manage users
    client.put_user("my-table", "user1", submission_count=10, total_count=100)
    user = client.get_user("my-table", "user1")
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
from .config import get_api_base_url

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
