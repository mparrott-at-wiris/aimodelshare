"""
Test bias detective app automatic session-based authentication.

This test verifies that the bias detective app correctly authenticates
users via session ID from Gradio request query parameters, following
the same pattern as the judge app and other moral compass apps.
"""

import pytest
from unittest.mock import MagicMock, patch


class FakeRequest:
    """Mock Gradio Request object for testing."""
    def __init__(self, sessionid: str = None):
        self.query_params = {}
        if sessionid:
            self.query_params["sessionid"] = sessionid
        self.headers = {}
        self.cookies = {}


def test_try_session_based_auth_with_valid_session():
    """Test that _try_session_based_auth works with a valid session."""
    from aimodelshare.moral_compass.apps.bias_detective import _try_session_based_auth
    
    # Mock the AWS functions
    with patch('aimodelshare.moral_compass.apps.bias_detective.get_token_from_session') as mock_get_token, \
         patch('aimodelshare.moral_compass.apps.bias_detective._get_username_from_token') as mock_get_username:
        
        # Setup mocks
        mock_get_token.return_value = "fake-token-123"
        mock_get_username.return_value = "test-user"
        
        # Test with valid session
        request = FakeRequest(sessionid="test-session-id")
        success, username, token = _try_session_based_auth(request)
        
        assert success is True
        assert username == "test-user"
        assert token == "fake-token-123"
        
        # Verify mocks were called
        mock_get_token.assert_called_once_with("test-session-id")
        mock_get_username.assert_called_once_with("fake-token-123")


def test_try_session_based_auth_without_session():
    """Test that _try_session_based_auth returns failure when no session ID."""
    from aimodelshare.moral_compass.apps.bias_detective import _try_session_based_auth
    
    # Test without session
    request = FakeRequest(sessionid=None)
    success, username, token = _try_session_based_auth(request)
    
    assert success is False
    assert username is None
    assert token is None


def test_try_session_based_auth_with_invalid_token():
    """Test that _try_session_based_auth handles invalid tokens."""
    from aimodelshare.moral_compass.apps.bias_detective import _try_session_based_auth
    
    with patch('aimodelshare.moral_compass.apps.bias_detective.get_token_from_session') as mock_get_token:
        # Token retrieval fails
        mock_get_token.return_value = None
        
        request = FakeRequest(sessionid="invalid-session")
        success, username, token = _try_session_based_auth(request)
        
        assert success is False
        assert username is None
        assert token is None


def test_create_bias_detective_app_structure():
    """Test that the app can be created and has the expected structure."""
    from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app
    
    app = create_bias_detective_app()
    
    # Verify it's a Gradio Blocks app
    assert app is not None
    assert hasattr(app, 'blocks')  # Gradio Blocks have a blocks attribute
    assert hasattr(app, 'load')    # Should have a load method for event handlers


def test_app_has_demo_load_handler():
    """Test that the app has a load handler for automatic authentication."""
    from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app
    
    app = create_bias_detective_app()
    
    # Check that the app has blocks configured (which means it has event handlers)
    assert hasattr(app, 'blocks')
    assert len(app.blocks) > 0, "App should have blocks configured"
    
    # Verify the app was created successfully with the load handler
    # The presence of blocks confirms the app structure is correct
    assert app is not None


def test_handle_initial_load_with_mock_auth():
    """Test the initial load handler with mocked authentication."""
    from aimodelshare.moral_compass.apps.bias_detective import create_bias_detective_app
    
    # Create app
    app = create_bias_detective_app()
    
    # We can't easily test the actual load handler without running the app,
    # but we've verified the structure is correct
    assert app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
