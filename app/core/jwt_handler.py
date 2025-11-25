"""
JWT token creation, validation and refresh utilities.

This module handles all JWT-related operations including:
- Access token creation (1 hour expiry)
- Refresh token creation (7 days expiry)
- Token validation and decoding
- Token refresh logic
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
)
from app.exceptions.auth import InvalidTokenError, ExpiredTokenError


class JWTHandler:
    """Handles JWT token operations for authentication."""

    # Token expiry configurations
    ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    @staticmethod
    def create_tokens(user_id: int, additional_claims: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.

        Args:
            user_id: User ID to encode in token
            additional_claims: Optional additional claims to include in token

        Returns:
            Dictionary with 'access_token' and 'refresh_token'

        Example:
            >>> tokens = JWTHandler.create_tokens(user_id=1, additional_claims={'role': 'admin'})
            >>> print(tokens['access_token'])
        """
        identity = str(user_id)

        # Prepare additional claims
        claims = additional_claims or {}
        claims['created_at'] = datetime.now(timezone.utc).isoformat()

        # Create tokens with custom expiry
        access_token = create_access_token(
            identity=identity,
            additional_claims=claims,
            expires_delta=JWTHandler.ACCESS_TOKEN_EXPIRES
        )

        refresh_token = create_refresh_token(
            identity=identity,
            expires_delta=JWTHandler.REFRESH_TOKEN_EXPIRES
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(JWTHandler.ACCESS_TOKEN_EXPIRES.total_seconds())
        }

    @staticmethod
    def create_access_token_from_refresh(refresh_token_claims: Dict[str, Any]) -> str:
        """
        Create a new access token from refresh token claims.

        Args:
            refresh_token_claims: Claims from validated refresh token

        Returns:
            New access token string

        Raises:
            InvalidTokenError: If refresh token claims are invalid
        """
        identity = refresh_token_claims.get('sub')
        if not identity:
            raise InvalidTokenError("Invalid refresh token: missing subject")

        # Extract additional claims (exclude standard JWT claims)
        standard_claims = {'sub', 'iat', 'nbf', 'exp', 'jti', 'type', 'fresh'}
        additional_claims = {
            k: v for k, v in refresh_token_claims.items()
            if k not in standard_claims
        }
        additional_claims['created_at'] = datetime.now(timezone.utc).isoformat()

        return create_access_token(
            identity=identity,
            additional_claims=additional_claims,
            expires_delta=JWTHandler.ACCESS_TOKEN_EXPIRES
        )

    @staticmethod
    def get_current_user_id() -> int:
        """
        Get current user ID from JWT token.

        Returns:
            User ID as integer

        Raises:
            InvalidTokenError: If token identity is invalid

        Example:
            >>> # In a protected route
            >>> user_id = JWTHandler.get_current_user_id()
        """
        identity = get_jwt_identity()
        try:
            return int(identity)
        except (ValueError, TypeError) as e:
            raise InvalidTokenError(f"Invalid token identity: {identity}") from e

    @staticmethod
    def get_token_claims() -> Dict[str, Any]:
        """
        Get all claims from current JWT token.

        Returns:
            Dictionary with all token claims

        Example:
            >>> claims = JWTHandler.get_token_claims()
            >>> user_role = claims.get('role')
        """
        return get_jwt()

    @staticmethod
    def get_token_jti() -> str:
        """
        Get JWT ID (jti) from current token for blacklisting.

        Returns:
            JWT ID string
        """
        claims = get_jwt()
        return claims.get('jti', '')

    @staticmethod
    def validate_token_expiry(claims: Dict[str, Any]) -> None:
        """
        Validate that token has not expired.

        Args:
            claims: Token claims dictionary

        Raises:
            ExpiredTokenError: If token has expired
        """
        exp = claims.get('exp')
        if not exp:
            raise InvalidTokenError("Token missing expiration claim")

        expiry_time = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) >= expiry_time:
            raise ExpiredTokenError("Token has expired")

    @staticmethod
    def extract_user_role(claims: Dict[str, Any]) -> Optional[str]:
        """
        Extract user role from token claims.

        Args:
            claims: Token claims dictionary

        Returns:
            User role string or None if not present
        """
        return claims.get('role')

    @staticmethod
    def is_token_fresh(claims: Dict[str, Any]) -> bool:
        """
        Check if token is fresh (recently created).

        Args:
            claims: Token claims dictionary

        Returns:
            True if token is fresh, False otherwise
        """
        return claims.get('fresh', False)
