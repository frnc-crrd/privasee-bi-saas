"""
Authentication middleware for JWT token validation.

This module provides:
- JWT token validation decorator
- Token blacklist checking
- Current user retrieval
- Token refresh validation
"""

from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime, timezone
from flask import g, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from app.models import User
from app.extensions import db
from app.core.token_blacklist import token_blacklist
from app.exceptions.auth import (
    InvalidTokenError,
    ExpiredTokenError,
    AuthenticationError
)


def jwt_required_custom(optional: bool = False, fresh: bool = False) -> Callable:
    """
    Custom JWT required decorator with blacklist checking.

    This decorator extends Flask-JWT-Extended's jwt_required with
    additional token blacklist validation.

    Args:
        optional: If True, allows requests without tokens
        fresh: If True, requires a fresh token

    Returns:
        Decorator function

    Raises:
        AuthenticationError: If token is invalid or blacklisted

    Example:
        >>> @jwt_required_custom()
        >>> def protected_route():
        >>>     return {"message": "Protected"}
        >>>
        >>> @jwt_required_custom(optional=True)
        >>> def optional_auth_route():
        >>>     user = get_current_user()
        >>>     if user:
        >>>         return {"message": f"Hello {user.username}"}
        >>>     return {"message": "Hello anonymous"}
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                # Verify JWT is present and valid
                verify_jwt_in_request(optional=optional, fresh=fresh)

                # If optional and no token provided, proceed
                if optional:
                    try:
                        identity = get_jwt_identity()
                        if not identity:
                            return fn(*args, **kwargs)
                    except Exception:
                        return fn(*args, **kwargs)

                # Get token claims
                claims = get_jwt()
                jti = claims.get('jti')

                # Check if token is blacklisted
                if jti and token_blacklist.is_token_blacklisted(jti):
                    raise InvalidTokenError("Token has been revoked")

                # Check token expiry
                exp = claims.get('exp')
                if exp:
                    expiry_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                    if datetime.now(timezone.utc) >= expiry_time:
                        raise ExpiredTokenError("Token has expired")

                # Store user info in Flask g for easy access
                identity = get_jwt_identity()
                if identity:
                    user = db.session.get(User, int(identity))
                    if not user:
                        raise AuthenticationError("User not found")

                    if not user.is_active:
                        raise AuthenticationError("Account is disabled")

                    g.current_user = user
                    g.current_user_id = user.id
                    g.current_user_role = user.role

                return fn(*args, **kwargs)

            except ExpiredTokenError:
                current_app.logger.warning("Expired token attempt")
                raise
            except InvalidTokenError:
                current_app.logger.warning("Invalid or revoked token attempt")
                raise
            except Exception as e:
                current_app.logger.error(f"Authentication error: {str(e)}")
                raise AuthenticationError(f"Authentication failed: {str(e)}") from e

        return wrapper
    return decorator


def get_current_user() -> Optional[User]:
    """
    Get current authenticated user from Flask g.

    Returns:
        User object if authenticated, None otherwise

    Example:
        >>> @jwt_required_custom()
        >>> def my_route():
        >>>     user = get_current_user()
        >>>     return {"username": user.username}
    """
    return getattr(g, 'current_user', None)


def get_current_user_id() -> Optional[int]:
    """
    Get current authenticated user ID from Flask g.

    Returns:
        User ID if authenticated, None otherwise

    Example:
        >>> @jwt_required_custom()
        >>> def my_route():
        >>>     user_id = get_current_user_id()
        >>>     return {"user_id": user_id}
    """
    return getattr(g, 'current_user_id', None)


def get_current_user_role() -> Optional[str]:
    """
    Get current authenticated user role from Flask g.

    Returns:
        User role if authenticated, None otherwise

    Example:
        >>> @jwt_required_custom()
        >>> def my_route():
        >>>     role = get_current_user_role()
        >>>     return {"role": role}
    """
    return getattr(g, 'current_user_role', None)


def verify_refresh_token() -> Callable:
    """
    Decorator to verify refresh token (for token refresh endpoint).

    Returns:
        Decorator function

    Raises:
        AuthenticationError: If token is not a refresh token

    Example:
        >>> @verify_refresh_token()
        >>> def refresh_route():
        >>>     return {"access_token": "new_token"}
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Verify JWT is present
            verify_jwt_in_request(refresh=True)

            # Get token claims
            claims = get_jwt()

            # Verify it's a refresh token
            token_type = claims.get('type')
            if token_type != 'refresh':
                raise AuthenticationError("Invalid token type. Refresh token required.")

            # Check if token is blacklisted
            jti = claims.get('jti')
            if jti and token_blacklist.is_token_blacklisted(jti):
                raise InvalidTokenError("Refresh token has been revoked")

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def optional_jwt_auth() -> Callable:
    """
    Decorator for routes that optionally use JWT authentication.

    If a valid token is provided, user info is loaded.
    If no token or invalid token, request proceeds without user info.

    Returns:
        Decorator function

    Example:
        >>> @optional_jwt_auth()
        >>> def public_route():
        >>>     user = get_current_user()
        >>>     if user:
        >>>         return {"message": f"Hello {user.username}"}
        >>>     return {"message": "Hello anonymous"}
    """
    return jwt_required_custom(optional=True)
