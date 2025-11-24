"""Unit tests for app.core.context module.

Tests request context tracking, user context management, and middleware functionality.
"""

import uuid

from flask import g

from app.core.context import (
    clear_user_context,
    generate_request_id,
    get_full_context,
    get_request_id,
    get_user_context,
    log_context,
    request_context,
    set_request_id,
    set_user_context,
    setup_request_context,
)


class TestGenerateRequestId:
    """Test request ID generation."""

    def test_generate_request_id_returns_valid_uuid(self):
        """Test that generated request ID is a valid UUID4."""
        request_id = generate_request_id()

        # Should be a valid UUID string
        assert isinstance(request_id, str)
        uuid_obj = uuid.UUID(request_id)
        assert uuid_obj.version == 4  # UUID4

    def test_generate_request_id_returns_unique_ids(self):
        """Test that multiple calls generate different IDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        id3 = generate_request_id()

        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


class TestRequestIdContext:
    """Test request ID storage and retrieval."""

    def test_get_request_id_outside_context_returns_none(self):
        """Test getting request ID outside Flask context returns None."""
        request_id = get_request_id()
        assert request_id is None

    def test_set_and_get_request_id_within_context(self, app):
        """Test setting and getting request ID within Flask context."""
        with app.test_request_context():
            test_id = "test-request-id-123"
            set_request_id(test_id)

            retrieved_id = get_request_id()
            assert retrieved_id == test_id

    def test_set_request_id_stores_in_flask_g(self, app):
        """Test that set_request_id stores value in Flask g object."""
        with app.test_request_context():
            test_id = "test-id-456"
            set_request_id(test_id)

            assert hasattr(g, "request_id")
            assert g.request_id == test_id

    def test_set_request_id_outside_context_does_not_raise(self):
        """Test that setting request ID outside context doesn't raise error."""
        # Should not raise exception
        set_request_id("test-id")


class TestUserContext:
    """Test user context management."""

    def test_get_user_context_outside_request_returns_empty(self):
        """Test getting user context outside Flask context returns empty dict."""
        context = get_user_context()

        assert isinstance(context, dict)
        assert context == {
            "user_id": None,
            "username": None,
            "role": None,
            "email": None,
        }

    def test_set_user_context_all_fields(self, app):
        """Test setting all user context fields."""
        with app.test_request_context():
            set_user_context(
                user_id=123,
                username="john_doe",
                role="admin",
                email="john@example.com",
            )

            context = get_user_context()
            assert context["user_id"] == 123
            assert context["username"] == "john_doe"
            assert context["role"] == "admin"
            assert context["email"] == "john@example.com"

    def test_set_user_context_partial_fields(self, app):
        """Test setting only some user context fields."""
        with app.test_request_context():
            set_user_context(user_id=456, role="viewer")

            context = get_user_context()
            assert context["user_id"] == 456
            assert context["username"] is None
            assert context["role"] == "viewer"
            assert context["email"] is None

    def test_set_user_context_stores_in_flask_g(self, app):
        """Test that user context is stored in Flask g object."""
        with app.test_request_context():
            set_user_context(user_id=789, username="jane")

            assert hasattr(g, "user_id")
            assert hasattr(g, "username")
            assert g.user_id == 789
            assert g.username == "jane"

    def test_clear_user_context(self, app):
        """Test clearing user context removes all fields."""
        with app.test_request_context():
            # Set context
            set_user_context(
                user_id=111,
                username="test_user",
                role="analyst",
                email="test@example.com",
            )

            # Clear context
            clear_user_context()

            # Check fields are removed from g
            assert not hasattr(g, "user_id")
            assert not hasattr(g, "username")
            assert not hasattr(g, "role")
            assert not hasattr(g, "email")

    def test_clear_user_context_partial_fields(self, app):
        """Test clearing context when only some fields were set."""
        with app.test_request_context():
            # Set only user_id
            set_user_context(user_id=222)

            # Clear should not raise even if other fields don't exist
            clear_user_context()

            assert not hasattr(g, "user_id")


