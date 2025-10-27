"""Production-ready API client for moral_compass (aimodelshare) REST API.

Features:
- Auto-discovery of API base URL
- HTTP retries with exponential backoff
- Typed dataclasses for responses
- Pagination helpers
- Structured error classes
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Iterator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import get_api_base_url


# ============================================================================
# Exception Classes
# ============================================================================

class ApiClientError(Exception):
    """Base exception for API client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[requests.Response] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class NotFoundError(ApiClientError):
    """Raised when a resource is not found (404)."""
    pass


class ServerError(ApiClientError):
    """Raised when server returns 5xx error."""
    pass


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MoralcompassTableMeta:
    """Metadata for a table/playground."""
    table_id: str
    display_name: str
    created_at: str
    is_archived: bool
    user_count: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoralcompassTableMeta':
        """Create instance from API response dictionary."""
        return cls(
            table_id=data['tableId'],
            display_name=data['displayName'],
            created_at=data['createdAt'],
            is_archived=data['isArchived'],
            user_count=data['userCount']
        )


@dataclass
class MoralcompassUserStats:
    """User statistics for a table."""
    username: str
    submission_count: int
    total_count: int
    last_updated: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoralcompassUserStats':
        """Create instance from API response dictionary."""
        return cls(
            username=data['username'],
            submission_count=data['submissionCount'],
            total_count=data['totalCount'],
            last_updated=data['lastUpdated']
        )


# ============================================================================
# API Client
# ============================================================================

