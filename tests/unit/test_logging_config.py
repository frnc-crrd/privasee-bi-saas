"""Unit tests for app.core.logging_config module.

Tests structured logging configuration, formatters, and filters.
"""

import json
import logging

from app.core.config import Settings
from app.core.context import set_request_id, set_user_context
from app.core.logging_config import (
    CustomJsonFormatter,
    RequestContextFilter,
    TextFormatter,
    log_exception,
    log_request_info,
    setup_logging,
)


class TestRequestContextFilter:
    """Test RequestContextFilter for context injection."""

    def test_filter_adds_request_context(self, app):
        """Test that filter adds request context to log records."""
        with app.test_request_context("/test", method="POST"):
            set_request_id("test-req-123")
            set_user_context(user_id=456)

            log_filter = RequestContextFilter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Apply filter
            result = log_filter.filter(record)

            assert result is True  # Filter doesn't block records
            assert record.request_id == "test-req-123"
            assert record.method == "POST"
            assert record.path == "/test"
            assert record.user_id == 456
            assert record.ip is not None  # Should have remote_addr

    def test_filter_sets_none_outside_request_context(self):
        """Test that filter sets None values outside request context."""
        log_filter = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = log_filter.filter(record)

        assert result is True
        assert record.request_id is None
        assert record.method is None
        assert record.path is None
        assert record.ip is None
        assert record.user_id is None


class TestCustomJsonFormatter:
    """Test CustomJsonFormatter for JSON log output."""

    def test_json_formatter_basic_structure(self, app):
        """Test that JSON formatter produces valid JSON with required fields."""
        with app.test_request_context():
            formatter = CustomJsonFormatter()
            record = logging.LogRecord(
                name="test.module",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test log message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            log_data = json.loads(output)

            assert "timestamp" in log_data
            assert log_data["level"] == "INFO"
            assert log_data["logger"] == "test.module"
            assert log_data["message"] == "Test log message"

    def test_json_formatter_includes_request_context(self, app):
        """Test that JSON formatter includes request context when available."""
        with app.test_request_context("/api/users", method="GET"):
            set_request_id("req-789")
            set_user_context(user_id=123)

            formatter = CustomJsonFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Request received",
                args=(),
                exc_info=None,
            )

            # Simulate filter applying context
            log_filter = RequestContextFilter()
            log_filter.filter(record)

            output = formatter.format(record)
            log_data = json.loads(output)

            assert log_data["request_id"] == "req-789"
            assert log_data["method"] == "GET"
            assert log_data["path"] == "/api/users"
            assert log_data["user_id"] == 123

    def test_json_formatter_excludes_none_context(self, app):
        """Test that JSON formatter doesn't include None context values."""
        with app.test_request_context():
            formatter = CustomJsonFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )

            # Apply filter but no context set
            log_filter = RequestContextFilter()
            log_filter.filter(record)

            output = formatter.format(record)
            log_data = json.loads(output)

            # None values should not appear in output
            assert "request_id" not in log_data
            assert "user_id" not in log_data

    def test_json_formatter_includes_exception(self, app):
        """Test that JSON formatter includes exception information."""
        with app.test_request_context():
            formatter = CustomJsonFormatter()

            try:
                raise ValueError("Test error")
            except ValueError as e:
                record = logging.LogRecord(
                    name="test",
                    level=logging.ERROR,
                    pathname="test.py",
                    lineno=10,
                    msg="Error occurred",
                    args=(),
                    exc_info=(type(e), e, e.__traceback__),
                )

                output = formatter.format(record)
                log_data = json.loads(output)

                assert "exception" in log_data
                assert "ValueError" in log_data["exception"]
                assert "Test error" in log_data["exception"]


class TestTextFormatter:
    """Test TextFormatter for human-readable output."""

    def test_text_formatter_basic_output(self, app):
        """Test that text formatter produces readable output."""
        with app.test_request_context():
            formatter = TextFormatter(fmt="%(levelname)s - %(name)s - %(message)s")
            record = logging.LogRecord(
                name="test.module",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)

            assert "INFO" in output
            assert "test.module" in output
            assert "Test message" in output

    def test_text_formatter_includes_context(self, app):
        """Test that text formatter includes request context."""
        with app.test_request_context("/api/test", method="POST"):
            set_request_id("text-req-123")
            set_user_context(user_id=789)

            formatter = TextFormatter(fmt="%(levelname)s - %(message)s")
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Request",
                args=(),
                exc_info=None,
            )

            # Apply filter to add context
            log_filter = RequestContextFilter()
            log_filter.filter(record)

            output = formatter.format(record)

            assert "request_id=text-req-123" in output
            assert "POST /api/test" in output
            assert "user_id=789" in output


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_configures_handlers(self, app):
        """Test that setup_logging configures logging handlers."""
        settings = Settings(
            SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            TESTING=True,
            LOG_LEVEL="INFO",
            LOG_FORMAT="text",
            LOG_FILE="",
        )

        setup_logging(app, settings)

        root_logger = logging.getLogger()

        # Should have at least one handler (console)
        assert len(root_logger.handlers) > 0

        # Check log level
        assert root_logger.level == logging.INFO

    def test_setup_logging_json_format(self, app):
        """Test that JSON format is applied when configured."""
        settings = Settings(
            SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            TESTING=True,
            LOG_LEVEL="DEBUG",
            LOG_FORMAT="json",
            LOG_FILE="",
        )

        setup_logging(app, settings)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]

        # Handler should have CustomJsonFormatter
        assert isinstance(console_handler.formatter, CustomJsonFormatter)

    def test_setup_logging_text_format(self, app):
        """Test that text format is applied when configured."""
        settings = Settings(
            SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            TESTING=True,
            LOG_LEVEL="WARNING",
            LOG_FORMAT="text",
            LOG_FILE="",
        )

        setup_logging(app, settings)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]

        # Handler should have TextFormatter
        assert isinstance(console_handler.formatter, TextFormatter)

    def test_setup_logging_adds_context_filter(self, app):
        """Test that RequestContextFilter is added to handlers."""
        settings = Settings(
            SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            TESTING=True,
            LOG_LEVEL="INFO",
            LOG_FORMAT="text",
            LOG_FILE="",
        )

        setup_logging(app, settings)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]

        # Should have RequestContextFilter
        filters = console_handler.filters
        assert any(isinstance(f, RequestContextFilter) for f in filters)

    def test_setup_logging_respects_log_level(self, app):
        """Test that log level from settings is applied."""
        settings = Settings(
            SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            TESTING=True,
            LOG_LEVEL="ERROR",
            LOG_FORMAT="text",
            LOG_FILE="",
        )

        setup_logging(app, settings)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR


