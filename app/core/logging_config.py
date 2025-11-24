"""Structured logging configuration with JSON output support.

This module provides enterprise-grade logging infrastructure with:
- Structured JSON logging for production environments
- Human-readable text logging for development
- Request context injection (request_id, user_id, endpoint)
- Flask integration with automatic request/response logging
- Log level configuration per environment
- File and console output support

Usage:
    from app.core.logging_config import setup_logging

    # In application factory
    app = Flask(__name__)
    setup_logging(app, settings)

    # Use standard Python logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info("User logged in", extra={"user_id": 123, "email": "user@example.com"})
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Flask, g, has_request_context, request
from pythonjsonlogger import jsonlogger

from app.core.config import Settings


class RequestContextFilter(logging.Filter):
    """Inject Flask request context into log records.

    Automatically adds request metadata to all log records when executing
    within a Flask request context:
    - request_id: Unique identifier for request tracing
    - method: HTTP method (GET, POST, etc.)
    - path: Request path
    - ip: Client IP address
    - user_id: Authenticated user ID (if available)

    Attributes:
        None
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record.

        Args:
            record: Log record to be enriched with context

        Returns:
            Always True (does not filter out records)
        """
        if has_request_context():
            record.request_id = getattr(g, "request_id", None)
            record.method = request.method
            record.path = request.path
            record.ip = request.remote_addr
            record.user_id = getattr(g, "user_id", None)
        else:
            record.request_id = None
            record.method = None
            record.path = None
            record.ip = None
            record.user_id = None

        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with custom field mapping and ISO timestamps.

    Produces structured JSON logs with consistent field names:
    - timestamp: ISO 8601 format with UTC timezone
    - level: Log level name (INFO, ERROR, etc.)
    - logger: Logger name (module path)
    - message: Log message
    - Additional fields from extra parameter or request context

    Attributes:
        None
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to JSON log record.

        Args:
            log_record: Dictionary that will be serialized to JSON
            record: Standard Python log record
            message_dict: Additional fields from log call
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 format
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Rename fields for consistency
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add request context if available
        if hasattr(record, "request_id") and record.request_id:
            log_record["request_id"] = record.request_id
        if hasattr(record, "method") and record.method:
            log_record["method"] = record.method
        if hasattr(record, "path") and record.path:
            log_record["path"] = record.path
        if hasattr(record, "ip") and record.ip:
            log_record["ip"] = record.ip
        if hasattr(record, "user_id") and record.user_id:
            log_record["user_id"] = record.user_id

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development.

    Produces colored, multi-line logs suitable for terminal output.
    Includes all request context fields in a readable format.

    Attributes:
        None
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Base format: timestamp - level - logger - message
        base_msg = super().format(record)

        # Add request context if available
        context_parts = []
        if hasattr(record, "request_id") and record.request_id:
            context_parts.append(f"request_id={record.request_id}")
        if hasattr(record, "method") and record.method:
            context_parts.append(f"{record.method} {record.path}")
        if hasattr(record, "user_id") and record.user_id:
            context_parts.append(f"user_id={record.user_id}")

        if context_parts:
            base_msg += f" [{' | '.join(context_parts)}]"

        return base_msg


def setup_logging(app: Flask, settings: Settings) -> None:
    """Configure application logging based on environment settings.

    Sets up structured logging with:
    - JSON output for production (machine-readable)
    - Text output for development (human-readable)
    - Request context injection via middleware
    - Console and file handlers as configured
    - Werkzeug and SQLAlchemy log configuration

    Args:
        app: Flask application instance
        settings: Application settings with logging configuration

    Returns:
        None

    Example:
        >>> from flask import Flask
        >>> from app.core.config import get_settings
        >>> app = Flask(__name__)
        >>> settings = get_settings()
        >>> setup_logging(app, settings)
    """
    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatter based on environment
    if settings.LOG_FORMAT.lower() == "json":
        formatter: logging.Formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
    else:
        formatter = TextFormatter(
            fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)

    # Configure Werkzeug (Flask) logger
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.WARNING if settings.ENVIRONMENT == "production" else log_level)

    # Configure SQLAlchemy logger
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.INFO if settings.SQLALCHEMY_ECHO else logging.WARNING)

    # Configure application logger
    app_logger = logging.getLogger(settings.APP_NAME)
    app_logger.setLevel(log_level)

    # Log startup message
    app.logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}, "
        f"environment={settings.ENVIRONMENT}"
    )


def log_request_info(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[int] = None,
) -> None:
    """Log HTTP request with structured metadata.

    Convenience function for logging HTTP requests with consistent format.
    Should be called from Flask after_request handler.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: Authenticated user ID (optional)

    Returns:
        None

    Example:
        >>> log_request_info("GET", "/api/users", 200, 45.2, user_id=123)
    """
    logger = logging.getLogger(__name__)

    extra: Dict[str, Any] = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
    }

    if user_id:
        extra["user_id"] = user_id

    if status_code >= 500:
        log_level = logging.ERROR
    elif status_code >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO

    logger.log(
        log_level,
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra=extra,
    )


def log_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log exception with optional context.

    Convenience function for logging exceptions with structured metadata.
    Automatically includes exception type, message, and stack trace.

    Args:
        exception: Exception to log
        context: Additional context dictionary (optional)

    Returns:
        None

    Example:
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     log_exception(e, {"user_id": 123, "operation": "update_profile"})
    """
    logger = logging.getLogger(__name__)

    extra = context or {}
    extra["exception_type"] = type(exception).__name__

    logger.exception(
        f"Unhandled exception: {str(exception)}",
        exc_info=exception,
        extra=extra,
    )