class MoralcompassApiClient:
    """
    Production-ready client for moral_compass (aimodelshare) REST API.
    
    Features:
    - Auto-discovery of API base URL if not provided
    - Automatic retries for transient failures
    - Typed dataclasses for responses
    - Pagination helpers
    
    Example:
        >>> client = MoralcompassApiClient()  # Auto-discovers URL
        >>> client.health()
        >>> table = client.create_table("my-table", "My Table")
        >>> for table in client.iter_tables():
        ...     print(table.table_id)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: API base URL. If None, will auto-discover from env/config.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.base_url = (base_url or get_api_base_url()).rstrip('/')
        self.timeout = timeout
        
        # Configure session with retry logic
        self.session = requests.Session()
        
        # Retry configuration: retry on 500, 502, 503, 504 and connection errors
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            backoff_factor=1  # 1s, 2s, 4s delays
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make an HTTP request with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., '/tables')
            json: JSON body for POST/PUT/PATCH
            params: URL query parameters
            
        Returns:
            Response object
            
        Raises:
            NotFoundError: For 404 responses
            ServerError: For 5xx responses
            ApiClientError: For other error responses
        """
        url = f"{self.base_url}{path}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=self.timeout
            )
            
            # Handle error status codes
            if response.status_code == 404:
                raise NotFoundError(
                    f"Resource not found: {path}",
                    status_code=404,
                    response=response
                )
            elif response.status_code >= 500:
                raise ServerError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response=response
                )
            elif not response.ok:
                raise ApiClientError(
                    f"Request failed: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                    response=response
                )
            
            return response
            
        except requests.exceptions.Timeout:
            raise ApiClientError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ApiClientError(f"Connection failed: {str(e)}")
        except (NotFoundError, ServerError, ApiClientError):
            raise
        except Exception as e:
            raise ApiClientError(f"Unexpected error: {str(e)}")
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def health(self) -> Dict[str, Any]:
        """
        Check API health.
        
        Returns:
            Health check response
        """
        response = self._request("GET", "/health")
        return response.json()
    
    # ========================================================================
    # Table Operations
    # ========================================================================
    
    def create_table(self, table_id: str, display_name: str) -> Dict[str, Any]:
        """
        Create a new table.
        
        Args:
            table_id: Unique table identifier
            display_name: Human-readable table name
            
        Returns:
            Creation response with tableId and message
            
        Raises:
            ApiClientError: If table already exists (409) or validation fails
        """
        response = self._request(
            "POST",
            "/tables",
            json={"tableId": table_id, "displayName": display_name}
        )
        return response.json()
    
    def get_table(self, table_id: str) -> MoralcompassTableMeta:
        """
        Get table metadata.
        
        Args:
            table_id: Table identifier
            
        Returns:
            Table metadata
            
        Raises:
            NotFoundError: If table does not exist
        """
        response = self._request("GET", f"/tables/{table_id}")
        return MoralcompassTableMeta.from_dict(response.json())
    
    def patch_table(self, table_id: str, is_archived: bool) -> Dict[str, Any]:
        """
        Update table metadata (currently supports archiving).
        
        Args:
            table_id: Table identifier
            is_archived: Whether to archive the table
            
        Returns:
            Update response
        """
        response = self._request(
            "PATCH",
            f"/tables/{table_id}",
            json={"isArchived": is_archived}
        )
        return response.json()
    
    def list_tables_page(
        self,
        limit: Optional[int] = None,
        last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List tables with pagination.
        
        Args:
            limit: Maximum number of tables to return (default: API default)
            last_key: Pagination token from previous response
            
        Returns:
            Response with 'tables' list and optional 'lastKey' for next page
        """
        params = {}
        if limit is not None:
            params['limit'] = str(limit)
        if last_key is not None:
            params['lastKey'] = str(last_key)
        
        response = self._request("GET", "/tables", params=params)
        return response.json()
    
    def iter_tables(self, limit: Optional[int] = None) -> Iterator[MoralcompassTableMeta]:
        """
        Iterate over all tables, automatically handling pagination.
        
        Args:
            limit: Page size for each request
            
        Yields:
            Table metadata objects
        """
        last_key = None
        
        while True:
            response = self.list_tables_page(limit=limit, last_key=last_key)
            tables = response.get('tables', [])
            
            for table_data in tables:
                yield MoralcompassTableMeta.from_dict(table_data)
            
            # Check if there are more pages
            last_key = response.get('lastKey')
            if not last_key:
                break
    
    # ========================================================================
    # User Operations
    # ========================================================================
    
    def put_user(
        self,
        table_id: str,
        username: str,
        submission_count: int,
        total_count: int
    ) -> Dict[str, Any]:
        """
        Create or update user statistics.
        
        Args:
            table_id: Table identifier
            username: Username
            submission_count: Number of submissions
            total_count: Total count
            
        Returns:
            User data with message
        """
        response = self._request(
            "PUT",
            f"/tables/{table_id}/users/{username}",
            json={
                "submissionCount": submission_count,
                "totalCount": total_count
            }
        )
        return response.json()
    
    def get_user(self, table_id: str, username: str) -> MoralcompassUserStats:
        """
        Get user statistics.
        
        Args:
            table_id: Table identifier
            username: Username
            
        Returns:
            User statistics
            
        Raises:
            NotFoundError: If user does not exist
        """
        response = self._request("GET", f"/tables/{table_id}/users/{username}")
        return MoralcompassUserStats.from_dict(response.json())
    
    def list_users_page(
        self,
        table_id: str,
        limit: Optional[int] = None,
        last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List users in a table with pagination.
        
        Args:
            table_id: Table identifier
            limit: Maximum number of users to return
            last_key: Pagination token from previous response
            
        Returns:
            Response with 'users' list and optional 'lastKey'
        """
        params = {}
        if limit is not None:
            params['limit'] = str(limit)
        if last_key is not None:
            params['lastKey'] = str(last_key)
        
        response = self._request("GET", f"/tables/{table_id}/users", params=params)
        return response.json()
    
    def iter_users(
        self,
        table_id: str,
        limit: Optional[int] = None
    ) -> Iterator[MoralcompassUserStats]:
        """
        Iterate over all users in a table, automatically handling pagination.
        
        Args:
            table_id: Table identifier
            limit: Page size for each request
            
        Yields:
            User statistics objects
        """
        last_key = None
        
        while True:
            response = self.list_users_page(table_id, limit=limit, last_key=last_key)
            users = response.get('users', [])
            
            for user_data in users:
                yield MoralcompassUserStats.from_dict(user_data)
            
            # Check if there are more pages
            last_key = response.get('lastKey')
            if not last_key:
                break
