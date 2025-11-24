"""Request context tracking and distributed tracing support.

This module provides infrastructure for tracking requests across the application:
- Automatic request ID generation for distributed tracing
- X-Request-ID header injection in responses
- User context tracking for authenticated requests
- Thread-safe context storage using Flask's g object
- Support for propagating context in async operations

Request IDs enable:
- Correlating logs across multiple services
- Debugging distributed systems
- Request performance tracking
- Error tracing and debugging

Usage:
    from app.core.context import setup_request_context

    # In application factory
    app = Flask(__name__)
    setup_request_context(app)

    # Access request context anywhere
    from app.core.context import get_request_id, set_user_context
    request_id = get_request_id()
    set_user_context(user_id=123, username="john_doe")
"""

import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from flask import Flask, g, has_request_context, request
from flask.wrappers import Response


def generate_request_id() -> str:
    """Generate a unique request ID.

    Creates a UUID4-based identifier for request tracing.

    Returns:
        Unique request ID string

    Example:
        >>> generate_request_id()
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get the current request ID from Flask context.

    Returns:
        Request ID if available, None otherwise

    Example:
        >>> # Within a Flask request
        >>> get_request_id()
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        >>> # Outside request context
        >>> get_request_id()
        None
    """
    if has_request_context():
        return getattr(g, "request_id", None)
    return None


def set_request_id(request_id: str) -> None:
    """Set the request ID in Flask context.

    Args:
        request_id: Request ID to store

    Returns:
        None

    Example:
        >>> set_request_id("custom-request-id-123")
    """
    if has_request_context():
        g.request_id = request_id


def get_user_context() -> Dict[str, Any]:
    """Get the current user context from Flask g object.

    Returns:
        Dictionary with user_id, username, role, etc. (empty if not set)

    Example:
        >>> user_context = get_user_context()
        >>> print(user_context)
        {'user_id': 123, 'username': 'john_doe', 'role': 'admin'}
    """
    if has_request_context():
        return {
            "user_id": getattr(g, "user_id", None),
            "username": getattr(g, "username", None),
            "role": getattr(g, "role", None),
            "email": getattr(g, "email", None),
        }
    return {}


def set_user_context(
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """Set user context in Flask g object.

    Should be called after authentication to track the authenticated user
    throughout the request lifecycle.

    Args:
        user_id: User's database ID
        username: User's username
        role: User's role (admin, viewer, analyst)
        email: User's email address

    Returns:
        None

    Example:
        >>> # In authentication middleware
        >>> set_user_context(user_id=123, username="john", role="admin")
    """
    if has_request_context():
        if user_id is not None:
            g.user_id = user_id
        if username is not None:
            g.username = username
        if role is not None:
            g.role = role
        if email is not None:
            g.email = email


def clear_user_context() -> None:
    """Clear user context from Flask g object.

    Useful for testing or after logout operations.

    Returns:
        None

    Example:
        >>> clear_user_context()
    """
    if has_request_context():
        for attr in ["user_id", "username", "role", "email"]:
            if hasattr(g, attr):
                delattr(g, attr)


@contextmanager
def request_context(
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Context manager for operations outside Flask request context.

    Useful for background tasks, CLI commands, or async operations that
    need request tracking.

    Args:
        request_id: Optional request ID (generated if not provided)
        user_id: Optional user ID for context

    Yields:
        Context dictionary with request_id and user_id

    Example:
        >>> from app.core.context import request_context
        >>> with request_context(user_id=123) as ctx:
        ...     logger.info("Processing task", extra={"request_id": ctx["request_id"]})
    """
    context = {
        "request_id": request_id or generate_request_id(),
        "user_id": user_id,
    }

    try:
        yield context
    finally:
        pass  # Cleanup if needed


def setup_request_context(app: Flask) -> None:
    """Configure request context tracking middleware.

    Registers Flask before_request and after_request handlers to:
    - Generate or extract request IDs
    - Inject X-Request-ID header in responses
    - Track request lifecycle

    Args:
        app: Flask application instance

    Returns:
        None

    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> setup_request_context(app)
    """

    @app.before_request
    def before_request_handler() -> None:
        """Extract or generate request ID before processing request.

        Checks for X-Request-ID header in incoming request.
        If not present, generates a new UUID.
        Stores request_id in Flask g object.
        """
        # Extract request ID from header or generate new one
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = incoming_request_id if incoming_request_id else generate_request_id()

        # Store in Flask g object
        set_request_id(request_id)

        # Log request start (optional, can be enabled via config)
        # app.logger.debug(
        #     f"Request started: {request.method} {request.path}",
        #     extra={"request_id": request_id}
        # )

    @app.after_request
    def after_request_handler(response: Response) -> Response:
        """Inject request ID into response headers.

        Adds X-Request-ID header to all responses for client-side tracing.

        Args:
            response: Flask response object

        Returns:
            Modified response with X-Request-ID header
        """
        request_id = get_request_id()
        if request_id:
            response.headers["X-Request-ID"] = request_id

        return response


def get_full_context() -> Dict[str, Any]:
    """Get complete request and user context.

    Convenience function that combines request_id and user context
    into a single dictionary.

    Returns:
        Dictionary with all context information

    Example:
        >>> get_full_context()
        {
            'request_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            'user_id': 123,
            'username': 'john_doe',
            'role': 'admin',
            'email': 'john@example.com'
        }
    """
    context = {"request_id": get_request_id()}
    context.update(get_user_context())
    return context


def log_context() -> Dict[str, Any]:
    """Get context dictionary suitable for structured logging.

    Returns only non-None values for cleaner log output.

    Returns:
        Dictionary with context values (excluding None values)

    Example:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("User action", extra=log_context())
    """
    context = get_full_context()
    return {k: v for k, v in context.items() if v is not None}
