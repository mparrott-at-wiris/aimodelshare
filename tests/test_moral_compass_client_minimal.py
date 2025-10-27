#!/usr/bin/env python3
"""
Integration tests for moral_compass client library.

These tests validate the production-ready client against the live API:
- Auto-discovery of API base URL
- Health check endpoint
- Table lifecycle (create, get, patch, list, iterate)
- User upsert and retrieval
- Pagination iterators
- Error handling (NotFoundError)

Tests are marked with @pytest.mark.integration and should be run after
infrastructure deployment.

Usage:
    pytest -m integration tests/test_moral_compass_client_minimal.py
"""

import uuid
import pytest
from moral_compass import (
    MoralcompassApiClient,
    MoralcompassTableMeta,
    MoralcompassUserStats,
    NotFoundError,
    get_api_base_url,
)


@pytest.fixture(scope="module")
def api_client():
    """Create API client using auto-discovery."""
    # This will use environment variables or cached Terraform outputs
    client = MoralcompassApiClient()
    return client


@pytest.fixture(scope="module")
def test_table_id():
    """Generate unique test table ID."""
    return f"moral-compass-test-{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
def test_api_base_url_discovery():
    """Test that API base URL can be discovered."""
    url = get_api_base_url()
    assert url is not None
    assert url.startswith("http")
    print(f"✅ API Base URL discovered: {url}")


@pytest.mark.integration
def test_health_check(api_client):
    """Test API health endpoint."""
    response = api_client.health()
    assert response is not None
    print(f"✅ Health check response: {response}")


@pytest.mark.integration
def test_create_table(api_client, test_table_id):
    """Test creating a new table."""
    response = api_client.create_table(
        table_id=test_table_id,
        display_name=f"Moral Compass Test Table {test_table_id}"
    )
    assert response is not None
    assert response.get("tableId") == test_table_id
    assert "message" in response
    print(f"✅ Created table: {test_table_id}")


@pytest.mark.integration
def test_get_table(api_client, test_table_id):
    """Test retrieving table metadata."""
    table = api_client.get_table(test_table_id)
    assert isinstance(table, MoralcompassTableMeta)
    assert table.table_id == test_table_id
    assert table.display_name is not None
    assert table.created_at is not None
    assert isinstance(table.is_archived, bool)
    assert isinstance(table.user_count, int)
    print(f"✅ Retrieved table: {table.table_id}, users: {table.user_count}")


@pytest.mark.integration
def test_get_nonexistent_table(api_client):
    """Test that getting a non-existent table raises NotFoundError."""
    nonexistent_id = f"nonexistent-{uuid.uuid4().hex[:8]}"
    with pytest.raises(NotFoundError):
        api_client.get_table(nonexistent_id)
    print(f"✅ NotFoundError correctly raised for non-existent table")


@pytest.mark.integration
def test_patch_table(api_client, test_table_id):
    """Test updating table metadata."""
    # Archive the table
    response = api_client.patch_table(test_table_id, is_archived=True)
    assert "message" in response
    
    # Verify it's archived
    table = api_client.get_table(test_table_id)
    assert table.is_archived is True
    
    # Unarchive it
    response = api_client.patch_table(test_table_id, is_archived=False)
    assert "message" in response
    
    # Verify it's unarchived
    table = api_client.get_table(test_table_id)
    assert table.is_archived is False
    
    print(f"✅ Successfully patched table archive status")


@pytest.mark.integration
def test_list_tables(api_client, test_table_id):
    """Test listing tables with pagination."""
    response = api_client.list_tables_page(limit=10)
    assert "tables" in response
    assert isinstance(response["tables"], list)
    
    # Our test table should be in the list (eventually)
    # Note: May need to retry due to eventual consistency
    found = any(t.get("tableId") == test_table_id for t in response["tables"])
    if not found:
        # Try fetching all pages
        all_tables = list(api_client.iter_tables())
        found = any(t.table_id == test_table_id for t in all_tables)
    
    assert found, f"Test table {test_table_id} not found in tables list"
    print(f"✅ Test table found in tables list")


