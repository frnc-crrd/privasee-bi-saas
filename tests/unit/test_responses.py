"""Unit tests for app.core.responses module.

Tests standardized API response wrappers and builders.
"""

import json
from http import HTTPStatus

from app.core.context import set_request_id
from app.core.responses import (
    bad_request_response,
    conflict_response,
    created_response,
    error_response,
    forbidden_response,
    internal_error_response,
    no_content_response,
    not_found_response,
    paginated_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)


class TestSuccessResponse:
    """Test success_response function."""

    def test_success_response_basic(self, app):
        """Test basic success response structure."""
        with app.test_request_context():
            response, status_code = success_response(data={"key": "value"})

            data = json.loads(response.get_data(as_text=True))

            assert status_code == HTTPStatus.OK
            assert data["success"] is True
            assert data["data"] == {"key": "value"}
            assert data["error"] is None
            assert "meta" in data
            assert "timestamp" in data["meta"]

    def test_success_response_with_message(self, app):
        """Test success response with custom message."""
        with app.test_request_context():
            response, status_code = success_response(
                data={"id": 123}, message="User created successfully"
            )

            data = json.loads(response.get_data(as_text=True))

            assert data["message"] == "User created successfully"

    def test_success_response_with_custom_status_code(self, app):
        """Test success response with custom status code."""
        with app.test_request_context():
            response, status_code = success_response(
                data={"id": 456}, status_code=HTTPStatus.CREATED
            )

            assert status_code == HTTPStatus.CREATED

    def test_success_response_with_pagination(self, app):
        """Test success response with pagination metadata."""
        with app.test_request_context():
            pagination = {"page": 1, "per_page": 10, "total": 100, "pages": 10}
            response, status_code = success_response(data=[], pagination=pagination)

            data = json.loads(response.get_data(as_text=True))

            assert data["meta"]["pagination"] == pagination

    def test_success_response_includes_request_id(self, app):
        """Test that success response includes request_id in meta."""
        with app.test_request_context():
            set_request_id("test-request-123")

            response, status_code = success_response(data={})

            data = json.loads(response.get_data(as_text=True))

            assert data["meta"]["request_id"] == "test-request-123"

    def test_success_response_with_additional_meta(self, app):
        """Test success response with additional metadata."""
        with app.test_request_context():
            response, status_code = success_response(data={}, meta={"custom_field": "custom_value"})

            data = json.loads(response.get_data(as_text=True))

            assert data["meta"]["custom_field"] == "custom_value"

    def test_success_response_null_data(self, app):
        """Test success response with null data."""
        with app.test_request_context():
            response, status_code = success_response(data=None)

            data = json.loads(response.get_data(as_text=True))

            assert data["data"] is None
            assert data["success"] is True


class TestErrorResponse:
    """Test error_response function."""

    def test_error_response_basic(self, app):
        """Test basic error response structure."""
        with app.test_request_context():
            response, status_code = error_response(message="Something went wrong")

            data = json.loads(response.get_data(as_text=True))

            assert status_code == HTTPStatus.BAD_REQUEST
            assert data["success"] is False
            assert data["data"] is None
            assert data["error"]["message"] == "Something went wrong"
            assert "code" in data["error"]

    def test_error_response_with_custom_code(self, app):
        """Test error response with custom error code."""
        with app.test_request_context():
            response, status_code = error_response(
                message="Validation failed", error_code="VALIDATION_ERROR"
            )

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_error_response_with_details(self, app):
        """Test error response with error details."""
        with app.test_request_context():
            details = {"field": "email", "reason": "Invalid format"}
            response, status_code = error_response(message="Validation failed", details=details)

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["details"] == details

    def test_error_response_custom_status_code(self, app):
        """Test error response with custom status code."""
        with app.test_request_context():
            response, status_code = error_response(
                message="Not found", status_code=HTTPStatus.NOT_FOUND
            )

            assert status_code == HTTPStatus.NOT_FOUND

    def test_error_response_default_error_code(self, app):
        """Test that default error code is generated from status code."""
        with app.test_request_context():
            response, status_code = error_response(message="Error", status_code=404)

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["code"] == "ERROR_404"


