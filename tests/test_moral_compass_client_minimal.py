#!/usr/bin/env python3
"""
Integration tests for aimodelshare.moral_compass client.

These tests validate the moral_compass API client against a live API instance.
They require the API to be deployed and accessible via MORAL_COMPASS_API_BASE_URL
or AIMODELSHARE_API_BASE_URL environment variable, or via cached terraform outputs.

Run with: pytest -m integration tests/test_moral_compass_client_minimal.py
"""

import pytest
import os
import uuid
from typing import Generator

from unittest.mock import patch

# Import from the new submodule
from aimodelshare.moral_compass import (
    MoralcompassApiClient,
    MoralcompassTableMeta,
    MoralcompassUserStats,
    NotFoundError,
    ApiClientError,
)
from aimodelshare.aws import set_credentials, get_aws_token
from aimodelshare.modeluser import get_jwt_token, create_user_getkeyandpassword

@pytest.fixture(scope="session", autouse=True)
def ensure_jwt_token():
    """
    Ensure JWT_AUTHORIZATION_TOKEN is set before tests run.
    """
    username = os.environ.get('username')
    password = os.environ.get('password')
    if username and password:
        token = get_jwt_token(username, password)
        # get_jwt_token already sets the JWT_AUTHORIZATION_TOKEN env var.
    else:
        raise RuntimeError(
            "You must set 'username' and 'password' environment variables for JWT authentication."
        )


@pytest.fixture(scope="module")
def client() -> MoralcompassApiClient:
    """Create a client instance for testing"""
    return MoralcompassApiClient()


@pytest.fixture
def test_table_id() -> str:
    """Generate a unique test table ID"""
    return f"test-table-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_username() -> str:
    """Generate a unique test username"""
    return f"testuser-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def created_table(client: MoralcompassApiClient, test_table_id: str) -> Generator[str, None, None]:
    """Create a test table and clean it up after the test"""
    # Create table
    client.create_table(test_table_id, f"Test Table {test_table_id}")
    yield test_table_id
    # Cleanup: Archive the table (we don't have delete endpoint)
    try:
        client.patch_table(test_table_id, is_archived=True)
    except Exception:
        pass  # Best effort cleanup


