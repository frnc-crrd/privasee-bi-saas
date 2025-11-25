"""
Security middleware for HTTP security headers and request validation.

This module provides:
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Request context tracking (X-Request-ID)
- CORS configuration helpers
- Request logging
"""

from typing import Any, Callable
from functools import wraps
import uuid
from flask import request, g, current_app, Response
from datetime import datetime


def apply_security_headers(response: Response) -> Response:
    """
    Apply security headers to Flask response.

    Headers applied:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin

    Args:
        response: Flask response object

    Returns:
        Response with security headers applied

    Example:
        >>> # In app factory
        >>> @app.after_request
        >>> def add_security_headers(response):
        >>>     return apply_security_headers(response)
    """
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Enforce HTTPS (only in production)
    if not current_app.config.get('DEBUG', False):
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains; preload'
        )

    # Content Security Policy
    # Note: Adjust CSP based on your frontend requirements
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers['Content-Security-Policy'] = csp_policy

    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions Policy (formerly Feature-Policy)
    response.headers['Permissions-Policy'] = (
        'geolocation=(), microphone=(), camera=()'
    )

    return response


def track_request_context() -> None:
    """
    Add request context tracking (X-Request-ID).

    Generates or uses existing X-Request-ID header for request tracking.
    Stores request ID in Flask g for use in logging.

    Example:
        >>> # In app factory
        >>> @app.before_request
        >>> def before_request():
        >>>     track_request_context()
    """
    # Get or generate request ID
    request_id = request.headers.get('X-Request-ID')
    if not request_id:
        request_id = str(uuid.uuid4())

    # Store in Flask g for access in request context
    g.request_id = request_id

    # Store request metadata
    g.request_start_time = datetime.utcnow()
    g.request_method = request.method
    g.request_path = request.path


def log_request_info() -> None:
    """
    Log incoming request information.

    Logs request method, path, IP address, and request ID.

    Example:
        >>> # In app factory
        >>> @app.before_request
        >>> def before_request():
        >>>     track_request_context()
        >>>     log_request_info()
    """
    request_id = getattr(g, 'request_id', 'unknown')
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'unknown')

    current_app.logger.info(
        f"Request: {request.method} {request.path} | "
        f"IP: {ip_address} | "
        f"Request-ID: {request_id} | "
        f"User-Agent: {user_agent}"
    )


def log_response_info(response: Response) -> Response:
    """
    Log response information including execution time.

    Args:
        response: Flask response object

    Returns:
        Response object (unchanged)

    Example:
        >>> # In app factory
        >>> @app.after_request
        >>> def after_request(response):
        >>>     return log_response_info(response)
    """
    request_id = getattr(g, 'request_id', 'unknown')
    start_time = getattr(g, 'request_start_time', None)

    execution_time = 'unknown'
    if start_time:
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        execution_time = f"{duration:.2f}ms"

    current_app.logger.info(
        f"Response: {response.status_code} | "
        f"Request-ID: {request_id} | "
        f"Execution-Time: {execution_time}"
    )

    # Add request ID to response headers
    response.headers['X-Request-ID'] = request_id

    return response


def validate_content_type(allowed_types: list = None) -> Callable:
    """
    Decorator to validate request Content-Type.

    Args:
        allowed_types: List of allowed content types

    Returns:
        Decorator function

    Raises:
        ValueError: If Content-Type is not allowed

    Example:
        >>> @validate_content_type(['application/json'])
        >>> def create_user():
        >>>     # Only accepts JSON requests
        >>>     return {"message": "User created"}
    """
    if allowed_types is None:
        allowed_types = ['application/json']

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            content_type = request.content_type

            # Skip validation for GET requests (no body)
            if request.method == 'GET':
                return fn(*args, **kwargs)

            if content_type not in allowed_types:
                current_app.logger.warning(
                    f"Invalid Content-Type: {content_type}. "
                    f"Allowed: {allowed_types}"
                )
                return {
                    'error': 'Invalid Content-Type',
                    'message': f'Content-Type must be one of: {", ".join(allowed_types)}',
                    'allowed_types': allowed_types
                }, 415

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def cors_config() -> dict:
    """
    Get CORS configuration for Flask-CORS.

    Returns:
        Dictionary with CORS configuration

    Example:
        >>> # In app factory
        >>> from flask_cors import CORS
        >>> CORS(app, **cors_config())
    """
    return {
        'origins': [
            'http://localhost:3000',  # React dev server
            'http://localhost:5000',  # Flask dev server
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5000',
        ],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': [
            'Content-Type',
            'Authorization',
            'X-Request-ID',
        ],
        'expose_headers': [
            'X-Request-ID',
            'X-Total-Count',
        ],
        'supports_credentials': True,
        'max_age': 3600,
    }


def sanitize_input(data: str, max_length: int = 1000) -> str:
    """
    Basic input sanitization for user-provided strings.

    Args:
        data: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Example:
        >>> clean_input = sanitize_input(user_input)
    """
    if not data:
        return ''

    # Trim to max length
    sanitized = data[:max_length]

    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()

    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')

    return sanitized


class SecurityConfig:
    """
    Security configuration constants.

    These can be overridden in config.py based on environment.
    """

    # Maximum request body size (in bytes)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Session configuration
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

    # JWT configuration
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days

    # Rate limiting (requests per minute)
    RATE_LIMIT_DEFAULT = '100/minute'
    RATE_LIMIT_AUTH = '5/minute'  # Stricter for auth endpoints

    # Allowed file upload extensions
    ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'csv', 'txt'}

    # CORS allowed origins (production)
    CORS_ORIGINS_PRODUCTION = [
        'https://your-production-domain.com',
    ]

    @staticmethod
    def is_safe_url(target: str) -> bool:
        """
        Check if redirect URL is safe (same domain).

        Args:
            target: URL to check

        Returns:
            True if URL is safe, False otherwise

        Example:
            >>> if SecurityConfig.is_safe_url(next_url):
            >>>     return redirect(next_url)
        """
        from urllib.parse import urlparse, urljoin
        from flask import request

        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))

        return test_url.scheme in ('http', 'https') and \
               ref_url.netloc == test_url.netloc
