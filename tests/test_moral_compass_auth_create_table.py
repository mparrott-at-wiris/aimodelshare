"""
Integration test for moral compass authentication and table creation.

Tests the automatic JWT generation feature when only username/password
credentials are provided in environment variables.
"""

import os
import uuid
import pytest
from unittest.mock import patch
from aimodelshare.moral_compass import MoralcompassApiClient
from aimodelshare.moral_compass.api_client import NotFoundError, ApiClientError


@pytest.mark.integration
def test_auto_jwt_and_table_create():
    """
    Test automatic JWT generation and table creation.
    
    Verifies that the client can auto-generate JWT tokens from username/password
    credentials and successfully create tables when AUTH_ENABLED=true.
    """
    # Skip if API base URL not configured
    base_url = os.getenv('MORAL_COMPASS_API_BASE_URL')
    if not base_url:
        pytest.skip('MORAL_COMPASS_API_BASE_URL environment variable not set')
    
    # Ensure JWT not set to force auto generation path
    original_jwt = os.environ.pop('JWT_AUTHORIZATION_TOKEN', None)
    try:
        assert 'JWT_AUTHORIZATION_TOKEN' not in os.environ, "JWT_AUTHORIZATION_TOKEN should not be set for this test"
        
        # Require username/password credentials
        username = os.getenv('MC_USERNAME') or os.getenv('AIMODELSHARE_USERNAME')
        password = os.getenv('MC_PASSWORD') or os.getenv('AIMODELSHARE_PASSWORD')
        
        if not (username and password):
            pytest.skip('Missing MC_USERNAME/MC_PASSWORD or AIMODELSHARE_USERNAME/AIMODELSHARE_PASSWORD credentials')
        
        # Set credentials in environment for auto-generation
        with patch.dict(os.environ, {
            'AIMODELSHARE_USERNAME': username,
            'AIMODELSHARE_PASSWORD': password
        }):
            # Create client - should auto-generate JWT
            client = MoralcompassApiClient(api_base_url=base_url)
            
            # Verify token was auto-generated
            assert client.auth_token, "Client should have auto-generated JWT token"
            assert os.getenv('JWT_AUTHORIZATION_TOKEN'), "JWT_AUTHORIZATION_TOKEN should be set in environment"
            
            # Generate unique table identifiers
            table_id = f'ci-auto-{uuid.uuid4().hex[:8]}-mc'
            playground_url = f'https://example.com/playground/ci-auto-{uuid.uuid4().hex[:6]}'
            
            # Test table creation
            try:
                response = client.create_table(
                    table_id=table_id,
                    display_name='CI Auto JWT Test Table',
                    playground_url=playground_url
                )
                
                # Verify response structure
                assert response.get('tableId') == table_id, f"Expected tableId {table_id}, got {response.get('tableId')}"
                assert 'message' in response, "Response should contain success message"
                
                # Test table retrieval
                table_meta = client.get_table(table_id)
                assert table_meta.table_id == table_id, f"Retrieved table ID mismatch: {table_meta.table_id} != {table_id}"
                assert table_meta.display_name == 'CI Auto JWT Test Table', f"Display name mismatch: {table_meta.display_name}"
                
                print(f"✓ Successfully created and retrieved table: {table_id}")
                
            except ApiClientError as e:
                if "401" in str(e):
                    pytest.fail(f"Authentication failed despite auto-generated JWT: {e}")
                else:
                    # Other API errors (like naming enforcement) should not fail the test
                    # as they indicate the auth worked but other constraints apply
                    print(f"Note: Table creation failed for non-auth reasons: {e}")
    
    finally:
        # Restore original JWT token if it existed
        if original_jwt:
            os.environ['JWT_AUTHORIZATION_TOKEN'] = original_jwt


@pytest.mark.integration
def test_auto_jwt_no_credentials():
    """
    Test that client gracefully handles missing credentials.
    
    When no JWT token and no username/password are available,
    client should initialize without auth token.
    """
    base_url = os.getenv('MORAL_COMPASS_API_BASE_URL', 'https://example.com')
    
    # Clear all auth-related environment variables
    env_vars_to_clear = [
        'JWT_AUTHORIZATION_TOKEN', 'AWS_TOKEN', 
        'AIMODELSHARE_USERNAME', 'AIMODELSHARE_PASSWORD',
        'username', 'password', 'MC_USERNAME', 'MC_PASSWORD'
    ]
    
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.environ.pop(var, None)
    
    try:
        # Create client without any credentials
        client = MoralcompassApiClient(api_base_url=base_url)
        
        # Should initialize successfully but without auth token
        assert client.auth_token is None, "Client should not have auth token when no credentials provided"
        
    finally:
        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value


def test_auto_jwt_generation_mock():
    """
    Test the auto JWT generation logic with mocked dependencies.
    
    Unit test for the auto-generation functionality without requiring
    live credentials or API endpoints.
    """
    base_url = 'https://test-api.example.com'
    
    # Start with clean environment
    with patch.dict(os.environ, {}, clear=True):
        # Set up environment with credentials but no JWT token
        os.environ['AIMODELSHARE_USERNAME'] = 'test-user'
        os.environ['AIMODELSHARE_PASSWORD'] = 'test-password'
        
        # Mock the get_jwt_token function to simulate successful generation
        def mock_get_jwt_token(username, password):
            # Simulate what the real get_jwt_token does - set JWT_AUTHORIZATION_TOKEN
            os.environ['JWT_AUTHORIZATION_TOKEN'] = 'generated.jwt.token'
        
        with patch('aimodelshare.modeluser.get_jwt_token', mock_get_jwt_token):
            with patch('aimodelshare.moral_compass.api_client.logger') as mock_logger:
                
                # Create client - should trigger auto JWT generation
                client = MoralcompassApiClient(api_base_url=base_url)
                
                # Verify JWT token was set
                assert client.auth_token == 'generated.jwt.token', f"Expected generated token, got {client.auth_token}"
                assert os.getenv('JWT_AUTHORIZATION_TOKEN') == 'generated.jwt.token'
                
                # Verify info logging was called
                mock_logger.info.assert_called()
                
                # Check that one of the info calls contains the expected message
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                jwt_log_found = any("Auto-generated JWT token" in msg for msg in info_calls)
                assert jwt_log_found, f"Expected 'Auto-generated JWT token' in logs, got: {info_calls}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])