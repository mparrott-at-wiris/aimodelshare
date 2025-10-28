"""
Tests for moral compass authentication and authorization.

Tests ownership enforcement, naming conventions, and access control.
These tests require AUTH_ENABLED=true and MC_ENFORCE_NAMING=true on the server.
"""

import os
import time
import pytest
import json
from unittest.mock import patch, Mock
from aimodelshare.moral_compass import MoralcompassApiClient
from aimodelshare.moral_compass.api_client import NotFoundError, ApiClientError


# Test configuration
PLAYGROUND_ID = 'test_auth_playground'
TABLE_ID_VALID = f'{PLAYGROUND_ID}-mc'
TABLE_ID_INVALID = 'invalid_table_name'
PLAYGROUND_URL = f'https://example.com/playground/{PLAYGROUND_ID}'
USERNAME_OWNER = 'owner_user'
USERNAME_OTHER = 'other_user'


def create_mock_jwt_token(sub='user123', email='user@example.com', username=None):
    """
    Create a mock JWT token payload.
    
    Note: This is for testing the unverified decode path.
    Real JWT tokens should be properly signed and verified.
    """
    import jwt
    
    payload = {
        'sub': sub,
        'email': email,
        'iss': 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test'
    }
    
    if username:
        payload['cognito:username'] = username
    
    # Create unverified token (no signature verification needed for mock)
    token = jwt.encode(payload, 'secret', algorithm='HS256')
    return token


class TestAuthTokenHandling:
    """Test authentication token retrieval and usage"""
    
    def test_get_primary_token_jwt_preferred(self):
        """JWT_AUTHORIZATION_TOKEN should be preferred over AWS_TOKEN"""
        from aimodelshare.auth import get_primary_token
        
        with patch.dict(os.environ, {
            'JWT_AUTHORIZATION_TOKEN': 'jwt_token_value',
            'AWS_TOKEN': 'aws_token_value'
        }):
            token = get_primary_token()
            assert token == 'jwt_token_value'
    
    def test_get_primary_token_aws_fallback(self):
        """Should fall back to AWS_TOKEN with deprecation warning"""
        from aimodelshare.auth import get_primary_token
        
        with patch.dict(os.environ, {'AWS_TOKEN': 'aws_token_value'}, clear=True):
            with pytest.warns(DeprecationWarning, match='AWS_TOKEN'):
                token = get_primary_token()
                assert token == 'aws_token_value'
    
    def test_get_primary_token_none(self):
        """Should return None when no token is available"""
        from aimodelshare.auth import get_primary_token
        
        with patch.dict(os.environ, {}, clear=True):
            token = get_primary_token()
            assert token is None
    
    def test_api_client_auto_attaches_token(self):
        """API client should auto-attach auth token from environment"""
        mock_token = 'test_jwt_token'
        
        with patch.dict(os.environ, {'JWT_AUTHORIZATION_TOKEN': mock_token}):
            # Create client without explicit token - should get from env
            client = MoralcompassApiClient(api_base_url='https://api.example.com')
            assert client.auth_token == mock_token
    
    def test_api_client_explicit_token(self):
        """API client should use explicitly provided token"""
        explicit_token = 'explicit_jwt_token'
        env_token = 'env_jwt_token'
        
        with patch.dict(os.environ, {'JWT_AUTHORIZATION_TOKEN': env_token}):
            # Explicit token should override environment
            client = MoralcompassApiClient(
                api_base_url='https://api.example.com',
                auth_token=explicit_token
            )
            assert client.auth_token == explicit_token


class TestIdentityClaims:
    """Test JWT identity claim extraction"""
    
    def test_get_identity_claims_success(self):
        """Should successfully decode JWT and extract claims"""
        from aimodelshare.auth import get_identity_claims
        
        token = create_mock_jwt_token(
            sub='user123',
            email='test@example.com',
            username='testuser'
        )
        
        claims = get_identity_claims(token, verify=False)
        
        assert claims['sub'] == 'user123'
        assert claims['email'] == 'test@example.com'
        assert claims['cognito:username'] == 'testuser'
        assert claims['principal'] == 'testuser'  # Derived
    
    def test_get_identity_claims_no_token(self):
        """Should raise ValueError when no token provided"""
        from aimodelshare.auth import get_identity_claims
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match='No authentication token'):
                get_identity_claims()
    
    def test_derive_principal_priority(self):
        """Principal should be derived with correct priority"""
        from aimodelshare.auth import derive_principal
        
        # Test priority: cognito:username > email > sub
        claims = {
            'cognito:username': 'username_value',
            'email': 'email_value',
            'sub': 'sub_value'
        }
        assert derive_principal(claims) == 'username_value'
        
        claims = {
            'email': 'email_value',
            'sub': 'sub_value'
        }
        assert derive_principal(claims) == 'email_value'
        
        claims = {
            'sub': 'sub_value'
        }
        assert derive_principal(claims) == 'sub_value'
    
    def test_is_admin_with_groups(self):
        """Should correctly identify admin users"""
        from aimodelshare.auth import is_admin
        
        claims_admin = {'cognito:groups': ['admin', 'users']}
        assert is_admin(claims_admin) is True
        
        claims_user = {'cognito:groups': ['users']}
        assert is_admin(claims_user) is False
        
        claims_no_groups = {}
        assert is_admin(claims_no_groups) is False


