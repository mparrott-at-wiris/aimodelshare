"""
Authentication and identity management helpers for aimodelshare.

Provides unified authentication around Cognito IdToken (JWT_AUTHORIZATION_TOKEN),
with backward compatibility for legacy AWS_TOKEN.
"""

import os
import warnings
import logging
from typing import Optional, Dict, Any
import json

logger = logging.getLogger("aimodelshare.auth")

try:
    import jwt
except ImportError:
    jwt = None
    logger.warning("PyJWT not installed. JWT decode functionality will be limited.")


def get_primary_token() -> Optional[str]:
    """
    Get the primary authentication token from environment variables.
    
    Prefers JWT_AUTHORIZATION_TOKEN over legacy AWS_TOKEN.
    Issues a deprecation warning if only AWS_TOKEN is present.
    
    Returns:
        Optional[str]: The authentication token, or None if not found
    """
    jwt_token = os.getenv('JWT_AUTHORIZATION_TOKEN')
    if jwt_token:
        return jwt_token
    
    aws_token = os.getenv('AWS_TOKEN')
    if aws_token:
        warnings.warn(
            "Using legacy AWS_TOKEN environment variable. "
            "Please migrate to JWT_AUTHORIZATION_TOKEN. "
            "AWS_TOKEN support will be deprecated in a future release.",
            DeprecationWarning,
            stacklevel=2
        )
        return aws_token
    
    return None


def get_identity_claims(token: Optional[str] = None, verify: bool = False) -> Dict[str, Any]:
    """
    Extract identity claims from a JWT token.
    
    Args:
        token: JWT token string. If None, uses get_primary_token()
        verify: If True, performs signature verification (requires JWKS endpoint)
                Currently defaults to False as JWKS verification is future work
    
    Returns:
        Dict containing identity claims:
        - sub: Subject (user ID)
        - email: User email
        - cognito:username: Username (if present)
        - iss: Issuer
        - principal: Derived principal identifier
    
    Raises:
        ValueError: If token is invalid or missing
        RuntimeError: If PyJWT is not installed
    
    Note:
        This currently performs unverified decode as JWKS signature verification
        is planned for future work. Do not use in production security-critical
        contexts without implementing signature verification.
    """
    if token is None:
        token = get_primary_token()
    
    if not token:
        raise ValueError("No authentication token available")
    
    if jwt is None:
        raise RuntimeError("PyJWT not installed. Install with: pip install PyJWT>=2.4.0")
    
    # TODO: Implement JWKS signature verification (future work)
    # For now, perform unverified decode
    if verify:
        warnings.warn(
            "JWT signature verification requested but not yet implemented. "
            "Using unverified decode. This should not be used in production "
            "for security-critical operations.",
            UserWarning,
            stacklevel=2
        )
    
    try:
        # Unverified decode - JWKS verification is future work
        claims = jwt.decode(token, options={"verify_signature": False})
        
        # Derive principal from claims
        # Priority: cognito:username > email > sub
        principal = (
            claims.get('cognito:username') or 
            claims.get('email') or 
            claims.get('sub')
        )
        
        if principal:
            claims['principal'] = principal
        
        return claims
    
    except jwt.DecodeError as e:
        raise ValueError(f"Invalid JWT token: {e}")
    except Exception as e:
        raise ValueError(f"Failed to decode JWT token: {e}")


def derive_principal(claims: Dict[str, Any]) -> str:
    """
    Derive a principal identifier from identity claims.
    
    Args:
        claims: Identity claims dictionary
    
    Returns:
        str: Principal identifier
    
    Raises:
        ValueError: If no suitable principal identifier found
    """
    principal = (
        claims.get('principal') or
        claims.get('cognito:username') or
        claims.get('email') or
        claims.get('sub')
    )
    
    if not principal:
        raise ValueError("No principal identifier found in claims")
    
    return str(principal)


def is_admin(claims: Dict[str, Any]) -> bool:
    """
    Check if the identity has admin privileges.
    
    Args:
        claims: Identity claims dictionary
    
    Returns:
        bool: True if user has admin privileges
    
    Note:
        Currently checks for 'cognito:groups' containing 'admin'.
        Extend this logic as needed for your authorization model.
    """
    groups = claims.get('cognito:groups', [])
    if isinstance(groups, list):
        return 'admin' in groups
    return False
