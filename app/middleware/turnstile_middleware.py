# app/middleware/turnstile_middleware.py
"""
Turnstile Middleware
--------------------
Decorator for protecting endpoints with Cloudflare Turnstile bot verification.

Applies Turnstile challenge to sensitive endpoints (login, registration, password reset)
to prevent automated attacks while maintaining good user experience.
"""

from functools import wraps
from typing import Callable, Any
from flask import request

from app.core.responses import error_response
from app.services.turnstile_service import TurnstileService


def require_turnstile(
    token_param: str = 'cf-turnstile-response',
    token_location: str = 'form'
) -> Callable:
    """
    Decorator to require Turnstile verification for an endpoint.

    Extracts Turnstile token from request and verifies it with Cloudflare.
    Rejects request with 403 Forbidden if verification fails.

    Args:
        token_param: Name of parameter containing Turnstile token
                    (default: 'cf-turnstile-response')
        token_location: Where to find token ('form', 'json', 'args')
                       (default: 'form')

    Returns:
        Decorator function that wraps the endpoint

    Usage:
        @app.route('/login', methods=['POST'])
        @require_turnstile()
        def login():
            # Turnstile already verified, proceed with authentication
            pass

        @app.route('/api/register', methods=['POST'])
        @require_turnstile(token_location='json')
        def register():
            # Verify JSON payload Turnstile token
            pass

    Security:
        - Automatically skipped when Turnstile is disabled (dev/test mode)
        - Extracts real client IP for verification
        - Returns 403 with security-friendly error message
        - Logs all verification attempts

    Token Locations:
        - 'form': HTML form data (POST with Content-Type: multipart/form-data)
        - 'json': JSON request body (POST with Content-Type: application/json)
        - 'args': URL query parameters (GET requests)
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Skip verification if Turnstile is disabled
            if not TurnstileService.is_enabled():
                return f(*args, **kwargs)

            # Extract token based on location
            token = None
            if token_location == 'form':
                token = request.form.get(token_param)
            elif token_location == 'json':
                json_data = request.get_json(silent=True) or {}
                token = json_data.get(token_param)
            elif token_location == 'args':
                token = request.args.get(token_param)
            else:
                raise ValueError(
                    f"Invalid token_location: {token_location}. "
                    f"Must be 'form', 'json', or 'args'"
                )

            # Verify token
            if not TurnstileService.verify_token(token):
                return error_response(
                    message="Verification failed. Please try again.",
                    status_code=403
                )

            # Token verified, proceed with endpoint
            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_turnstile_json() -> Callable:
    """
    Convenience decorator for JSON API endpoints.

    Equivalent to @require_turnstile(token_location='json')

    Usage:
        @app.route('/api/v1/auth/login', methods=['POST'])
        @require_turnstile_json()
        def login():
            pass
    """
    return require_turnstile(token_location='json')


def require_turnstile_form() -> Callable:
    """
    Convenience decorator for HTML form endpoints.

    Equivalent to @require_turnstile(token_location='form')

    Usage:
        @app.route('/login', methods=['POST'])
        @require_turnstile_form()
        def login():
            pass
    """
    return require_turnstile(token_location='form')