class TestPaginatedResponse:
    """Test paginated_response function."""

    def test_paginated_response_basic(self, app):
        """Test basic paginated response."""
        with app.test_request_context():
            items = [{"id": 1}, {"id": 2}, {"id": 3}]
            response, status_code = paginated_response(items=items, page=1, per_page=10, total=30)

            data = json.loads(response.get_data(as_text=True))

            assert status_code == HTTPStatus.OK
            assert data["success"] is True
            assert data["data"] == items
            assert "pagination" in data["meta"]

    def test_paginated_response_pagination_metadata(self, app):
        """Test pagination metadata calculation."""
        with app.test_request_context():
            response, status_code = paginated_response(items=[], page=2, per_page=10, total=25)

            data = json.loads(response.get_data(as_text=True))
            pagination = data["meta"]["pagination"]

            assert pagination["page"] == 2
            assert pagination["per_page"] == 10
            assert pagination["total"] == 25
            assert pagination["pages"] == 3  # Ceiling of 25/10
            assert pagination["has_next"] is True  # Page 2 of 3
            assert pagination["has_prev"] is True  # Page 2 of 3

    def test_paginated_response_first_page(self, app):
        """Test pagination metadata for first page."""
        with app.test_request_context():
            response, status_code = paginated_response(items=[], page=1, per_page=10, total=50)

            data = json.loads(response.get_data(as_text=True))
            pagination = data["meta"]["pagination"]

            assert pagination["has_next"] is True
            assert pagination["has_prev"] is False

    def test_paginated_response_last_page(self, app):
        """Test pagination metadata for last page."""
        with app.test_request_context():
            response, status_code = paginated_response(items=[], page=5, per_page=10, total=50)

            data = json.loads(response.get_data(as_text=True))
            pagination = data["meta"]["pagination"]

            assert pagination["has_next"] is False
            assert pagination["has_prev"] is True

    def test_paginated_response_single_page(self, app):
        """Test pagination metadata when all items fit in one page."""
        with app.test_request_context():
            response, status_code = paginated_response(items=[], page=1, per_page=100, total=50)

            data = json.loads(response.get_data(as_text=True))
            pagination = data["meta"]["pagination"]

            assert pagination["pages"] == 1
            assert pagination["has_next"] is False
            assert pagination["has_prev"] is False

    def test_paginated_response_with_message(self, app):
        """Test paginated response with custom message."""
        with app.test_request_context():
            response, status_code = paginated_response(
                items=[], page=1, per_page=10, total=0, message="No results found"
            )

            data = json.loads(response.get_data(as_text=True))

            assert data["message"] == "No results found"


class TestCreatedResponse:
    """Test created_response convenience function."""

    def test_created_response_status_code(self, app):
        """Test that created response returns 201 status."""
        with app.test_request_context():
            response, status_code = created_response(data={"id": 123})

            assert status_code == HTTPStatus.CREATED

    def test_created_response_default_message(self, app):
        """Test created response default message."""
        with app.test_request_context():
            response, status_code = created_response(data={})

            data = json.loads(response.get_data(as_text=True))

            assert data["message"] == "Resource created successfully"

    def test_created_response_custom_message(self, app):
        """Test created response with custom message."""
        with app.test_request_context():
            response, status_code = created_response(data={}, message="User created")

            data = json.loads(response.get_data(as_text=True))

            assert data["message"] == "User created"


class TestNoContentResponse:
    """Test no_content_response convenience function."""

    def test_no_content_response_status_code(self, app):
        """Test that no content response returns 204 status."""
        with app.test_request_context():
            response, status_code = no_content_response()

            assert status_code == HTTPStatus.NO_CONTENT

    def test_no_content_response_empty_body(self, app):
        """Test that no content response has empty body."""
        with app.test_request_context():
            response, status_code = no_content_response()

            data = json.loads(response.get_data(as_text=True))

            assert data == {}


class TestBadRequestResponse:
    """Test bad_request_response convenience function."""

    def test_bad_request_response_status_code(self, app):
        """Test that bad request returns 400 status."""
        with app.test_request_context():
            response, status_code = bad_request_response()

            assert status_code == HTTPStatus.BAD_REQUEST

    def test_bad_request_response_error_code(self, app):
        """Test bad request error code."""
        with app.test_request_context():
            response, status_code = bad_request_response()

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["code"] == "BAD_REQUEST"


