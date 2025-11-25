"""
User management routes for CRUD operations and admin functions.

Endpoints:
- GET /api/v1/users - List all users (admin, analyst)
- GET /api/v1/users/{id} - Get user by ID
- PUT /api/v1/users/{id} - Update user
- DELETE /api/v1/users/{id} - Deactivate user (admin only)
- POST /api/v1/users/{id}/activate - Activate user (admin only)
- GET /api/v1/users/stats - Get user statistics (admin, analyst)
"""

from flask import Blueprint, request, current_app
from pydantic import ValidationError as PydanticValidationError
from app.services.user_service import UserService
from app.schemas.user_schemas import UserUpdateRequest, UserResponse
from app.middleware.auth_middleware import (
    jwt_required_custom,
    get_current_user_id,
    get_current_user_role
)
from app.middleware.rbac_middleware import (
    require_role,
    require_analyst_or_admin,
    require_admin
)
from app.core.responses import success_response, error_response
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError
from app.exceptions.validation import ValidationError
from app.exceptions.base import ResourceNotFoundError


# Create blueprint
user_bp = Blueprint('users', __name__)

# Initialize service
user_service = UserService()


@user_bp.route('', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
def list_users():
    """
    List all users with pagination and filtering.

    Query Parameters:
        - skip: Number of records to skip (default: 0)
        - limit: Maximum records to return (default: 100, max: 1000)
        - role: Filter by role (admin, analyst, viewer)
        - is_active: Filter by active status (true/false)
        - search: Search in username/email

    Returns:
        200: List of users with pagination metadata

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/users?skip=0&limit=50&role=admin" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        role_filter = request.args.get('role', None)
        is_active_filter = request.args.get('is_active', None)
        search_query = request.args.get('search', None)

        # Validate limit
        if limit > 1000:
            limit = 1000

        # Parse is_active filter
        if is_active_filter is not None:
            is_active_filter = is_active_filter.lower() == 'true'

        # Get current user role
        current_role = get_current_user_role()

        # Get users
        result = user_service.list_users(
            current_user_role=current_role,
            skip=skip,
            limit=limit,
            role_filter=role_filter,
            is_active_filter=is_active_filter,
            search_query=search_query
        )

        return success_response(
            data=result,
            message="Users retrieved successfully"
        )

    except InsufficientPermissionsError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except Exception as e:
        current_app.logger.error(f"List users error: {str(e)}")
        return error_response(
            message="Failed to retrieve users",
            status_code=500
        )


@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required_custom()
def get_user(user_id: int):
    """
    Get user by ID.

    Users can view their own profile.
    Admins and analysts can view any user.

    Path Parameters:
        user_id: User ID

    Returns:
        200: User profile data
        403: Insufficient permissions
        404: User not found

    Example:
        $ curl -X GET http://localhost:5000/api/v1/users/1 \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        current_user_id = get_current_user_id()
        current_role = get_current_user_role()

        # Authorization: users can view themselves, admins/analysts can view anyone
        if current_user_id != user_id and current_role not in ['admin', 'analyst']:
            raise InsufficientPermissionsError(
                "You can only view your own profile"
            )

        # Get user profile
        user_data = user_service.get_user_profile(user_id)

        return success_response(
            data={'user': user_data},
            message="User retrieved successfully"
        )

    except InsufficientPermissionsError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except ResourceNotFoundError as e:
        return error_response(
            message=str(e),
            status_code=404
        )
    except Exception as e:
        current_app.logger.error(f"Get user error: {str(e)}")
        return error_response(
            message="Failed to retrieve user",
            status_code=500
        )


@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required_custom()
def update_user(user_id: int):
    """
    Update user profile.

    Users can update their own profile (username, email).
    Admins can update any user (including role and is_active).

    Path Parameters:
        user_id: User ID

    Request Body:
        {
            "username": "newusername",  // optional
            "email": "newemail@example.com",  // optional
            "role": "admin",  // optional, admin only
            "is_active": true  // optional, admin only
        }

    Returns:
        200: Updated user data
        400: Validation error
        403: Insufficient permissions
        404: User not found

    Example:
        $ curl -X PUT http://localhost:5000/api/v1/users/1 \\
          -H "Authorization: Bearer <access_token>" \\
          -H "Content-Type: application/json" \\
          -d '{"username":"newname"}'
    """
    try:
        # Parse request data
        data = request.get_json() or {}

        # Get current user info
        current_user_id = get_current_user_id()
        current_role = get_current_user_role()

        # Update user
        updated_user = user_service.update_user_profile(
            user_id=user_id,
            current_user_id=current_user_id,
            current_user_role=current_role,
            **data
        )

        return success_response(
            data={'user': updated_user},
            message="User updated successfully"
        )

    except PydanticValidationError as e:
        return error_response(
            message="Validation error",
            details={"validation_errors": e.errors()},
            status_code=400
        )
    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except AuthorizationError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except ResourceNotFoundError as e:
        return error_response(
            message=str(e),
            status_code=404
        )
    except Exception as e:
        current_app.logger.error(f"Update user error: {str(e)}")
        return error_response(
            message="Failed to update user",
            status_code=500
        )


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required_custom()
@require_admin()
def deactivate_user(user_id: int):
    """
    Deactivate user account (soft delete).

    Only admins can deactivate users.
    Users cannot deactivate themselves.

    Path Parameters:
        user_id: User ID

    Returns:
        200: User deactivated successfully
        400: Validation error
        403: Insufficient permissions
        404: User not found

    Example:
        $ curl -X DELETE http://localhost:5000/api/v1/users/5 \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        current_user_id = get_current_user_id()
        current_role = get_current_user_role()

        # Deactivate user
        result = user_service.deactivate_user(
            user_id=user_id,
            current_user_id=current_user_id,
            current_user_role=current_role
        )

        return success_response(
            data=result,
            message="User deactivated successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except InsufficientPermissionsError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except ResourceNotFoundError as e:
        return error_response(
            message=str(e),
            status_code=404
        )
    except Exception as e:
        current_app.logger.error(f"Deactivate user error: {str(e)}")
        return error_response(
            message="Failed to deactivate user",
            status_code=500
        )


@user_bp.route('/<int:user_id>/activate', methods=['POST'])
@jwt_required_custom()
@require_admin()
def activate_user(user_id: int):
    """
    Activate a deactivated user account.

    Only admins can activate users.

    Path Parameters:
        user_id: User ID

    Returns:
        200: User activated successfully
        403: Insufficient permissions
        404: User not found

    Example:
        $ curl -X POST http://localhost:5000/api/v1/users/5/activate \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        current_role = get_current_user_role()

        # Activate user
        result = user_service.activate_user(
            user_id=user_id,
            current_user_role=current_role
        )

        return success_response(
            data=result,
            message="User activated successfully"
        )

    except InsufficientPermissionsError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except ResourceNotFoundError as e:
        return error_response(
            message=str(e),
            status_code=404
        )
    except Exception as e:
        current_app.logger.error(f"Activate user error: {str(e)}")
        return error_response(
            message="Failed to activate user",
            status_code=500
        )


@user_bp.route('/stats', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
def get_user_statistics():
    """
    Get user statistics.

    Only admins and analysts can view statistics.

    Returns:
        200: User statistics
        403: Insufficient permissions

    Example:
        $ curl -X GET http://localhost:5000/api/v1/users/stats \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        current_role = get_current_user_role()

        # Get statistics
        stats = user_service.get_user_statistics(current_role)

        return success_response(
            data=stats,
            message="Statistics retrieved successfully"
        )

    except InsufficientPermissionsError as e:
        return error_response(
            message=str(e),
            status_code=403
        )
    except Exception as e:
        current_app.logger.error(f"Get statistics error: {str(e)}")
        return error_response(
            message="Failed to retrieve statistics",
            status_code=500
        )