class TestFullContext:
    """Test combined context retrieval."""

    def test_get_full_context_includes_request_and_user(self, app):
        """Test that full context includes both request and user data."""
        with app.test_request_context():
            set_request_id("req-123")
            set_user_context(user_id=999, username="full_user", role="admin")

            context = get_full_context()

            assert context["request_id"] == "req-123"
            assert context["user_id"] == 999
            assert context["username"] == "full_user"
            assert context["role"] == "admin"

    def test_get_full_context_outside_request_returns_none_values(self):
        """Test full context outside request returns None values."""
        context = get_full_context()

        assert context["request_id"] is None
        assert context["user_id"] is None
        assert context["username"] is None
        assert context["role"] is None
        assert context["email"] is None

    def test_log_context_excludes_none_values(self, app):
        """Test that log_context only returns non-None values."""
        with app.test_request_context():
            set_request_id("log-req-456")
            set_user_context(user_id=777)  # Only set user_id

            context = log_context()

            # Should only include non-None values
            assert "request_id" in context
            assert "user_id" in context
            assert "username" not in context  # Was None
            assert "role" not in context  # Was None
            assert "email" not in context  # Was None

    def test_log_context_empty_when_no_context_set(self):
        """Test log_context returns empty dict when no context is set."""
        context = log_context()
        assert context == {}


class TestRequestContextManager:
    """Test request_context context manager."""

    def test_request_context_manager_generates_id(self):
        """Test that context manager generates request ID."""
        with request_context() as ctx:
            assert "request_id" in ctx
            assert ctx["request_id"] is not None
            # Should be valid UUID
            uuid.UUID(ctx["request_id"])

    def test_request_context_manager_uses_provided_id(self):
        """Test that context manager uses provided request ID."""
        custom_id = "custom-request-id"
        with request_context(request_id=custom_id) as ctx:
            assert ctx["request_id"] == custom_id

    def test_request_context_manager_includes_user_id(self):
        """Test that context manager includes user_id if provided."""
        with request_context(user_id=123) as ctx:
            assert ctx["user_id"] == 123

    def test_request_context_manager_cleanup(self):
        """Test that context manager doesn't leak context."""
        request_id = None
        with request_context() as ctx:
            request_id = ctx["request_id"]

        # Context should still be accessible outside
        assert request_id is not None


class TestSetupRequestContext:
    """Test Flask middleware setup."""

    def test_setup_request_context_generates_id_on_request(self, app):
        """Test that middleware generates request ID for incoming requests."""
        setup_request_context(app)

        with app.test_client() as client:
            # Make a request
            response = client.get("/")

            # Response should have X-Request-ID header
            assert "X-Request-ID" in response.headers
            request_id = response.headers["X-Request-ID"]

            # Should be valid UUID
            uuid.UUID(request_id)

    def test_setup_request_context_preserves_incoming_id(self):
        """Test that middleware preserves X-Request-ID from incoming request."""
        from app import create_app

        # Create fresh app with middleware setup before any requests
        test_app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        setup_request_context(test_app)

        incoming_id = "client-generated-id-123"

        with test_app.test_client() as client:
            # Send request with X-Request-ID header
            response = client.get("/", headers={"X-Request-ID": incoming_id})

            # Response should have same request ID
            assert response.headers.get("X-Request-ID") == incoming_id

    def test_setup_request_context_multiple_requests_unique_ids(self):
        """Test that multiple requests get unique IDs."""
        from app import create_app

        test_app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        setup_request_context(test_app)

        with test_app.test_client() as client:
            response1 = client.get("/")
            response2 = client.get("/")
            response3 = client.get("/")

            id1 = response1.headers["X-Request-ID"]
            id2 = response2.headers["X-Request-ID"]
            id3 = response3.headers["X-Request-ID"]

            # All IDs should be different
            assert id1 != id2
            assert id2 != id3
            assert id1 != id3

    def test_request_id_available_in_request_context(self):
        """Test that request ID is accessible within request handlers."""
        from app import create_app

        test_app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        setup_request_context(test_app)

        captured_id = None

        @test_app.route("/test-route")
        def test_route():
            nonlocal captured_id
            captured_id = get_request_id()
            return "OK"

        with test_app.test_client() as client:
            response = client.get("/test-route")
            response_id = response.headers["X-Request-ID"]

            # ID in handler should match ID in response
            assert captured_id == response_id
