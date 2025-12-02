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
    List all users with advanced filtering and pagination.
    ---
    tags:
      - Users
    summary: List users
    description: |
      Retrieve a paginated list of users with support for filtering, searching, sorting, and field selection.
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
        description: Page number (starts at 1)
        example: 1
      - in: query
        name: per_page
        type: integer
        default: 20
        description: Items per page (max 100)
        example: 20
      - in: query
        name: role
        type: string
        enum: [admin, analyst, viewer]
        description: Filter by user role
        example: analyst
      - in: query
        name: is_active
        type: boolean
        description: Filter by active status
        example: true
      - in: query
        name: search
        type: string
        description: Search in username and email fields
        example: john
      - in: query
        name: sort
        type: string
        description: Sort fields (prefix with - for descending). Multiple fields separated by comma.
        example: "-created_at,username"
      - in: query
        name: fields
        type: string
        description: Specific fields to include (comma-separated)
        example: "id,username,email,role"
      - in: query
        name: created_at__gte
        type: string
        format: date-time
        description: Filter users created after this date
        example: "2024-01-01T00:00:00Z"
      - in: query
        name: created_at__lte
        type: string
        format: date-time
        description: Filter users created before this date
        example: "2024-12-31T23:59:59Z"
    responses:
      200:
        description: Users retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Users retrieved successfully
            data:
              type: object
              properties:
                users:
                  type: array
                  items:
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
            pagination:
              type: object
              properties:
                page:
                  type: integer
                  example: 1
                per_page:
                  type: integer
                  example: 20
                total_items:
                  type: integer
                  example: 150
                total_pages:
                  type: integer
                  example: 8
                has_next:
                  type: boolean
                  example: true
                has_prev:
                  type: boolean
                  example: false
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Missing or invalid token
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Insufficient permissions
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
              example: An unexpected error occurred
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
    Get user profile by ID.
    ---
    tags:
      - Users
    summary: Get user by ID
    description: |
      Retrieves detailed information about a specific user by their ID.

      **Authorization Rules:**
      - Any authenticated user can view their own profile
      - Admin and analyst roles can view any user's profile
      - Viewer role can only view their own profile

      Returns complete user information including account status, role, and activity timestamps.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: Unique user identifier
        example: 1
    responses:
      200:
        description: User retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User retrieved successfully
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
      403:
        description: Forbidden (insufficient permissions to view this user)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: You can only view your own profile
      404:
        description: User not found
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
              example: Failed to retrieve user
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
    Update user profile with role-based permissions.
    ---
    tags:
      - Users
    summary: Update user
    description: |
      Updates user profile information with different permissions based on role.

      **Authorization Rules:**
      - **Regular users** can update their own username and email only
      - **Admins** can update any user including role and is_active status
      - **Analysts** cannot modify other users

      **Updatable Fields:**
      - username (all authenticated users for own profile)
      - email (all authenticated users for own profile)
      - role (admin only)
      - is_active (admin only)

      All fields are optional. Only provided fields will be updated.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to update
        example: 1
      - in: body
        name: body
        required: true
        description: User update data (all fields optional)
        schema:
          type: object
          properties:
            username:
              type: string
              minLength: 3
              maxLength: 50
              description: New username (unique)
              example: johndoe_updated
            email:
              type: string
              format: email
              description: New email address (unique)
              example: john.updated@example.com
            role:
              type: string
              enum: [admin, analyst, viewer]
              description: New role (admin only)
              example: analyst
            is_active:
              type: boolean
              description: Account active status (admin only)
              example: true
    responses:
      200:
        description: User updated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User updated successfully
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
                      example: johndoe_updated
                    email:
                      type: string
                      example: john.updated@example.com
                    role:
                      type: string
                      example: analyst
                    is_active:
                      type: boolean
                      example: true
                    created_at:
                      type: string
                      format: date-time
                    last_login:
                      type: string
                      format: date-time
      400:
        description: Validation error (invalid data, duplicate username/email)
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
      403:
        description: Forbidden (insufficient permissions to update this user or field)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Insufficient permissions to update this field
      404:
        description: User not found
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
              example: Failed to update user
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
    Deactivate user account (soft delete) - Admin only.
    ---
    tags:
      - Users
    summary: Deactivate user
    description: |
      Soft-deletes a user account by setting is_active to false. This is a reversible operation
      that preserves all user data while preventing authentication.

      **Security Features:**
      - Admin role required
      - Users cannot deactivate themselves (safety measure)
      - All user data is preserved (no hard delete)
      - Can be reversed with POST /users/{id}/activate
      - Action is logged for audit trail

      **Effects of Deactivation:**
      - User cannot log in
      - Existing tokens are not immediately invalidated
      - User data remains in database
      - Can be reactivated by admins

      **Use Cases:**
      - Employee offboarding
      - Account suspension
      - Security incidents
      - Temporary access removal
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to deactivate
        example: 5
    responses:
      200:
        description: User deactivated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User deactivated successfully
            data:
              type: object
              properties:
                user_id:
                  type: integer
                  example: 5
                is_active:
                  type: boolean
                  example: false
                deactivated_at:
                  type: string
                  format: date-time
                  example: "2024-12-01T15:30:00Z"
      400:
        description: Validation error (e.g., trying to deactivate yourself)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: You cannot deactivate your own account
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
      403:
        description: Forbidden (non-admin user)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Admin role required
      404:
        description: User not found
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
              example: Failed to deactivate user
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
    Reactivate a deactivated user account - Admin only.
    ---
    tags:
      - Users
    summary: Activate user
    description: |
      Reactivates a previously deactivated user account by setting is_active to true.
      This reverses the soft delete operation and restores full access.

      **Security Features:**
      - Admin role required
      - Action is logged for audit trail
      - User can immediately log in after activation
      - All previous user data is preserved

      **Effects of Activation:**
      - User can log in again
      - All permissions restored
      - Access to protected resources enabled
      - User appears in active user lists

      **Use Cases:**
      - Employee rehiring
      - Account restoration after suspension
      - Reversing accidental deactivation
      - Reinstating user access
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
        description: User ID to activate
        example: 5
    responses:
      200:
        description: User activated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: User activated successfully
            data:
              type: object
              properties:
                user_id:
                  type: integer
                  example: 5
                is_active:
                  type: boolean
                  example: true
                activated_at:
                  type: string
                  format: date-time
                  example: "2024-12-01T16:00:00Z"
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
      403:
        description: Forbidden (non-admin user)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Admin role required
      404:
        description: User not found
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
              example: Failed to activate user
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
