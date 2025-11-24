"""Standardized API response wrappers for consistent HTTP responses.

This module provides utilities for creating consistent, well-structured API responses:
- Uniform response format across all endpoints
- Automatic status code handling
- Metadata injection (timestamp, request_id, pagination)
- Type-safe response builders
- Support for success, error, and paginated responses

All responses follow this structure:
{
    "success": true/false,
    "data": {...} or null,
    "error": {...} or null,
    "meta": {
        "timestamp": "2025-11-24T10:30:00.000Z",
        "request_id": "uuid-here",
        "pagination": {...} (optional)
    }
}

Usage:
    from app.core.responses import success_response, error_response

    @app.route("/api/users")
    def get_users():
        users = User.query.all()
        return success_response(
            data=[user.to_dict() for user in users],
            message="Users retrieved successfully"
        )

    @app.route("/api/users/<int:user_id>")
    def get_user(user_id):
        user = User.query.get(user_id)
        if not user:
            return not_found_response(f"User {user_id} not found")
        return success_response(data=user.to_dict())
"""

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

from flask import g, has_request_context, jsonify
from flask.wrappers import Response


def _get_request_id() -> Optional[str]:
    """Get request ID from Flask request context.

    Returns:
        Request ID string if available, None otherwise
    """
    if has_request_context():
        return getattr(g, "request_id", None)
    return None


def _build_meta(
    pagination: Optional[Dict[str, Any]] = None,
    additional_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build response metadata object.

    Args:
        pagination: Pagination information (page, per_page, total, pages)
        additional_meta: Additional metadata to include

    Returns:
        Metadata dictionary with timestamp and request_id
    """
    meta: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": _get_request_id(),
    }

    if pagination:
        meta["pagination"] = pagination

    if additional_meta:
        meta.update(additional_meta)

    return meta


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = HTTPStatus.OK,
    pagination: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a successful API response.

    Args:
        data: Response payload (dict, list, or any JSON-serializable type)
        message: Optional success message
        status_code: HTTP status code (default: 200 OK)
        pagination: Pagination metadata (page, per_page, total, pages)
        meta: Additional metadata to include

    Returns:
        Tuple of (Flask Response object, status code)

    Example:
        >>> success_response({"user_id": 123}, message="User created", status_code=201)
        (<Response 123 bytes [201 CREATED]>, 201)
    """
    response_body = {
        "success": True,
        "data": data,
        "error": None,
        "meta": _build_meta(pagination=pagination, additional_meta=meta),
    }

    if message:
        response_body["message"] = message

    return jsonify(response_body), status_code


def error_response(
    message: str,
    status_code: int = HTTPStatus.BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create an error API response.

    Args:
        message: Human-readable error message
        status_code: HTTP status code (default: 400 Bad Request)
        error_code: Machine-readable error code (e.g., "VALIDATION_ERROR")
        details: Additional error details (field errors, validation failures)
        meta: Additional metadata to include

    Returns:
        Tuple of (Flask Response object, status code)

    Example:
        >>> error_response(
        ...     "Invalid email format",
        ...     status_code=422,
        ...     error_code="VALIDATION_ERROR",
        ...     details={"field": "email"}
        ... )
        (<Response 456 bytes [422 UNPROCESSABLE ENTITY]>, 422)
    """
    error_obj: Dict[str, Any] = {
        "message": message,
        "code": error_code or f"ERROR_{status_code}",
    }

    if details:
        error_obj["details"] = details

    response_body = {
        "success": False,
        "data": None,
        "error": error_obj,
        "meta": _build_meta(additional_meta=meta),
    }

    return jsonify(response_body), status_code


def paginated_response(
    items: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a paginated success response.

    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        per_page: Items per page
        total: Total number of items across all pages
        message: Optional success message
        meta: Additional metadata to include

    Returns:
        Tuple of (Flask Response object, status code)

    Example:
        >>> users = User.query.paginate(page=2, per_page=10)
        >>> paginated_response(
        ...     items=[u.to_dict() for u in users.items],
        ...     page=users.page,
        ...     per_page=users.per_page,
        ...     total=users.total,
        ...     message="Users retrieved successfully"
        ... )
        (<Response 789 bytes [200 OK]>, 200)
    """
    total_pages = (total + per_page - 1) // per_page  # Ceiling division

    pagination = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }

    return success_response(
        data=items,
        message=message,
        pagination=pagination,
        meta=meta,
    )


# =============================================================================
# Convenience Response Builders for Common HTTP Status Codes
# =============================================================================


def created_response(
    data: Any,
    message: str = "Resource created successfully",
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a 201 Created response.

    Args:
        data: Created resource data
        message: Success message (default: "Resource created successfully")
        meta: Additional metadata

    Returns:
        Tuple of (Flask Response object, 201)

    Example:
        >>> created_response({"user_id": 123, "email": "user@example.com"})
        (<Response 123 bytes [201 CREATED]>, 201)
    """
    return success_response(
        data=data,
        message=message,
        status_code=HTTPStatus.CREATED,
        meta=meta,
    )


def no_content_response() -> Tuple[Response, int]:
    """Create a 204 No Content response.

    Used for successful operations that don't return data (e.g., DELETE).

    Returns:
        Tuple of (Flask Response object, 204)

    Example:
        >>> @app.route("/api/users/<int:user_id>", methods=["DELETE"])
        ... def delete_user(user_id):
        ...     user = User.query.get(user_id)
        ...     db.session.delete(user)
        ...     db.session.commit()
        ...     return no_content_response()
    """
    return jsonify({}), HTTPStatus.NO_CONTENT


def bad_request_response(
    message: str = "Bad request",
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a 400 Bad Request response.

    Args:
        message: Error message (default: "Bad request")
        details: Additional error details

    Returns:
        Tuple of (Flask Response object, 400)

    Example:
        >>> bad_request_response("Missing required field: email")
        (<Response 456 bytes [400 BAD REQUEST]>, 400)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.BAD_REQUEST,
        error_code="BAD_REQUEST",
        details=details,
    )


def unauthorized_response(
    message: str = "Authentication required",
) -> Tuple[Response, int]:
    """Create a 401 Unauthorized response.

    Args:
        message: Error message (default: "Authentication required")

    Returns:
        Tuple of (Flask Response object, 401)

    Example:
        >>> unauthorized_response("Invalid credentials")
        (<Response 456 bytes [401 UNAUTHORIZED]>, 401)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.UNAUTHORIZED,
        error_code="UNAUTHORIZED",
    )


def forbidden_response(
    message: str = "Access denied",
) -> Tuple[Response, int]:
    """Create a 403 Forbidden response.

    Args:
        message: Error message (default: "Access denied")

    Returns:
        Tuple of (Flask Response object, 403)

    Example:
        >>> forbidden_response("Admin access required")
        (<Response 456 bytes [403 FORBIDDEN]>, 403)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.FORBIDDEN,
        error_code="FORBIDDEN",
    )


def not_found_response(
    message: str = "Resource not found",
) -> Tuple[Response, int]:
    """Create a 404 Not Found response.

    Args:
        message: Error message (default: "Resource not found")

    Returns:
        Tuple of (Flask Response object, 404)

    Example:
        >>> not_found_response("User with ID 123 not found")
        (<Response 456 bytes [404 NOT FOUND]>, 404)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.NOT_FOUND,
        error_code="NOT_FOUND",
    )


