"""
Authentication routes for user registration, login, logout, and token management.

Endpoints:
- POST /api/v1/auth/register - User registration
- POST /api/v1/auth/login - User login
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - User logout (token revocation)
- POST /api/v1/auth/password/change - Change password
"""

from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, decode_token
from pydantic import ValidationError as PydanticValidationError
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.audit_service import AuditService
from app.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema,
    PasswordResetResponseSchema,
)
from app.middleware.auth_middleware import jwt_required_custom, verify_refresh_token
from app.middleware.turnstile_middleware import require_turnstile_json
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
@require_turnstile_json()  # Bot protection
def register():
    """
    Register a new user account.
    ---
    tags:
      - Authentication
    summary: Register a new user
    description: |
      Creates a new user account with email and password authentication.
      Rate limited to 10 registrations per hour per IP address.
      Requires bot protection via Cloudflare Turnstile (if enabled).
    parameters:
      - in: body
        name: body
        required: true
        description: User registration data
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              example: johndoe
              description: Unique username (3-50 characters)
            email:
              type: string
              format: email
              example: john@example.com
              description: Valid email address
            password:
              type: string
              format: password
              example: SecurePass123!
              description: Password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char)
            role:
              type: string
              enum: [viewer, analyst, admin]
              default: viewer
              description: User role (optional, defaults to viewer)
    responses:
      201:
        description: User registered successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User registered successfully
            data:
              type: object
              properties:
                user:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 1
                    username:
                      type: string
                      example: johndoe
                    email:
                      type: string
                      example: john@example.com
                    role:
                      type: string
                      example: viewer
                    is_active:
                      type: boolean
                      example: true
                    created_at:
                      type: string
                      format: date-time
                access_token:
                  type: string
                  description: JWT access token (valid for 1 hour)
                refresh_token:
                  type: string
                  description: JWT refresh token (valid for 7 days)
      400:
        description: Validation error (invalid input data)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Validation error
            errors:
              type: object
      409:
        description: User already exists (email or username conflict)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: User already exists
      429:
        description: Rate limit exceeded (too many registration attempts)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Rate limit exceeded
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

        # Audit log user creation
        AuditService.log_user_created(
            user_id=result['user']['id'],
            username=result['user']['username'],
            details={'role': register_data.role},
            status_code=201
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
@require_turnstile_json()  # Bot protection
def login():
    """
    Authenticate user and return JWT tokens.
    ---
    tags:
      - Authentication
    summary: User login
    description: |
      Authenticates a user with email and password, returns access and refresh tokens.
      Rate limited to 5 login attempts per minute per IP for brute-force protection.
      Requires bot protection via Cloudflare Turnstile (if enabled).
    parameters:
      - in: body
        name: body
        required: true
        description: Login credentials
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
              example: john@example.com
              description: User email address
            password:
              type: string
              format: password
              example: SecurePass123!
              description: User password
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Login successful
            data:
              type: object
              properties:
                user:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 1
                    username:
                      type: string
                      example: johndoe
                    email:
                      type: string
                      example: john@example.com
                    role:
                      type: string
                      example: viewer
                    is_active:
                      type: boolean
                      example: true
                    last_login:
                      type: string
                      format: date-time
                access_token:
                  type: string
                  description: JWT access token (valid for 1 hour)
                refresh_token:
                  type: string
                  description: JWT refresh token (valid for 7 days)
      400:
        description: Validation error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Validation error
      401:
        description: Invalid credentials or account disabled
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Invalid credentials
      429:
        description: Rate limit exceeded (too many login attempts)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Rate limit exceeded
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

        # Audit log successful login
        AuditService.log_login(
            user_id=result['user']['id'],
            username=result['user']['username'],
            status_code=200
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
        # Audit log failed login attempt
        AuditService.log_login_failed(
            username=login_data.email,
            status_code=401,
            details={'reason': 'invalid_credentials'}
        )

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
    Refresh access token using a valid refresh token.
    ---
    tags:
      - Authentication
    summary: Refresh access token
    description: |
      Generates a new access token using a valid refresh token.
      The refresh token has a longer lifetime (7 days) compared to access tokens (1 hour).
      Use this endpoint when the access token expires to obtain a new one without re-authentication.
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token with refresh token (not access token)
        example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    responses:
      200:
        description: Token refreshed successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Token refreshed successfully
            data:
              type: object
              properties:
                access_token:
                  type: string
                  description: New access token (valid for 1 hour)
                  example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                token_type:
                  type: string
                  example: Bearer
                expires_in:
                  type: integer
                  description: Access token lifetime in seconds
                  example: 3600
      401:
        description: Invalid or expired refresh token
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Invalid or expired refresh token
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Token refresh failed
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
    Logout user and invalidate current access token.
    ---
    tags:
      - Authentication
    summary: Logout user
    description: |
      Logs out the authenticated user by blacklisting their current access token.
      The token will be invalidated immediately and cannot be used for future requests.
      This ensures secure session termination.

      Note: Refresh tokens are not automatically invalidated. Users should discard them client-side.
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token with access token (not refresh token)
        example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    responses:
      200:
        description: Logout successful, token blacklisted
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Logout successful
      401:
        description: Unauthorized (missing or invalid token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Missing or invalid token
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Logout failed
    """
    try:
        # Get token claims
        claims = get_jwt()
        jti = claims['jti']
        exp = claims['exp']
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        user_id = int(get_jwt_identity())
        username = claims.get('username', '')

        # Logout user (blacklist token)
        auth_service.logout_user(jti, exp_datetime)

        # Audit log logout
        AuditService.log_logout(
            user_id=user_id,
            username=username,
            status_code=200
        )

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
    Change authenticated user's password.
    ---
    tags:
      - Authentication
    summary: Change password
    description: |
      Allows an authenticated user to change their password by providing the current password
      and a new password. The new password must meet security requirements:
      - Minimum 8 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character

      This action is logged for security auditing purposes.
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token with access token
        example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      - in: body
        name: body
        required: true
        description: Current and new password
        schema:
          type: object
          required:
            - old_password
            - new_password
          properties:
            old_password:
              type: string
              format: password
              description: Current password
              example: "OldPass123!"
            new_password:
              type: string
              format: password
              description: New password (must meet security requirements)
              example: "NewSecurePass456!"
    responses:
      200:
        description: Password changed successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Password changed successfully
      400:
        description: Validation error (password requirements not met)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Validation error
            details:
              type: object
              properties:
                validation_errors:
                  type: array
                  items:
                    type: object
      401:
        description: Unauthorized (invalid old password or missing token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Invalid old password
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Password change failed
    """
    try:
        # Parse and validate request data
        data = request.get_json()
        password_data = ChangePasswordRequest(**data)

        # Get current user ID and username from JWT
        user_id = int(get_jwt_identity())
        claims = get_jwt()
        username = claims.get('username', '')

        # Change password
        auth_service.change_password(
            user_id=user_id,
            old_password=password_data.old_password,
            new_password=password_data.new_password
        )

        # Audit log password change
        AuditService.log_password_change(
            user_id=user_id,
            username=username,
            status_code=200
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
    Get current authenticated user's profile information.
    ---
    tags:
      - Authentication
    summary: Get current user profile
    description: |
      Retrieves the profile information of the currently authenticated user based on the JWT token.
      Returns user details including ID, username, email, role, and account status.

      This endpoint is useful for:
      - Displaying user profile in the UI
      - Verifying current authentication status
      - Retrieving user permissions (role)
    security:
      - Bearer: []
    responses:
      200:
        description: User information retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User information retrieved successfully
            data:
              type: object
              properties:
                user:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 1
                    username:
                      type: string
                      example: johndoe
                    email:
                      type: string
                      example: john@example.com
                    role:
                      type: string
                      enum: [admin, analyst, viewer]
                      example: analyst
                    is_active:
                      type: boolean
                      example: true
                    created_at:
                      type: string
                      format: date-time
                      example: "2024-01-15T10:30:00Z"
                    last_login:
                      type: string
                      format: date-time
                      example: "2024-12-01T14:20:00Z"
      401:
        description: Unauthorized (missing or invalid token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Missing or invalid token
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Failed to retrieve user information
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


@auth_bp.route('/password/reset-request', methods=['POST'])
@limiter.limit("3/hour")
@require_turnstile_json()  # Bot protection
def request_password_reset():
    """
    Request password reset email with secure token.
    ---
    tags:
      - Authentication
    summary: Request password reset
    description: |
      Initiates a password reset process by sending a secure reset link to the user's email address.

      **Security Features:**
      - Always returns success response to prevent user enumeration attacks
      - Reset token expires after 1 hour
      - Rate limited to 3 requests per hour per IP address
      - Requires bot protection via Cloudflare Turnstile (if enabled)
      - Token is single-use and invalidated after successful password reset

      **Note:** Even if the email doesn't exist in the system, a success response is returned
      to prevent attackers from discovering valid email addresses.
    parameters:
      - in: body
        name: body
        required: true
        description: User email address
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              description: Registered email address
              example: "user@example.com"
    responses:
      200:
        description: Password reset email sent (or email not found - security response)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: If the email exists, a password reset link has been sent
            data:
              type: object
              properties:
                message:
                  type: string
                  example: If the email exists, a password reset link has been sent
                expires_in:
                  type: integer
                  description: Token expiration time in seconds
                  example: 3600
      400:
        description: Validation error (invalid email format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Validation error
            details:
              type: object
      429:
        description: Rate limit exceeded (too many reset requests)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Rate limit exceeded. Please try again later.
      500:
        description: Server error (email service unavailable)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Failed to send password reset email
    """
    try:
        # Validate request data
        data = PasswordResetRequestSchema(**request.json)

        # Find user by email
        from app.models import User
        user = User.query.filter_by(email=data.email).first()

        # Security: Always return success to prevent user enumeration
        # Even if user doesn't exist, attacker cannot determine valid emails
        if not user:
            current_app.logger.warning(
                f"Password reset requested for non-existent email: {data.email}"
            )
            return success_response(
                data=PasswordResetResponseSchema(
                    message="If the email exists, a password reset link has been sent",
                    email_sent=True
                ).model_dump(),
                status_code=200
            )

        # Generate password reset token (JWT with 1-hour expiry)
        reset_token = create_access_token(
            identity=user.email,
            additional_claims={"type": "password_reset", "user_id": user.id},
            expires_delta=timedelta(hours=1)
        )

        # Send reset email
        email_service = EmailService()
        email_sent = email_service.send_password_reset_email(
            recipient_email=user.email,
            reset_token=reset_token,
            expiry_minutes=60
        )

        if not email_sent:
            current_app.logger.error(
                f"Failed to send password reset email to {user.email}"
            )
            return error_response(
                message="Failed to send password reset email. Please try again later.",
                status_code=500
            )

        current_app.logger.info(
            f"Password reset requested successfully for user: {user.email}"
        )

        return success_response(
            data=PasswordResetResponseSchema(
                message="Password reset email sent successfully. Check your inbox.",
                email_sent=True
            ).model_dump(),
            status_code=200
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            errors=e.errors(),
            status_code=400
        )
    except Exception as e:
        current_app.logger.error(f"Password reset request error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@auth_bp.route('/password/reset-confirm', methods=['POST'])
def confirm_password_reset():
    """
    Complete password reset using token from email.
    ---
    tags:
      - Authentication
    summary: Confirm password reset
    description: |
      Completes the password reset process by validating the reset token received via email
      and setting a new password for the user.

      **Security Features:**
      - Validates token signature and expiration (1-hour lifetime)
      - Enforces strong password requirements
      - Token is single-use (expires immediately after use)
      - All password resets are logged for security auditing
      - Verifies token type to prevent token confusion attacks

      **Password Requirements:**
      - Minimum 8 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
    parameters:
      - in: body
        name: body
        required: true
        description: Reset token and new password
        schema:
          type: object
          required:
            - token
            - new_password
          properties:
            token:
              type: string
              description: Password reset token received via email
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwidHlwZSI6InBhc3N3b3JkX3Jlc2V0IiwiZXhwIjoxNzMzMDk4ODAwfQ.signature"
            new_password:
              type: string
              format: password
              description: New password (must meet security requirements)
              example: "NewSecureP@ss123!"
    responses:
      200:
        description: Password reset successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Password has been reset successfully
            data:
              type: object
              properties:
                message:
                  type: string
                  example: You can now log in with your new password
      400:
        description: Validation error (weak password or invalid request format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Validation error
            details:
              type: object
              properties:
                validation_errors:
                  type: array
                  items:
                    type: object
      401:
        description: Token expired, invalid, or wrong token type
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Invalid or expired password reset token
      404:
        description: User not found (email from token doesn't exist)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: User not found
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Password reset failed
    """
    try:
        # Validate request data
        data = PasswordResetConfirmSchema(**request.json)

        # Decode and validate reset token
        try:
            token_data = decode_token(data.token)
        except Exception as token_error:
            current_app.logger.warning(
                f"Invalid password reset token received: {str(token_error)}"
            )
            return error_response(
                message="Invalid or expired password reset token",
                status_code=401
            )

        # Verify token type
        if token_data.get("type") != "password_reset":
            current_app.logger.warning(
                "Wrong token type used for password reset"
            )
            return error_response(
                message="Invalid token type. Please request a new password reset.",
                status_code=401
            )

        # Extract user information from token
        user_email = token_data.get("sub")
        user_id = token_data.get("user_id")

        if not user_email or not user_id:
            current_app.logger.error(
                "Password reset token missing required claims"
            )
            return error_response(
                message="Malformed password reset token",
                status_code=401
            )

        # Find user
        from app.models import User
        from app.extensions import db

        user = User.query.filter_by(id=user_id, email=user_email).first()

        if not user:
            current_app.logger.error(
                f"User not found for password reset: user_id={user_id}, email={user_email}"
            )
            return error_response(
                message="User not found",
                status_code=404
            )

        # Update password
        user.set_password(data.new_password)
        db.session.commit()

        # Audit log password reset
        AuditService.log_password_reset(
            user_id=user.id,
            username=user.username,
            status_code=200
        )

        current_app.logger.info(
            f"Password reset completed successfully for user: {user.email}"
        )

        return success_response(
            data={
                "message": "Password reset successful. You can now log in with your new password.",
                "email": user.email
            },
            status_code=200
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            errors=e.errors(),
            status_code=400
        )
    except Exception as e:
        current_app.logger.error(f"Password reset confirmation error: {str(e)}")
        # Rollback any database changes
        from app.extensions import db
        db.session.rollback()
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )
