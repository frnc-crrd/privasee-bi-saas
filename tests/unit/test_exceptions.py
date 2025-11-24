"""Unit tests for app.exceptions module.

Tests exception hierarchy, attributes, and methods.
"""

from http import HTTPStatus

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.exceptions import (
    AccountInactiveError,
    AuthenticationError,
    AuthorizationError,
    BadRequestException,
    BaseAPIException,
    BusinessRuleViolationError,
    ConflictException,
    DatabaseException,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidFormatError,
    InvalidTokenError,
    RequiredFieldError,
    ResourceAccessDeniedError,
    ResourceNotFoundException,
    SchemaValidationError,
    TokenExpiredError,
    ValidationError,
    ValueRangeError,
)


class TestBaseAPIException:
    """Test BaseAPIException class."""

    def test_base_exception_default_values(self):
        """Test BaseAPIException with default values."""
        exc = BaseAPIException("Test error")

        assert exc.message == "Test error"
        assert exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert exc.error_code == "API_ERROR"
        assert exc.details == {}

    def test_base_exception_custom_values(self):
        """Test BaseAPIException with custom values."""
        exc = BaseAPIException(
            message="Custom error",
            status_code=400,
            error_code="CUSTOM_ERROR",
            details={"key": "value"},
        )

        assert exc.message == "Custom error"
        assert exc.status_code == 400
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"key": "value"}

    def test_base_exception_to_dict(self):
        """Test to_dict method."""
        exc = BaseAPIException(
            message="Test",
            error_code="TEST_ERROR",
            details={"field": "value"},
        )

        result = exc.to_dict()

        assert result == {
            "message": "Test",
            "code": "TEST_ERROR",
            "details": {"field": "value"},
        }

    def test_base_exception_str(self):
        """Test string representation."""
        exc = BaseAPIException("Test error", error_code="TEST_CODE")

        assert str(exc) == "[TEST_CODE] Test error"

    def test_base_exception_repr(self):
        """Test repr representation."""
        exc = BaseAPIException("Test", status_code=400, error_code="TEST", details={"k": "v"})

        repr_str = repr(exc)

        assert "BaseAPIException" in repr_str
        assert "Test" in repr_str
        assert "400" in repr_str
        assert "TEST" in repr_str


class TestDatabaseException:
    """Test DatabaseException class."""

    def test_database_exception_default(self):
        """Test DatabaseException with default message."""
        exc = DatabaseException()

        assert exc.message == "Database operation failed"
        assert exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert exc.error_code == "DATABASE_ERROR"

    def test_database_exception_custom_message(self):
        """Test DatabaseException with custom message."""
        exc = DatabaseException(message="Connection failed", details={"table": "users"})

        assert exc.message == "Connection failed"
        assert exc.details == {"table": "users"}


class TestResourceNotFoundException:
    """Test ResourceNotFoundException class."""

    def test_resource_not_found_default(self):
        """Test ResourceNotFoundException with default message."""
        exc = ResourceNotFoundException()

        assert exc.message == "Resource not found"
        assert exc.status_code == HTTPStatus.NOT_FOUND
        assert exc.error_code == "NOT_FOUND"

    def test_resource_not_found_with_resource_info(self):
        """Test ResourceNotFoundException with resource information."""
        exc = ResourceNotFoundException(
            message="User not found", resource_type="User", resource_id=123
        )

        assert exc.message == "User not found"
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == 123


class TestConflictException:
    """Test ConflictException class."""

    def test_conflict_exception_default(self):
        """Test ConflictException with default message."""
        exc = ConflictException()

        assert exc.message == "Resource conflict"
        assert exc.status_code == HTTPStatus.CONFLICT
        assert exc.error_code == "CONFLICT"

    def test_conflict_exception_with_details(self):
        """Test ConflictException with conflict details."""
        exc = ConflictException(message="Email exists", details={"field": "email"})

        assert exc.message == "Email exists"
        assert exc.details["field"] == "email"


class TestBadRequestException:
    """Test BadRequestException class."""

    def test_bad_request_exception_default(self):
        """Test BadRequestException with default message."""
        exc = BadRequestException()

        assert exc.message == "Bad request"
        assert exc.status_code == HTTPStatus.BAD_REQUEST
        assert exc.error_code == "BAD_REQUEST"