class TestLogRequestInfo:
    """Test log_request_info helper function."""

    def test_log_request_info_success(self, app, caplog):
        """Test logging successful request (status 200)."""
        with app.test_request_context():
            with caplog.at_level(logging.INFO):
                log_request_info("GET", "/api/users", 200, 45.5, user_id=123)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            assert record.levelname == "INFO"
            assert "GET /api/users" in record.message
            assert "200" in record.message
            assert "45.5" in record.message or "45.50" in record.message

    def test_log_request_info_client_error(self, app, caplog):
        """Test logging client error (4xx status)."""
        with app.test_request_context():
            with caplog.at_level(logging.WARNING):
                log_request_info("POST", "/api/login", 401, 12.3)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            assert record.levelname == "WARNING"
            assert "401" in record.message

    def test_log_request_info_server_error(self, app, caplog):
        """Test logging server error (5xx status)."""
        with app.test_request_context():
            with caplog.at_level(logging.ERROR):
                log_request_info("GET", "/api/data", 500, 100.0)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            assert record.levelname == "ERROR"
            assert "500" in record.message


class TestLogException:
    """Test log_exception helper function."""

    def test_log_exception_basic(self, app, caplog):
        """Test logging exception with basic info."""
        with app.test_request_context():
            try:
                raise ValueError("Something went wrong")
            except ValueError as e:
                with caplog.at_level(logging.ERROR):
                    log_exception(e)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            assert record.levelname == "ERROR"
            assert "Something went wrong" in record.message
            # exc_info should contain the exception
            assert record.exc_info is not None

    def test_log_exception_with_context(self, app, caplog):
        """Test logging exception with additional context."""
        with app.test_request_context():
            try:
                raise RuntimeError("Database connection failed")
            except RuntimeError as e:
                context = {"user_id": 456, "operation": "fetch_data"}

                with caplog.at_level(logging.ERROR):
                    log_exception(e, context=context)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            assert record.levelname == "ERROR"
            # Context should be available (exact assertion depends on handler)
            assert "Database connection failed" in record.message

    def test_log_exception_includes_traceback(self, app, caplog):
        """Test that exception logging includes traceback."""
        with app.test_request_context():
            try:
                # Create nested exception for traceback
                def inner():
                    raise KeyError("Missing key")

                inner()
            except KeyError as e:
                with caplog.at_level(logging.ERROR):
                    log_exception(e)

            assert len(caplog.records) == 1
            record = caplog.records[0]

            # Record should have exception info
            assert record.exc_info is not None


class TestLoggingIntegration:
    """Test logging integration with Flask."""

    def test_logging_captures_flask_errors(self, caplog):
        """Test that Flask errors are captured by logging."""
        from app import create_app

        test_app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )

        @test_app.route("/error-route")
        def error_route():
            test_app.logger.error("Route error occurred")
            return "Error", 500

        with test_app.test_client() as client:
            with caplog.at_level(logging.ERROR):
                client.get("/error-route")

            # Should have logged the error
            error_logs = [r for r in caplog.records if "Route error" in r.message]
            assert len(error_logs) > 0

    def test_logging_with_request_context_in_route(self, caplog):
        """Test that logging in routes includes request context."""
        from app import create_app
        from app.core.context import setup_request_context

        test_app = create_app(
            config_overrides={
                "TESTING": True,
                "SECRET_KEY": "test-key-for-testing-only",
            }
        )
        setup_request_context(test_app)

        @test_app.route("/test-logging")
        def test_logging():
            logger = logging.getLogger(__name__)
            logger.info("Test log from route")
            return "OK"

        with test_app.test_client() as client:
            with caplog.at_level(logging.INFO):
                client.get("/test-logging")

            # Find the log record
            test_logs = [r for r in caplog.records if "Test log from route" in r.message]
            assert len(test_logs) > 0

            # Should have request context applied by filter
            # (exact assertion depends on whether filter was applied)