class TestTableOwnership:
    """Test table ownership and naming enforcement"""
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_create_table_with_valid_naming(self):
        """Creating table with correct naming convention should succeed"""
        # This would require a live server with AUTH_ENABLED=true
        # Skipped by default, can be enabled for integration testing
        pass
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_create_table_with_invalid_naming(self):
        """Creating table with wrong naming convention should fail"""
        # This would require a live server with MC_ENFORCE_NAMING=true
        # Skipped by default, can be enabled for integration testing
        pass
    
    def test_create_table_for_playground_helper(self):
        """Helper method should correctly derive table ID from playground URL"""
        with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient._request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                'tableId': TABLE_ID_VALID,
                'displayName': f'Moral Compass - {PLAYGROUND_ID}',
                'message': 'Table created successfully'
            }
            mock_request.return_value = mock_response
            
            client = MoralcompassApiClient(api_base_url='https://api.example.com')
            result = client.create_table_for_playground(PLAYGROUND_URL)
            
            # Verify the request was made with correct parameters
            assert mock_request.called
            call_args = mock_request.call_args
            assert call_args[0][0] == 'POST'
            assert call_args[0][1] == '/tables'
            
            payload = call_args[1]['json']
            assert payload['tableId'] == TABLE_ID_VALID
            assert payload['playgroundUrl'] == PLAYGROUND_URL
            assert 'displayName' in payload
    
    def test_create_table_for_playground_invalid_url(self):
        """Helper should raise ValueError for invalid URL"""
        client = MoralcompassApiClient(api_base_url='https://api.example.com')
        
        with pytest.raises(ValueError, match='Could not extract playground ID'):
            client.create_table_for_playground('https://example.com')


class TestAuthorizationChecks:
    """Test authorization enforcement on mutating operations"""
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_owner_can_update_progress(self):
        """Table owner should be able to update user progress"""
        # Requires live server with auth
        pass
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_non_owner_cannot_update_other_user_progress(self):
        """Non-owner should not be able to update another user's progress"""
        # Requires live server with auth
        pass
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_user_can_update_own_progress(self):
        """User should be able to update their own progress"""
        # Requires live server with auth
        pass
    
    @pytest.mark.skipif(
        os.getenv('SKIP_AUTH_TESTS', 'true').lower() == 'true',
        reason="Auth tests require AUTH_ENABLED=true server"
    )
    def test_delete_table_owner_only(self):
        """Only owner or admin should be able to delete table"""
        # Requires live server with auth and ALLOW_TABLE_DELETE=true
        pass


class TestBackwardCompatibility:
    """Test backward compatibility with existing tables"""
    
    def test_create_table_without_playground_url(self):
        """Should still support creating tables without playgroundUrl"""
        with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient._request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                'tableId': 'legacy_table',
                'displayName': 'Legacy Table',
                'message': 'Table created successfully'
            }
            mock_request.return_value = mock_response
            
            client = MoralcompassApiClient(api_base_url='https://api.example.com')
            result = client.create_table('legacy_table', display_name='Legacy Table')
            
            # Verify playgroundUrl not required
            call_args = mock_request.call_args
            payload = call_args[1]['json']
            assert 'playgroundUrl' not in payload or payload['playgroundUrl'] is None


class TestDeleteEndpoint:
    """Test DELETE table endpoint"""
    
    def test_delete_table_method_exists(self):
        """API client should have delete_table method"""
        client = MoralcompassApiClient(api_base_url='https://api.example.com')
        assert hasattr(client, 'delete_table')
        assert callable(client.delete_table)
    
    def test_delete_table_sends_delete_request(self):
        """delete_table should send DELETE request to correct endpoint"""
        with patch('aimodelshare.moral_compass.api_client.MoralcompassApiClient._request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                'message': 'Table deleted successfully',
                'deletedItems': 5
            }
            mock_request.return_value = mock_response
            
            client = MoralcompassApiClient(api_base_url='https://api.example.com')
            result = client.delete_table('test_table')
            
            # Verify DELETE request was made
            assert mock_request.called
            call_args = mock_request.call_args
            assert call_args[0][0] == 'DELETE'
            assert call_args[0][1] == '/tables/test_table'
            
            assert result['message'] == 'Table deleted successfully'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
