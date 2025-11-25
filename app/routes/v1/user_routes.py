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
from sqlalchemy import select

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
from app.core.pagination import PaginationParams, paginate_query
from app.core.filtering import FilterParams, apply_filters, apply_search
from app.core.sorting import SortParams, apply_sorting, SortField, SortOrder
from app.core.field_selector import FieldSelector, select_fields
from app.exceptions.auth import InsufficientPermissionsError, AuthorizationError
from app.exceptions.validation import ValidationError
from app.exceptions.base import ResourceNotFoundError
from app.models import User
from app.extensions import db


# Create blueprint
user_bp = Blueprint('users', __name__)

# Initialize service
user_service = UserService()


@user_bp.route('', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
def list_users():
    """
    List all users with pagination, filtering, sorting, and field selection.

    Query Parameters:
        Pagination:
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)

        Filtering:
            - role: Filter by role (admin, analyst, viewer)
            - is_active: Filter by active status (true/false)
            - created_at__gte: Filter by creation date (greater than or equal)
            - created_at__lte: Filter by creation date (less than or equal)

        Search:
            - search: Search in username and email fields

        Sorting:
            - sort: Sort fields (e.g., "created_at", "-username")
                   Prefix with - for descending order
                   Multiple fields: "role,-created_at"

        Field Selection:
            - fields: Specific fields to include (e.g., "id,username,email")
            - exclude: Fields to exclude (e.g., "password_hash")

    Returns:
        200: List of users with pagination metadata

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/users?page=1&per_page=20&role=admin&sort=-created_at&fields=id,username,email" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Parse pagination parameters
        pagination = PaginationParams.from_request(request, default_per_page=20, max_per_page=100)

        # Parse filter parameters
        allowed_filter_fields = {'role', 'is_active', 'created_at'}
        filters = FilterParams.from_request(request, allowed_fields=allowed_filter_fields)

        # Parse sort parameters
        allowed_sort_fields = {'id', 'username', 'email', 'role', 'created_at', 'last_login'}
        default_sort = [SortField('created_at', SortOrder.DESC)]
        sort_params = SortParams.from_request(
            request,
            allowed_fields=allowed_sort_fields,
            default_sort=default_sort
        )

        # Parse field selection
        allowed_fields = {'id', 'username', 'email', 'role', 'is_active', 'created_at', 'last_login'}
        always_exclude = {'password_hash'}
        field_selector = FieldSelector.from_request(
            request,
            allowed_fields=allowed_fields,
            always_exclude=always_exclude
        )

        # Build base query
        query = select(User)

        # Apply filters
        query = apply_filters(query, User, filters)

        # Apply search if provided
        if filters.search:
            search_fields = ['username', 'email']
            query = apply_search(query, User, filters.search, search_fields)

        # Apply sorting
        query = apply_sorting(query, User, sort_params)

        # Paginate query
        users, meta = paginate_query(query, pagination)

        # Serialize users to dict
        users_data = []
        for user in users:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
            # Apply field selection
            filtered_user = select_fields(user_dict, field_selector)
            users_data.append(filtered_user)

        return success_response(
            data={'users': users_data},
            message="Users retrieved successfully",
            pagination=meta.to_dict()
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
