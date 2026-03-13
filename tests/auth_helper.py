#!/usr/bin/env python3
"""
Cognito authentication helper for integration tests.

Obtains a JWT IdToken via USER_PASSWORD_AUTH flow.
Credentials come from environment variables: username, password.

Usage:
    # As a module
    from auth_helper import get_auth_token
    token = get_auth_token()

    # As a CLI (prints token to stdout for shell scripts)
    python tests/auth_helper.py
"""

import os
import sys

COGNITO_CLIENT_ID = "7ptv9f8pt36elmg0e4v9v7jo9t"
COGNITO_REGION = "us-east-2"


def get_auth_token() -> str:
    """Authenticate with Cognito and return an IdToken JWT."""
    import boto3
    import botocore.config

    username = os.environ.get("username")
    password = os.environ.get("password")

    if not username or not password:
        raise RuntimeError(
            "Missing credentials: set 'username' and 'password' environment variables"
        )

    config = botocore.config.Config(signature_version=botocore.UNSIGNED)
    client = boto3.client("cognito-idp", region_name=COGNITO_REGION, config=config)

    response = client.initiate_auth(
        ClientId=COGNITO_CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )

    return response["AuthenticationResult"]["IdToken"]


def get_principal_from_token(token: str) -> str:
    """Extract the principal (cognito:username > email > sub) from a JWT."""
    import json
    import base64

    # Decode JWT payload without verification (matches Lambda behavior)
    payload = token.split(".")[1]
    # Add padding
    payload += "=" * (4 - len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))

    return (
        claims.get("cognito:username")
        or claims.get("email")
        or claims.get("sub")
    )


if __name__ == "__main__":
    try:
        token = get_auth_token()
        principal = get_principal_from_token(token)
        # Print as key=value lines for easy parsing in shell
        print(f"token={token}")
        print(f"principal={principal}")
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
