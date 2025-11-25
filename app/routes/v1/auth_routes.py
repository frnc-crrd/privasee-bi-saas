"""
Authentication routes for user registration, login, logout, and token management.

Endpoints:
- POST /api/v1/auth/register - User registration
- POST /api/v1/auth/login - User login
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - User logout (token revocation)
- POST /api/v1/auth/password/change - Change password
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity
from pydantic import ValidationError as PydanticValidationError
from app.services.auth_service import AuthService
from app.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
)
from app.middleware.auth_middleware import jwt_required_custom, verify_refresh_token
from app.core.responses import success_response, error_response
from app.exceptions.auth import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    AuthenticationError,
)
from app.exceptions.validation import ValidationError
from app.extensions import limiter


# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize service
auth_service = AuthService()


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("10/hour")  # Limit registration attempts
def register():
    """
    Register a new user.

    Request Body:
        {
            "username": "johndoe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "role": "viewer"  // optional, defaults to "viewer"
        }

    Returns:
        201: User created with tokens
        400: Validation error
        409: User already exists

    Example:
        $ curl -X POST http://localhost:5000/api/v1/auth/register \\
          -H "Content-Type: application/json" \\
          -d '{"username":"johndoe","email":"john@example.com","password":"SecurePass123!"}'
    """
    try:
        # Parse and validate request data
        data = request.get_json()
        register_data = RegisterRequest(**data)

        # Register user
        result = auth_service.register_user(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            role=register_data.role
        )

        current_app.logger.info(f"User registered: {register_data.username}")

        return success_response(
            data=result,
            message="User registered successfully",
            status_code=201
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            details={"validation_errors": e.errors()},
            status_code=400
        )
    except UserAlreadyExistsError as e:
        return error_response(
            message=str(e),
            status_code=409
        )
    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return error_response(
            message="Registration failed",
            status_code=500
        )


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5/minute")  # Strict rate limiting for brute force protection
def login():
    """
    Authenticate user and return tokens.

    Request Body:
        {
            "email": "john@example.com",
            "password": "SecurePass123!"
        }

    Returns:
        200: Login successful with tokens
        401: Invalid credentials
        400: Validation error

    Example:
        $ curl -X POST http://localhost:5000/api/v1/auth/login \\
          -H "Content-Type: application/json" \\
          -d '{"email":"john@example.com","password":"SecurePass123!"}'
    """
    try:
        # Parse and validate request data
        data = request.get_json()
        login_data = LoginRequest(**data)

        # Authenticate user
        result = auth_service.authenticate_user(
            email=login_data.email,
            password=login_data.password
        )

        current_app.logger.info(f"User logged in: {login_data.email}")

        return success_response(
            data=result,
            message="Login successful"
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            details={"validation_errors": e.errors()},
            status_code=400
        )
    except InvalidCredentialsError as e:
        return error_response(
            message=str(e),
            status_code=401
        )
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return error_response(
            message="Login failed",
            status_code=500
        )


@auth_bp.route('/refresh', methods=['POST'])
@verify_refresh_token()
def refresh():
    """
    Refresh access token using refresh token.

    Headers:
        Authorization: Bearer <refresh_token>

    Returns:
        200: New access token
        401: Invalid or expired refresh token

    Example:
        $ curl -X POST http://localhost:5000/api/v1/auth/refresh \\
          -H "Authorization: Bearer <refresh_token>"
    """
    try:
        # Get refresh token claims
        claims = get_jwt()

        # Generate new access token
        result = auth_service.refresh_access_token(claims)

        current_app.logger.info(f"Token refreshed for user: {get_jwt_identity()}")

        return success_response(
            data=result,
            message="Token refreshed successfully"
        )

    except AuthenticationError as e:
        return error_response(
            message=str(e),
            status_code=401
        )
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return error_response(
            message="Token refresh failed",
            status_code=500
        )


@auth_bp.route('/logout', methods=['POST'])
@jwt_required_custom()
def logout():
    """
    Logout user by blacklisting current token.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Logout successful

    Example:
        $ curl -X POST http://localhost:5000/api/v1/auth/logout \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get token claims
        claims = get_jwt()
        jti = claims['jti']
        exp = claims['exp']
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        # Logout user (blacklist token)
        auth_service.logout_user(jti, exp_datetime)

        current_app.logger.info(f"User logged out: {get_jwt_identity()}")

        return success_response(
            message="Logout successful"
        )

    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return error_response(
            message="Logout failed",
            status_code=500
        )


@auth_bp.route('/password/change', methods=['POST'])
@jwt_required_custom()
def change_password():
    """
    Change user password.

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
        {
            "old_password": "OldPass123!",
            "new_password": "NewPass456!"
        }

    Returns:
        200: Password changed successfully
        401: Invalid old password
        400: Validation error

    Example:
        $ curl -X POST http://localhost:5000/api/v1/auth/password/change \\
          -H "Authorization: Bearer <access_token>" \\
          -H "Content-Type: application/json" \\
          -d '{"old_password":"OldPass123!","new_password":"NewPass456!"}'
    """
    try:
        # Parse and validate request data
        data = request.get_json()
        password_data = ChangePasswordRequest(**data)

        # Get current user ID
        user_id = int(get_jwt_identity())

        # Change password
        auth_service.change_password(
            user_id=user_id,
            old_password=password_data.old_password,
            new_password=password_data.new_password
        )

        current_app.logger.info(f"Password changed for user: {user_id}")

        return success_response(
            message="Password changed successfully"
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            details={"validation_errors": e.errors()},
            status_code=400
        )
    except InvalidCredentialsError as e:
        return error_response(
            message=str(e),
            status_code=401
        )
    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except Exception as e:
        current_app.logger.error(f"Password change error: {str(e)}")
        return error_response(
            message="Password change failed",
            status_code=500
        )


@auth_bp.route('/me', methods=['GET'])
@jwt_required_custom()
def get_current_user_info():
    """
    Get current authenticated user information.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User information

    Example:
        $ curl -X GET http://localhost:5000/api/v1/auth/me \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        from app.middleware.auth_middleware import get_current_user

        user = get_current_user()

        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }

        return success_response(
            data={'user': user_data},
            message="User information retrieved successfully"
        )

    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        return error_response(
            message="Failed to retrieve user information",
            status_code=500
        )