class TestAuthenticationError:
    """Test AuthenticationError and subclasses."""

    def test_authentication_error_default(self):
        """Test AuthenticationError with default values."""
        exc = AuthenticationError()

        assert exc.message == "Authentication required"
        assert exc.status_code == HTTPStatus.UNAUTHORIZED
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError."""
        exc = InvalidCredentialsError()

        assert exc.message == "Invalid email or password"
        assert exc.status_code == HTTPStatus.UNAUTHORIZED
        assert exc.error_code == "INVALID_CREDENTIALS"

    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        exc = TokenExpiredError()

        assert exc.message == "Authentication token has expired"
        assert exc.error_code == "TOKEN_EXPIRED"

    def test_invalid_token_error(self):
        """Test InvalidTokenError."""
        exc = InvalidTokenError()

        assert exc.message == "Invalid authentication token"
        assert exc.error_code == "INVALID_TOKEN"

    def test_account_inactive_error(self):
        """Test AccountInactiveError."""
        exc = AccountInactiveError()

        assert exc.message == "Account is inactive or disabled"
        assert exc.error_code == "ACCOUNT_INACTIVE"


class TestAuthorizationError:
    """Test AuthorizationError and subclasses."""

    def test_authorization_error_default(self):
        """Test AuthorizationError with default values."""
        exc = AuthorizationError()

        assert exc.message == "Access denied"
        assert exc.status_code == HTTPStatus.FORBIDDEN
        assert exc.error_code == "AUTHORIZATION_ERROR"

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError."""
        exc = InsufficientPermissionsError(
            message="Admin required",
            required_roles=["admin"],
            user_role="viewer",
        )

        assert exc.message == "Admin required"
        assert exc.error_code == "INSUFFICIENT_PERMISSIONS"
        assert exc.details["required_roles"] == ["admin"]
        assert exc.details["user_role"] == "viewer"

    def test_resource_access_denied_error(self):
        """Test ResourceAccessDeniedError."""
        exc = ResourceAccessDeniedError(
            message="Cannot view order",
            resource_type="Order",
            resource_id=456,
        )

        assert exc.message == "Cannot view order"
        assert exc.error_code == "RESOURCE_ACCESS_DENIED"
        assert exc.details["resource_type"] == "Order"
        assert exc.details["resource_id"] == 456


class TestValidationError:
    """Test ValidationError and subclasses."""

    def test_validation_error_default(self):
        """Test ValidationError with default values."""
        exc = ValidationError()

        assert exc.message == "Validation failed"
        assert exc.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.field_errors == {}

    def test_validation_error_with_field_errors(self):
        """Test ValidationError with field errors."""
        field_errors = {
            "email": ["Invalid format"],
            "password": ["Too short"],
        }

        exc = ValidationError(
            message="Invalid data",
            field_errors=field_errors,
        )

        assert exc.message == "Invalid data"
        assert exc.field_errors == field_errors
        assert exc.details["field_errors"] == field_errors


class TestSchemaValidationError:
    """Test SchemaValidationError class."""

    def test_schema_validation_error_default(self):
        """Test SchemaValidationError with default values."""
        exc = SchemaValidationError()

        assert exc.message == "Schema validation failed"
        assert exc.error_code == "SCHEMA_VALIDATION_ERROR"

    def test_schema_validation_error_from_pydantic(self):
        """Test from_pydantic class method."""

        class TestModel(BaseModel):
            email: str
            age: int

        # Trigger Pydantic validation error
        try:
            TestModel(email="invalid", age="not-a-number")
        except PydanticValidationError as e:
            exc = SchemaValidationError.from_pydantic(e)

            assert exc.message == "Request validation failed"
            assert exc.error_code == "SCHEMA_VALIDATION_ERROR"
            assert "age" in exc.field_errors
            assert len(exc.field_errors["age"]) > 0


class TestRequiredFieldError:
    """Test RequiredFieldError class."""

    def test_required_field_error_default_message(self):
        """Test RequiredFieldError with default message."""
        exc = RequiredFieldError("email")

        assert exc.message == "Field 'email' is required"
        assert exc.error_code == "REQUIRED_FIELD_ERROR"
        assert exc.field_errors == {"email": ["This field is required"]}

    def test_required_field_error_custom_message(self):
        """Test RequiredFieldError with custom message."""
        exc = RequiredFieldError(
            field_name="password",
            message="Password must be provided",
        )

        assert exc.message == "Password must be provided"


class TestInvalidFormatError:
    """Test InvalidFormatError class."""

    def test_invalid_format_error(self):
        """Test InvalidFormatError with format details."""
        exc = InvalidFormatError(
            field_name="email",
            expected_format="valid email address",
            actual_value="not-an-email",
        )

        assert exc.message == "Field 'email' has invalid format"
        assert exc.error_code == "INVALID_FORMAT_ERROR"
        assert exc.details["expected_format"] == "valid email address"
        assert exc.details["actual_value"] == "not-an-email"
        assert exc.field_errors["email"] == ["Expected format: valid email address"]


class TestValueRangeError:
    """Test ValueRangeError class."""

    def test_value_range_error_min_max(self):
        """Test ValueRangeError with min and max values."""
        exc = ValueRangeError(
            field_name="age",
            min_value=18,
            max_value=120,
            actual_value=150,
        )

        assert "between 18 and 120" in exc.message
        assert exc.error_code == "VALUE_RANGE_ERROR"
        assert exc.details["min_value"] == 18
        assert exc.details["max_value"] == 120
        assert exc.details["actual_value"] == 150

    def test_value_range_error_min_only(self):
        """Test ValueRangeError with only min value."""
        exc = ValueRangeError(
            field_name="price",
            min_value=0,
        )

        assert "at least 0" in exc.message

    def test_value_range_error_max_only(self):
        """Test ValueRangeError with only max value."""
        exc = ValueRangeError(
            field_name="quantity",
            max_value=100,
        )

        assert "at most 100" in exc.message


class TestBusinessRuleViolationError:
    """Test BusinessRuleViolationError class."""

    def test_business_rule_violation_error(self):
        """Test BusinessRuleViolationError with rule details."""
        exc = BusinessRuleViolationError(
            message="Cannot delete active order",
            rule_name="order_deletion_policy",
            details={"order_id": 123, "status": "active"},
        )

        assert exc.message == "Cannot delete active order"
        assert exc.error_code == "BUSINESS_RULE_VIOLATION"
        assert exc.details["rule_name"] == "order_deletion_policy"
        assert exc.details["order_id"] == 123
