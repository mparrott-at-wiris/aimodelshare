"""
Session-based authentication helpers for multi-user Gradio apps in Cloud Run.

This module provides utilities for managing per-session authentication state
instead of using global environment variables, which are unsafe in multi-user
Cloud Run deployments where multiple users share the same container instance.

Key Design Principles:
- All authentication state is stored in Gradio State objects (per-session)
- No usage of os.environ for username, password, or tokens
- Thread-safe token generation
- Backward compatible with existing get_aws_token() function
"""

import logging
from typing import Optional, Dict, Any, Tuple
import os

# Import dependencies at module level
try:
    import botocore.config
    import boto3
    from aimodelshare.exceptions import AuthorizationError
except ImportError as e:
    # These are required dependencies
    raise ImportError(
        "Required dependencies not found. Ensure boto3 and botocore are installed."
    ) from e

logger = logging.getLogger("aimodelshare.moral_compass.apps.session_auth")


def generate_auth_token(username: str, password: str) -> str:
    """
    Generate an authentication token for a user session.
    
    This function wraps the existing get_aws_token() function from aimodelshare.aws
    but accepts username and password as parameters instead of reading from
    environment variables. This makes it safe for multi-user Cloud Run deployments.
    
    Args:
        username: The user's username
        password: The user's password
        
    Returns:
        str: The AWS authentication token (IdToken from Cognito)
        
    Raises:
        AuthorizationError: If authentication fails
        ValueError: If username or password is empty
        
    Example:
        >>> token = generate_auth_token("myuser", "mypass")
        >>> # Store token in Gradio State, not in os.environ
    """
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    
    if not password or not password.strip():
        raise ValueError("Password cannot be empty")
    
    try:
        # Get Cognito client ID from environment or use default
        # Note: This default is for the shared modelshare.ai Cognito pool
        client_id = os.getenv('COGNITO_CLIENT_ID', '7ptv9f8pt36elmg0e4v9v7jo9t')
        region = os.getenv('COGNITO_REGION', 'us-east-2')
        
        # Create unsigned config for Cognito client
        config = botocore.config.Config(signature_version=botocore.UNSIGNED)
        
        # Initialize Cognito provider client
        provider_client = boto3.client(
            "cognito-idp", 
            region_name=region, 
            config=config
        )
        
        # Authenticate with Cognito using USER_PASSWORD_AUTH flow
        response = provider_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username.strip(),
                "PASSWORD": password.strip()
            },
        )
        
        # Extract IdToken from response
        token = response["AuthenticationResult"]["IdToken"]
        
        logger.info(f"Successfully generated auth token for user: {username}")
        return token
        
    except Exception as err:
        logger.error(f"Authentication failed for user {username}: {err}")
        raise AuthorizationError(f"Could not authorize user. {str(err)}")


def create_session_state() -> Dict[str, Any]:
    """
    Create an initial session state dictionary for authentication.
    
    This state object should be stored in a Gradio State component and
    passed through all functions that need authentication information.
    
    Returns:
        Dict containing:
        - 'username': str or None
        - 'token': str or None
        - 'team_name': str or None
        - 'is_authenticated': bool
        
    Example:
        >>> session_state = gr.State(value=create_session_state())
    """
    return {
        'username': None,
        'token': None,
        'team_name': None,
        'is_authenticated': False
    }


def authenticate_session(
    session_state: Dict[str, Any],
    username: str,
    password: str
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Authenticate a user and update the session state.
    
    Args:
        session_state: Current session state dictionary
        username: Username to authenticate
        password: Password to authenticate
        
    Returns:
        Tuple of (updated_session_state, success, message)
        - updated_session_state: New session state with auth info
        - success: True if authentication succeeded
        - message: User-friendly message about authentication result
        
    Example:
        >>> session_state = create_session_state()
        >>> new_state, success, msg = authenticate_session(
        ...     session_state, "myuser", "mypass"
        ... )
        >>> if success:
        ...     print(f"Logged in as {new_state['username']}")
    """
    try:
        # Generate token
        token = generate_auth_token(username, password)
        
        # Update session state
        new_state = session_state.copy()
        new_state['username'] = username.strip()
        new_state['token'] = token
        new_state['is_authenticated'] = True
        
        message = f"✓ Successfully authenticated as {username}"
        logger.info(f"Session authenticated for user: {username}")
        
        return new_state, True, message
        
    except Exception as e:
        # Authentication failed - don't update state
        error_msg = f"⚠️ Authentication failed: {str(e)}"
        logger.error(f"Session authentication failed for user {username}: {e}")
        
        return session_state, False, error_msg


def get_session_token(session_state: Dict[str, Any]) -> Optional[str]:
    """
    Get the authentication token from session state.
    
    Args:
        session_state: Current session state dictionary
        
    Returns:
        The authentication token, or None if not authenticated
        
    Example:
        >>> token = get_session_token(session_state)
        >>> if token:
        ...     # User is authenticated, proceed with API call
        ...     api_client.set_token(token)
    """
    if session_state and session_state.get('is_authenticated'):
        return session_state.get('token')
    return None


def get_session_username(session_state: Dict[str, Any]) -> Optional[str]:
    """
    Get the username from session state.
    
    Args:
        session_state: Current session state dictionary
        
    Returns:
        The username, or None if not authenticated
    """
    if session_state and session_state.get('is_authenticated'):
        return session_state.get('username')
    return None


def is_session_authenticated(session_state: Dict[str, Any]) -> bool:
    """
    Check if the session is authenticated.
    
    Args:
        session_state: Current session state dictionary
        
    Returns:
        True if session is authenticated, False otherwise
    """
    return bool(session_state and session_state.get('is_authenticated'))


def set_session_team(
    session_state: Dict[str, Any],
    team_name: str
) -> Dict[str, Any]:
    """
    Set the team name in session state.
    
    Args:
        session_state: Current session state dictionary
        team_name: Team name to assign
        
    Returns:
        Updated session state dictionary
    """
    new_state = session_state.copy()
    new_state['team_name'] = team_name
    return new_state


def get_session_team(session_state: Dict[str, Any]) -> Optional[str]:
    """
    Get the team name from session state.
    
    Args:
        session_state: Current session state dictionary
        
    Returns:
        The team name, or None if not set
    """
    if session_state:
        return session_state.get('team_name')
    return None