class TestMoralcompassClientIntegration:
    """Integration tests for moral_compass API client"""
    
    @pytest.mark.integration
    def test_health_endpoint(self, client: MoralcompassApiClient):
        """Test that health endpoint is reachable"""
        health = client.health()
        assert isinstance(health, dict)
        assert "timestamp" in health
    
    @pytest.mark.integration
    def test_create_table(self, client: MoralcompassApiClient, test_table_id: str):
        """Test creating a new table"""
        response = client.create_table(test_table_id, "Test Display Name")
        assert response["tableId"] == test_table_id
        assert response["displayName"] == "Test Display Name"
        
        # Cleanup
        client.patch_table(test_table_id, is_archived=True)
    
    @pytest.mark.integration
    def test_get_table(self, client: MoralcompassApiClient, created_table: str):
        """Test getting a specific table"""
        table = client.get_table(created_table)
        
        assert isinstance(table, MoralcompassTableMeta)
        assert table.table_id == created_table
        assert table.display_name is not None
        assert isinstance(table.user_count, int)
    
    @pytest.mark.integration
    def test_get_nonexistent_table(self, client: MoralcompassApiClient):
        """Test that getting a non-existent table raises NotFoundError"""
        with pytest.raises(NotFoundError):
            client.get_table("nonexistent-table-12345")
    
    @pytest.mark.integration
    def test_list_tables(self, client: MoralcompassApiClient, created_table: str):
        """Test listing tables with pagination"""
        response = client.list_tables(limit=10)
        
        assert "tables" in response
        assert isinstance(response["tables"], list)
        
        # Verify our created table is in the list
        table_ids = [t["tableId"] for t in response["tables"]]
        assert created_table in table_ids
    
    @pytest.mark.integration
    def test_iter_tables(self, client: MoralcompassApiClient, created_table: str):
        """Test iterating over all tables with automatic pagination"""
        tables = list(client.iter_tables(limit=5))
        
        assert len(tables) > 0
        assert all(isinstance(t, MoralcompassTableMeta) for t in tables)
        
        # Verify our created table is in the iteration
        table_ids = [t.table_id for t in tables]
        assert created_table in table_ids
    
    @pytest.mark.integration
    def test_patch_table(self, client: MoralcompassApiClient, created_table: str):
        """Test updating table metadata"""
        response = client.patch_table(created_table, display_name="Updated Name")
        assert "message" in response
        
        # Verify update
        table = client.get_table(created_table)
        assert table.display_name == "Updated Name"
    
    @pytest.mark.integration
    def test_put_user(self, client: MoralcompassApiClient, created_table: str, test_username: str):
        """Test creating/updating a user"""
        response = client.put_user(
            created_table,
            test_username,
            submission_count=5,
            total_count=10
        )
        
        assert response["username"] == test_username
        assert response["submissionCount"] == 5
        assert response["totalCount"] == 10
    
    @pytest.mark.integration
    def test_get_user(self, client: MoralcompassApiClient, created_table: str, test_username: str):
        """Test getting a specific user"""
        # First create the user
        client.put_user(created_table, test_username, submission_count=3, total_count=15)
        
        # Then get it
        user = client.get_user(created_table, test_username)
        
        assert isinstance(user, MoralcompassUserStats)
        assert user.username == test_username
        assert user.submission_count == 3
        assert user.total_count == 15
    
    @pytest.mark.integration
    def test_get_nonexistent_user(self, client: MoralcompassApiClient, created_table: str):
        """Test that getting a non-existent user raises NotFoundError"""
        with pytest.raises(NotFoundError):
            client.get_user(created_table, "nonexistent-user-12345")
    
    @pytest.mark.integration
    def test_list_users(self, client: MoralcompassApiClient, created_table: str, test_username: str):
        """Test listing users with pagination"""
        # Create a user first
        client.put_user(created_table, test_username, submission_count=7, total_count=20)
        
        # List users
        response = client.list_users(created_table, limit=10)
        
        assert "users" in response
        assert isinstance(response["users"], list)
        
        # Verify our user is in the list
        usernames = [u["username"] for u in response["users"]]
        assert test_username in usernames
    
    @pytest.mark.integration
    def test_iter_users(self, client: MoralcompassApiClient, created_table: str, test_username: str):
        """Test iterating over all users with automatic pagination"""
        # Create a user first
        client.put_user(created_table, test_username, submission_count=8, total_count=25)
        
        # Iterate users
        users = list(client.iter_users(created_table, limit=5))
        
        assert len(users) > 0
        assert all(isinstance(u, MoralcompassUserStats) for u in users)
        
        # Verify our user is in the iteration
        usernames = [u.username for u in users]
        assert test_username in usernames
    
    @pytest.mark.integration
    def test_pagination_with_last_key(self, client: MoralcompassApiClient, created_table: str):
        """Test that pagination with lastKey works correctly"""
        # Create multiple users
        for i in range(5):
            client.put_user(created_table, f"user-{i}", submission_count=i, total_count=i*2)
        
        # Get first page
        page1 = client.list_users(created_table, limit=2)
        assert len(page1["users"]) <= 2
        
        # If there's a lastKey, get next page
        if "lastKey" in page1:
            page2 = client.list_users(created_table, limit=2, last_key=page1["lastKey"])
            assert "users" in page2
            # Ensure pages don't overlap
            page1_usernames = {u["username"] for u in page1["users"]}
            page2_usernames = {u["username"] for u in page2["users"]}
            assert page1_usernames.isdisjoint(page2_usernames)




if __name__ == "__main__":
    # Allow running directly for quick testing
    import sys
    
    print("Running integration tests for moral_compass client...")
    print("Note: This requires a deployed API instance.")
    print("")
    
    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "-m", "integration"])
    sys.exit(exit_code)