class TestUnauthorizedResponse:
    """Test unauthorized_response convenience function."""

    def test_unauthorized_response_status_code(self, app):
        """Test that unauthorized returns 401 status."""
        with app.test_request_context():
            response, status_code = unauthorized_response()

            assert status_code == HTTPStatus.UNAUTHORIZED

    def test_unauthorized_response_default_message(self, app):
        """Test unauthorized default message."""
        with app.test_request_context():
            response, status_code = unauthorized_response()

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["message"] == "Authentication required"


class TestForbiddenResponse:
    """Test forbidden_response convenience function."""

    def test_forbidden_response_status_code(self, app):
        """Test that forbidden returns 403 status."""
        with app.test_request_context():
            response, status_code = forbidden_response()

            assert status_code == HTTPStatus.FORBIDDEN

    def test_forbidden_response_default_message(self, app):
        """Test forbidden default message."""
        with app.test_request_context():
            response, status_code = forbidden_response()

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["message"] == "Access denied"


class TestNotFoundResponse:
    """Test not_found_response convenience function."""

    def test_not_found_response_status_code(self, app):
        """Test that not found returns 404 status."""
        with app.test_request_context():
            response, status_code = not_found_response()

            assert status_code == HTTPStatus.NOT_FOUND

    def test_not_found_response_custom_message(self, app):
        """Test not found with custom message."""
        with app.test_request_context():
            response, status_code = not_found_response("User not found")

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["message"] == "User not found"


class TestConflictResponse:
    """Test conflict_response convenience function."""

    def test_conflict_response_status_code(self, app):
        """Test that conflict returns 409 status."""
        with app.test_request_context():
            response, status_code = conflict_response()

            assert status_code == HTTPStatus.CONFLICT

    def test_conflict_response_with_details(self, app):
        """Test conflict response with details."""
        with app.test_request_context():
            details = {"field": "email", "existing_value": "john@example.com"}
            response, status_code = conflict_response(
                message="Email already exists", details=details
            )

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["details"] == details


class TestValidationErrorResponse:
    """Test validation_error_response convenience function."""

    def test_validation_error_response_status_code(self, app):
        """Test that validation error returns 422 status."""
        with app.test_request_context():
            response, status_code = validation_error_response()

            assert status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_validation_error_response_error_code(self, app):
        """Test validation error code."""
        with app.test_request_context():
            response, status_code = validation_error_response()

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_error_response_with_field_errors(self, app):
        """Test validation error with field-level errors."""
        with app.test_request_context():
            details = {
                "email": ["Invalid email format"],
                "password": ["Password too short", "Must contain number"],
            }
            response, status_code = validation_error_response(details=details)

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["details"] == details


class TestInternalErrorResponse:
    """Test internal_error_response convenience function."""

    def test_internal_error_response_status_code(self, app):
        """Test that internal error returns 500 status."""
        with app.test_request_context():
            response, status_code = internal_error_response()

            assert status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_internal_error_response_with_error_id(self, app):
        """Test internal error with tracking ID."""
        with app.test_request_context():
            response, status_code = internal_error_response(
                message="Database error", error_id="ERR_DB_12345"
            )

            data = json.loads(response.get_data(as_text=True))

            assert data["error"]["details"]["error_id"] == "ERR_DB_12345"


class TestResponseMetadata:
    """Test response metadata injection."""

    def test_response_includes_timestamp(self, app):
        """Test that all responses include timestamp in metadata."""
        with app.test_request_context():
            response, _ = success_response(data={})

            data = json.loads(response.get_data(as_text=True))

            assert "timestamp" in data["meta"]
            # Timestamp should be ISO format
            assert "T" in data["meta"]["timestamp"]  # ISO 8601 contains T

    def test_response_includes_request_id_when_available(self, app):
        """Test that responses include request_id from context."""
        with app.test_request_context():
            set_request_id("test-req-789")

            response, _ = success_response(data={})

            data = json.loads(response.get_data(as_text=True))

            assert data["meta"]["request_id"] == "test-req-789"

    def test_response_request_id_null_when_not_set(self, app):
        """Test that request_id is None when not set in context."""
        with app.test_request_context():
            # Don't set request_id
            response, _ = success_response(data={})

            data = json.loads(response.get_data(as_text=True))

            assert data["meta"]["request_id"] is None