@pytest.mark.integration
def test_iter_tables(api_client):
    """Test iterating over all tables."""
    tables = list(api_client.iter_tables(limit=10))
    assert len(tables) > 0
    assert all(isinstance(t, MoralcompassTableMeta) for t in tables)
    print(f"✅ Iterated over {len(tables)} tables")


@pytest.mark.integration
def test_put_user(api_client, test_table_id):
    """Test creating/updating a user."""
    username = f"testuser-{uuid.uuid4().hex[:6]}"
    response = api_client.put_user(
        table_id=test_table_id,
        username=username,
        submission_count=5,
        total_count=10
    )
    assert response is not None
    assert response.get("username") == username
    assert response.get("submissionCount") == 5
    assert response.get("totalCount") == 10
    print(f"✅ Created/updated user: {username}")


@pytest.mark.integration
def test_get_user(api_client, test_table_id):
    """Test retrieving user statistics."""
    username = f"getuser-{uuid.uuid4().hex[:6]}"
    
    # First create the user
    api_client.put_user(
        table_id=test_table_id,
        username=username,
        submission_count=3,
        total_count=7
    )
    
    # Now retrieve it
    user = api_client.get_user(test_table_id, username)
    assert isinstance(user, MoralcompassUserStats)
    assert user.username == username
    assert user.submission_count == 3
    assert user.total_count == 7
    assert user.last_updated is not None
    print(f"✅ Retrieved user: {user.username}, submissions: {user.submission_count}")


@pytest.mark.integration
def test_get_nonexistent_user(api_client, test_table_id):
    """Test that getting a non-existent user raises NotFoundError."""
    nonexistent_username = f"nonexistent-{uuid.uuid4().hex[:8]}"
    with pytest.raises(NotFoundError):
        api_client.get_user(test_table_id, nonexistent_username)
    print(f"✅ NotFoundError correctly raised for non-existent user")


@pytest.mark.integration
def test_list_users(api_client, test_table_id):
    """Test listing users with pagination."""
    # Create a few users
    for i in range(3):
        username = f"listuser-{i:02d}-{uuid.uuid4().hex[:4]}"
        api_client.put_user(
            table_id=test_table_id,
            username=username,
            submission_count=i + 1,
            total_count=(i + 1) * 2
        )
    
    # List users
    response = api_client.list_users_page(test_table_id, limit=10)
    assert "users" in response
    assert isinstance(response["users"], list)
    assert len(response["users"]) >= 3
    print(f"✅ Listed {len(response['users'])} users")


@pytest.mark.integration
def test_iter_users(api_client, test_table_id):
    """Test iterating over all users in a table."""
    # Create a few more users to ensure we have data
    for i in range(5):
        username = f"iteruser-{i:02d}-{uuid.uuid4().hex[:4]}"
        api_client.put_user(
            table_id=test_table_id,
            username=username,
            submission_count=i + 1,
            total_count=(i + 1) * 2
        )
    
    # Iterate over all users
    users = list(api_client.iter_users(test_table_id, limit=10))
    assert len(users) >= 5
    assert all(isinstance(u, MoralcompassUserStats) for u in users)
    print(f"✅ Iterated over {len(users)} users")


@pytest.mark.integration
def test_pagination_with_small_limit(api_client, test_table_id):
    """Test that pagination works correctly with a small limit."""
    # Create multiple users to test pagination
    num_users = 15
    usernames = []
    for i in range(num_users):
        username = f"pageuser-{i:03d}-{uuid.uuid4().hex[:4]}"
        usernames.append(username)
        api_client.put_user(
            table_id=test_table_id,
            username=username,
            submission_count=i + 1,
            total_count=(i + 1) * 2
        )
    
    # Fetch with small page size to force pagination
    all_users = list(api_client.iter_users(test_table_id, limit=5))
    
    # Should get all users we created (and possibly others from previous tests)
    assert len(all_users) >= num_users
    print(f"✅ Pagination worked correctly, retrieved {len(all_users)} users with limit=5")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-m", "integration"])
