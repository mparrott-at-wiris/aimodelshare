"""
API client for moral_compass REST API.

Provides a production-ready client with:
- Dataclasses for API responses
- Automatic retries for network and 5xx errors
- Pagination helpers
- Structured exceptions
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Iterator, List
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import get_api_base_url

logger = logging.getLogger("aimodelshare.moral_compass")


# ============================================================================
# Exceptions
# ============================================================================

class ApiClientError(Exception):
    """Base exception for API client errors"""
    pass


class NotFoundError(ApiClientError):
    """Raised when a resource is not found (404)"""
    pass


class ServerError(ApiClientError):
    """Raised when server returns 5xx error"""
    pass


# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class MoralcompassTableMeta:
    """Metadata for a moral compass table"""
    table_id: str
    display_name: str
    created_at: Optional[str] = None
    is_archived: bool = False
    user_count: int = 0


@dataclass
class MoralcompassUserStats:
    """Statistics for a user in a table"""
    username: str
    submission_count: int = 0
    total_count: int = 0
    last_updated: Optional[str] = None


# ============================================================================
# API Client
# ============================================================================

class MoralcompassApiClient:
    """
    Production-ready client for moral_compass REST API.
    
    Features:
    - Automatic API base URL discovery
    - Network retries with exponential backoff
    - Pagination helpers
    - Structured exceptions
    """
    
    def __init__(self, api_base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the API client.
        
        Args:
            api_base_url: Optional explicit API base URL. If None, will auto-discover.
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_base_url = (api_base_url or get_api_base_url()).rstrip("/")
        self.timeout = timeout
        self.session = self._create_session()
        logger.info(f"MoralcompassApiClient initialized with base URL: {self.api_base_url}")
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.
        
        Returns:
            Configured requests.Session with retry adapter
        """
        session = requests.Session()
        
        # Configure retries for network errors and 5xx server errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "PATCH", "POST", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with error handling.
        
        Args:
            method: HTTP method
            path: API path (without base URL)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            requests.Response object
            
        Raises:
            NotFoundError: If resource not found (404)
            ServerError: If server error (5xx)
            ApiClientError: For other errors
        """
        url = f"{self.api_base_url}/{path.lstrip('/')}"
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=kwargs.pop("timeout", self.timeout),
                **kwargs
            )
            
            # Handle specific error codes
            if response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}")
            elif 500 <= response.status_code < 600:
                raise ServerError(f"Server error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout as e:
            raise ApiClientError(f"Request timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            raise ApiClientError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            if not isinstance(e, (NotFoundError, ServerError)):
                raise ApiClientError(f"Request failed: {e}")
            raise
    
    # ========================================================================
    # Health endpoint
    # ========================================================================
    
    def health(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Dict containing health status information
        """
        response = self._request("GET", "/health")
        return response.json()
    
    # ========================================================================
    # Table endpoints
    # ========================================================================
    
    def create_table(self, table_id: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new table.
        
        Args:
            table_id: Unique identifier for the table
            display_name: Optional display name (defaults to table_id)
            
        Returns:
            Dict containing creation response
        """
        payload = {"tableId": table_id}
        if display_name:
            payload["displayName"] = display_name
        
        response = self._request("POST", "/tables", json=payload)
        return response.json()
    
    def list_tables(self, limit: int = 50, last_key: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List tables with pagination.
        
        Args:
            limit: Maximum number of tables to return (default: 50)
            last_key: Pagination key from previous response
            
        Returns:
            Dict containing 'tables' list and optional 'lastKey' for pagination
        """
        params = {"limit": limit}
        if last_key:
            params["lastKey"] = json.dumps(last_key)
        
        response = self._request("GET", f"/tables?{urlencode(params)}")
        return response.json()
    
    def iter_tables(self, limit: int = 50) -> Iterator[MoralcompassTableMeta]:
        """
        Iterate over all tables with automatic pagination.
        
        Args:
            limit: Page size (default: 50)
            
        Yields:
            MoralcompassTableMeta objects
        """
        last_key = None
        
        while True:
            response = self.list_tables(limit=limit, last_key=last_key)
            tables = response.get("tables", [])
            
            for table_data in tables:
                yield MoralcompassTableMeta(
                    table_id=table_data["tableId"],
                    display_name=table_data.get("displayName", table_data["tableId"]),
                    created_at=table_data.get("createdAt"),
                    is_archived=table_data.get("isArchived", False),
                    user_count=table_data.get("userCount", 0)
                )
            
            last_key = response.get("lastKey")
            if not last_key:
                break
    
    def get_table(self, table_id: str) -> MoralcompassTableMeta:
        """
        Get a specific table by ID.
        
        Args:
            table_id: The table identifier
            
        Returns:
            MoralcompassTableMeta object
            
        Raises:
            NotFoundError: If table not found
        """
        response = self._request("GET", f"/tables/{table_id}")
        data = response.json()
        
        return MoralcompassTableMeta(
            table_id=data["tableId"],
            display_name=data.get("displayName", data["tableId"]),
            created_at=data.get("createdAt"),
            is_archived=data.get("isArchived", False),
            user_count=data.get("userCount", 0)
        )
    
    def patch_table(self, table_id: str, display_name: Optional[str] = None, 
                    is_archived: Optional[bool] = None) -> Dict[str, Any]:
        """
        Update table metadata.
        
        Args:
            table_id: The table identifier
            display_name: Optional new display name
            is_archived: Optional archive status
            
        Returns:
            Dict containing update response
        """
        payload = {}
        if display_name is not None:
            payload["displayName"] = display_name
        if is_archived is not None:
            payload["isArchived"] = is_archived
        
        response = self._request("PATCH", f"/tables/{table_id}", json=payload)
        return response.json()
    
    # ========================================================================
    # User endpoints
    # ========================================================================
    
    def list_users(self, table_id: str, limit: int = 50, 
                   last_key: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        List users in a table with pagination.
        
        Args:
            table_id: The table identifier
            limit: Maximum number of users to return (default: 50)
            last_key: Pagination key from previous response
            
        Returns:
            Dict containing 'users' list and optional 'lastKey' for pagination
        """
        params = {"limit": limit}
        if last_key:
            params["lastKey"] = json.dumps(last_key)
        
        response = self._request("GET", f"/tables/{table_id}/users?{urlencode(params)}")
        return response.json()
    
    def iter_users(self, table_id: str, limit: int = 50) -> Iterator[MoralcompassUserStats]:
        """
        Iterate over all users in a table with automatic pagination.
        
        Args:
            table_id: The table identifier
            limit: Page size (default: 50)
            
        Yields:
            MoralcompassUserStats objects
        """
        last_key = None
        
        while True:
            response = self.list_users(table_id, limit=limit, last_key=last_key)
            users = response.get("users", [])
            
            for user_data in users:
                yield MoralcompassUserStats(
                    username=user_data["username"],
                    submission_count=user_data.get("submissionCount", 0),
                    total_count=user_data.get("totalCount", 0),
                    last_updated=user_data.get("lastUpdated")
                )
            
            last_key = response.get("lastKey")
            if not last_key:
                break
    
    def get_user(self, table_id: str, username: str) -> MoralcompassUserStats:
        """
        Get a specific user's stats in a table.
        
        Args:
            table_id: The table identifier
            username: The username
            
        Returns:
            MoralcompassUserStats object
            
        Raises:
            NotFoundError: If user or table not found
        """
        response = self._request("GET", f"/tables/{table_id}/users/{username}")
        data = response.json()
        
        return MoralcompassUserStats(
            username=data["username"],
            submission_count=data.get("submissionCount", 0),
            total_count=data.get("totalCount", 0),
            last_updated=data.get("lastUpdated")
        )
    
    def put_user(self, table_id: str, username: str, 
                 submission_count: int, total_count: int) -> Dict[str, Any]:
        """
        Create or update a user's stats in a table.
        
        Args:
            table_id: The table identifier
            username: The username
            submission_count: Number of submissions
            total_count: Total count
            
        Returns:
            Dict containing update response
        """
        payload = {
            "submissionCount": submission_count,
            "totalCount": total_count
        }
        
        response = self._request("PUT", f"/tables/{table_id}/users/{username}", json=payload)
        return response.json()
