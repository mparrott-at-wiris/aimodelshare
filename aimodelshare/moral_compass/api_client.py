"""
API client for moral_compass REST API.

Provides a production-ready client with:
- Dataclasses for API responses
- Automatic retries for network and 5xx errors
- Pagination helpers
- Structured exceptions
- Authentication support via JWT tokens
"""

import json
import logging
import time
import os
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
    - Automatic authentication token attachment
    """
    
    def __init__(self, api_base_url: Optional[str] = None, timeout: int = 30, auth_token: Optional[str] = None):
        """
        Initialize the API client.
        
        Args:
            api_base_url: Optional explicit API base URL. If None, will auto-discover.
            timeout: Request timeout in seconds (default: 30)
            auth_token: Optional JWT authentication token. If None, will try to get from environment.
        """
        self.api_base_url = (api_base_url or get_api_base_url()).rstrip("/")
        self.timeout = timeout
        self.auth_token = auth_token or self._get_auth_token_from_env()
        
        # Auto-generate JWT if no token found but credentials available
        if not self.auth_token:
            self._auto_generate_jwt_if_possible()
        
        self.session = self._create_session()
        logger.info(f"MoralcompassApiClient initialized with base URL: {self.api_base_url}")
    
    def _get_auth_token_from_env(self) -> Optional[str]:
        """
        Get authentication token from environment variables.
        
        Tries JWT_AUTHORIZATION_TOKEN first, then falls back to AWS_TOKEN.
        
        Returns:
            Optional[str]: Token or None if not found
        """
        try:
            from ..auth import get_primary_token
            return get_primary_token()
        except ImportError:
            # Fallback to direct environment variable access if auth module not available
            return os.getenv('JWT_AUTHORIZATION_TOKEN') or os.getenv('AWS_TOKEN')
    
    def _auto_generate_jwt_if_possible(self) -> None:
        """
        Attempt to auto-generate a JWT token if credentials are available.
        
        Checks for username/password environment variables and uses them to generate
        a JWT token via aimodelshare.modeluser.get_jwt_token if possible.
        
        Sets self.auth_token and exports JWT_AUTHORIZATION_TOKEN if successful.
        """
        # Check for username/password environment variables
        username = os.getenv('AIMODELSHARE_USERNAME') or os.getenv('username')
        password = os.getenv('AIMODELSHARE_PASSWORD') or os.getenv('password')
        
        if not (username and password):
            logger.debug("Auto JWT generation skipped: No username/password credentials found in environment")
            return
        
        try:
            from aimodelshare.modeluser import get_jwt_token
            
            # Generate JWT token
            logger.debug(f"Attempting to auto-generate JWT token for user: {username[:3]}***")
            get_jwt_token(username, password)
            
            # get_jwt_token sets JWT_AUTHORIZATION_TOKEN in environment, retrieve it
            token = os.getenv('JWT_AUTHORIZATION_TOKEN')
            if token:
                self.auth_token = token
                logger.info(f"Auto-generated JWT token for moral_compass client. Token: {token[:10]}...")
            else:
                logger.debug("JWT token generation completed but JWT_AUTHORIZATION_TOKEN not found in environment")
                
        except Exception as e:
            logger.debug(f"Auto JWT generation failed: {e}")
            # Continue without token - let the actual API calls handle authorization errors
    
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
            allowed_methods=["HEAD", "GET", "PUT", "PATCH", "POST", "DELETE", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with error handling and automatic auth header attachment.
        
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
        
        # Add Authorization header if token is available
        if self.auth_token:
            headers = kwargs.get('headers', {})
            headers['Authorization'] = f'Bearer {self.auth_token}'
            kwargs['headers'] = headers
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=kwargs.pop("timeout", self.timeout),
                **kwargs
            )
            
            # Handle specific error codes
            if response.status_code == 401:
                auth_msg = "Authentication failed (401 Unauthorized)"
                if not self.auth_token:
                    auth_msg += ". No authentication token provided. Set JWT_AUTHORIZATION_TOKEN environment variable or set AIMODELSHARE_USERNAME/AIMODELSHARE_PASSWORD for automatic JWT generation."
                else:
                    auth_msg += f". Token present but invalid or expired. Token: {self.auth_token[:10]}..."
                raise ApiClientError(f"{auth_msg} | URL: {response.url} | Response: {response.text}")
            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path} | body={response.text}")
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
    
    def create_table(self, table_id: str, display_name: Optional[str] = None, 
                     playground_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new table.
        
        Args:
            table_id: Unique identifier for the table
            display_name: Optional display name (defaults to table_id)
            playground_url: Optional playground URL for ownership and naming validation
            
        Returns:
            Dict containing creation response
        """
        payload = {"tableId": table_id}
        if display_name:
            payload["displayName"] = display_name
        if playground_url:
            payload["playgroundUrl"] = playground_url
        
        response = self._request("POST", "/tables", json=payload)
        return response.json()
    
    def create_table_for_playground(self, playground_url: str, suffix: str = '-mc', 
                                     display_name: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Convenience method to create a moral compass table for a playground.
        
        Automatically derives the table ID from the playground URL and suffix.
        Supports region-aware table naming.
        
        Args:
            playground_url: URL of the playground
            suffix: Suffix for the table ID (default: '-mc')
            display_name: Optional display name
            region: Optional AWS region for region-aware naming (e.g., 'us-east-1').
                   If provided, table ID will be <playgroundId>-<region><suffix>
            
        Returns:
            Dict containing creation response
            
        Raises:
            ValueError: If playground ID cannot be extracted from URL
        
        Examples:
            # Non-region-aware
            create_table_for_playground('https://example.com/playground/my-pg')
            # Creates table: my-pg-mc
            
            # Region-aware
            create_table_for_playground('https://example.com/playground/my-pg', region='us-east-1')
            # Creates table: my-pg-us-east-1-mc
        """
        from urllib.parse import urlparse
        
        # Extract playground ID from URL
        parsed = urlparse(playground_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        playground_id = None
        for i, part in enumerate(path_parts):
            if part.lower() in ['playground', 'playgrounds']:
                if i + 1 < len(path_parts):
                    playground_id = path_parts[i + 1]
                    break
        
        if not playground_id and path_parts:
            # Fallback: use last path component
            playground_id = path_parts[-1]
        
        if not playground_id:
            raise ValueError(f"Could not extract playground ID from URL: {playground_url}")
        
        # Build table ID with optional region
        if region:
            table_id = f"{playground_id}-{region}{suffix}"
        else:
            table_id = f"{playground_id}{suffix}"
        
        if not display_name:
            region_suffix = f" ({region})" if region else ""
            display_name = f"Moral Compass - {playground_id}{region_suffix}"
        
        return self.create_table(table_id=table_id, display_name=display_name, 
                                playground_url=playground_url)
    
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
    
    def delete_table(self, table_id: str) -> Dict[str, Any]:
        """
        Delete a table and all associated data.
        
        Requires owner or admin authorization when AUTH_ENABLED=true.
        Only works when ALLOW_TABLE_DELETE=true on server.
        
        Args:
            table_id: The table identifier
            
        Returns:
            Dict containing deletion confirmation
            
        Raises:
            NotFoundError: If table not found
            ApiClientError: If deletion not allowed or authorization fails
        """
        response = self._request("DELETE", f"/tables/{table_id}")
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
    
    def update_moral_compass(self, table_id: str, username: str,
                           metrics: Dict[str, float], 
                           tasks_completed: int = 0,
                           total_tasks: int = 0,
                           questions_correct: int = 0,
                           total_questions: int = 0,
                           primary_metric: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a user's moral compass score with dynamic metrics.
        
        Args:
            table_id: The table identifier
            username: The username
            metrics: Dictionary of metric_name -> numeric_value
            tasks_completed: Number of tasks completed (default: 0)
            total_tasks: Total number of tasks (default: 0)
            questions_correct: Number of questions answered correctly (default: 0)
            total_questions: Total number of questions (default: 0)
            primary_metric: Optional primary metric name (defaults to 'accuracy' or first sorted key)
            
        Returns:
            Dict containing moralCompassScore and other fields
        """
        payload = {
            "metrics": metrics,
            "tasksCompleted": tasks_completed,
            "totalTasks": total_tasks,
            "questionsCorrect": questions_correct,
            "totalQuestions": total_questions
        }
        
        if primary_metric is not None:
            payload["primaryMetric"] = primary_metric
        
        # Try hyphenated path first
        try:
            response = self._request("PUT", f"/tables/{table_id}/users/{username}/moral-compass", json=payload)
            return response.json()
        except NotFoundError as e:
            # If route not found, retry with legacy path (no hyphen)
            if "route not found" in str(e).lower():
                logger.warning(f"Hyphenated path failed with 404, retrying with legacy path: {e}")
                response = self._request("PUT", f"/tables/{table_id}/users/{username}/moralcompass", json=payload)
                return response.json()
            else:
                # Resource-level 404 (e.g., table or user not found), don't retry
                raise
