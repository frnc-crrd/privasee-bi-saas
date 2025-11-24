"""Unit tests for app.exceptions.handlers module.

Tests Flask error handlers for all exception types.
"""

import json

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.exceptions import (
    BadRequestException,
    InvalidCredentialsError,
    ResourceNotFoundException,
    ValidationError,
    register_error_handlers,
)


class TestRegisterErrorHandlers:
    """Test register_error_handlers function."""

    def test_register_error_handlers(self):
        """Test that register_error_handlers doesn't raise errors."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )

        # Should not raise
        register_error_handlers(app)


class TestBaseAPIExceptionHandler:
    """Test handler for BaseAPIException and subclasses."""

    def test_handle_resource_not_found(self):
        """Test handling ResourceNotFoundException."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-not-found")
        def test_route():
            raise ResourceNotFoundException("User not found", resource_type="User", resource_id=123)

        with app.test_client() as client:
            response = client.get("/test-not-found")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 404
            assert data["success"] is False
            assert data["error"]["message"] == "User not found"
            assert data["error"]["code"] == "NOT_FOUND"
            assert data["error"]["details"]["resource_type"] == "User"
            assert data["error"]["details"]["resource_id"] == 123

    def test_handle_bad_request(self):
        """Test handling BadRequestException."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-bad-request")
        def test_route():
            raise BadRequestException("Invalid input")

        with app.test_client() as client:
            response = client.get("/test-bad-request")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 400
            assert data["error"]["message"] == "Invalid input"
            assert data["error"]["code"] == "BAD_REQUEST"


class TestAuthenticationErrorHandler:
    """Test handler for authentication errors."""

    def test_handle_invalid_credentials(self):
        """Test handling InvalidCredentialsError."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-invalid-creds")
        def test_route():
            raise InvalidCredentialsError("Bad password")

        with app.test_client() as client:
            response = client.get("/test-invalid-creds")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 401
            assert data["error"]["message"] == "Bad password"
            assert data["error"]["code"] == "INVALID_CREDENTIALS"


class TestValidationErrorHandler:
    """Test handler for validation errors."""

    def test_handle_validation_error(self):
        """Test handling ValidationError with field errors."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-validation")
        def test_route():
            raise ValidationError(
                message="Invalid data",
                field_errors={
                    "email": ["Invalid format"],
                    "age": ["Must be positive"],
                },
            )

        with app.test_client() as client:
            response = client.get("/test-validation")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 422
            assert data["error"]["message"] == "Invalid data"
            assert data["error"]["code"] == "VALIDATION_ERROR"
            assert "field_errors" in data["error"]["details"]
            assert "email" in data["error"]["details"]["field_errors"]
            assert "age" in data["error"]["details"]["field_errors"]


class TestPydanticValidationErrorHandler:
    """Test handler for Pydantic validation errors."""

    def test_handle_pydantic_validation_error(self):
        """Test handling Pydantic ValidationError."""
        from app import create_app

        class TestModel(BaseModel):
            email: str
            age: int

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-pydantic")
        def test_route():
            try:
                TestModel(email=123, age="not-a-number")
            except PydanticValidationError as e:
                raise e

        with app.test_client() as client:
            response = client.get("/test-pydantic")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 422
            assert data["error"]["code"] == "VALIDATION_ERROR"
            assert "field_errors" in data["error"]["details"]


class TestSQLAlchemyErrorHandlers:
    """Test handlers for SQLAlchemy errors."""

    def test_handle_integrity_error(self):
        """Test handling SQLAlchemy IntegrityError."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-integrity")
        def test_route():
            # Simulate unique constraint violation
            error = IntegrityError(
                statement="INSERT INTO users...",
                params={},
                orig=Exception("UNIQUE constraint failed: users.email"),
            )
            raise error

        with app.test_client() as client:
            response = client.get("/test-integrity")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 409
            assert data["error"]["code"] == "DUPLICATE_ENTRY"

    def test_handle_operational_error(self):
        """Test handling SQLAlchemy OperationalError."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-operational")
        def test_route():
            error = OperationalError(
                statement="SELECT...",
                params={},
                orig=Exception("Connection failed"),
            )
            raise error

        with app.test_client() as client:
            response = client.get("/test-operational")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 500
            assert data["error"]["message"] == "Database operation failed"


class TestWerkzeugHTTPExceptionHandlers:
    """Test handlers for Werkzeug HTTP exceptions."""

    def test_handle_404_not_found(self):
        """Test handling 404 Not Found."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        with app.test_client() as client:
            response = client.get("/nonexistent-route")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 404
            assert data["error"]["code"] == "NOT_FOUND"

    def test_handle_405_method_not_allowed(self):
        """Test handling 405 Method Not Allowed."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-method", methods=["GET"])
        def test_route():
            return "OK"

        with app.test_client() as client:
            response = client.post("/test-method")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 405
            assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
            assert "allowed_methods" in data["error"]["details"]


class TestUnexpectedExceptionHandler:
    """Test handler for unexpected exceptions."""

    def test_handle_unexpected_exception(self):
        """Test handling unexpected exceptions."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-unexpected")
        def test_route():
            raise RuntimeError("Something went wrong")

        with app.test_client() as client:
            response = client.get("/test-unexpected")
            data = json.loads(response.get_data(as_text=True))

            assert response.status_code == 500
            assert data["error"]["message"] == "An unexpected error occurred"
            assert data["error"]["code"] == "INTERNAL_ERROR"


class TestErrorResponseStructure:
    """Test that all error responses follow standard structure."""

    def test_error_response_has_meta(self):
        """Test that error responses include metadata."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-error")
        def test_route():
            raise BadRequestException("Test error")

        with app.test_client() as client:
            response = client.get("/test-error")
            data = json.loads(response.get_data(as_text=True))

            # Check standard structure
            assert "success" in data
            assert "data" in data
            assert "error" in data
            assert "meta" in data

            # Check metadata
            assert "timestamp" in data["meta"]

    def test_error_response_consistency(self):
        """Test that all errors return consistent structure."""
        from app import create_app

        app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        register_error_handlers(app)

        @app.route("/test-not-found")
        def test_not_found():
            raise ResourceNotFoundException("Not found")

        @app.route("/test-validation")
        def test_validation():
            raise ValidationError("Invalid")

        with app.test_client() as client:
            # Test multiple error types
            response1 = client.get("/test-not-found")
            response2 = client.get("/test-validation")

            data1 = json.loads(response1.get_data(as_text=True))
            data2 = json.loads(response2.get_data(as_text=True))

            # Both should have same top-level keys
            assert set(data1.keys()) == set(data2.keys())

            # Both should have required error keys
            required_error_keys = {"message", "code"}
            assert required_error_keys.issubset(data1["error"].keys())
            assert required_error_keys.issubset(data2["error"].keys())