def conflict_response(
    message: str = "Resource conflict",
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a 409 Conflict response.

    Args:
        message: Error message (default: "Resource conflict")
        details: Additional error details

    Returns:
        Tuple of (Flask Response object, 409)

    Example:
        >>> conflict_response("Email already exists", details={"field": "email"})
        (<Response 456 bytes [409 CONFLICT]>, 409)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.CONFLICT,
        error_code="CONFLICT",
        details=details,
    )


def validation_error_response(
    message: str = "Validation failed",
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[Response, int]:
    """Create a 422 Unprocessable Entity response for validation errors.

    Args:
        message: Error message (default: "Validation failed")
        details: Field-level validation errors

    Returns:
        Tuple of (Flask Response object, 422)

    Example:
        >>> validation_error_response(
        ...     "Invalid input data",
        ...     details={
        ...         "email": ["Invalid email format"],
        ...         "password": ["Password too short"]
        ...     }
        ... )
        (<Response 456 bytes [422 UNPROCESSABLE ENTITY]>, 422)
    """
    return error_response(
        message=message,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        details=details,
    )


def internal_error_response(
    message: str = "Internal server error",
    error_id: Optional[str] = None,
) -> Tuple[Response, int]:
    """Create a 500 Internal Server Error response.

    Args:
        message: Error message (default: "Internal server error")
        error_id: Unique error identifier for tracking

    Returns:
        Tuple of (Flask Response object, 500)

    Example:
        >>> internal_error_response(
        ...     "Database connection failed",
        ...     error_id="ERR_DB_12345"
        ... )
        (<Response 456 bytes [500 INTERNAL SERVER ERROR]>, 500)
    """
    details = {"error_id": error_id} if error_id else None

    return error_response(
        message=message,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        details=details,
    )
