"""Prometheus metrics collection and monitoring."""

import time
from typing import Callable, Optional

from flask import Flask, Response, request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry
)
from werkzeug.wrappers import Response as WerkzeugResponse

# Create custom registry to avoid conflicts
registry = CollectorRegistry()

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint'],
    registry=registry
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=registry
)

# Authentication metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['status'],
    registry=registry
)

# Business metrics
active_users = Gauge(
    'active_users',
    'Number of currently active users',
    registry=registry
)

dashboard_views_total = Counter(
    'dashboard_views_total',
    'Total dashboard views',
    ['dashboard_name'],
    registry=registry
)


class MetricsMiddleware:
    """Middleware for collecting HTTP metrics."""

    def __init__(self, app: Optional[Flask] = None):
        """
        Initialize metrics middleware.

        Args:
            app: Flask application instance
        """
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """
        Initialize middleware with Flask app.

        Args:
            app: Flask application instance
        """
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        # Add metrics endpoint
        @app.route('/metrics')
        def metrics() -> Response:
            """
            Prometheus metrics endpoint.

            Returns:
                Prometheus formatted metrics
            """
            return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    def _before_request(self) -> None:
        """Record request start time and increment in-progress counter."""
        endpoint = request.endpoint or 'unknown'
        method = request.method

        # Increment in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Store start time for duration calculation
        request._prometheus_metrics_start_time = time.time()

    def _after_request(self, response: WerkzeugResponse) -> WerkzeugResponse:
        """
        Record request completion metrics.

        Args:
            response: Flask response object

        Returns:
            Unmodified response object
        """
        endpoint = request.endpoint or 'unknown'
        method = request.method
        status = response.status_code

        # Decrement in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

        # Increment total requests counter
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        # Record request duration
        if hasattr(request, '_prometheus_metrics_start_time'):
            duration = time.time() - request._prometheus_metrics_start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

        return response


def record_auth_attempt(success: bool) -> None:
    """
    Record authentication attempt.

    Args:
        success: Whether authentication was successful
    """
    status = 'success' if success else 'failure'
    auth_attempts_total.labels(status=status).inc()


def record_db_query(query_type: str, duration: float) -> None:
    """
    Record database query metrics.

    Args:
        query_type: Type of query (select, insert, update, delete)
        duration: Query duration in seconds
    """
    db_query_duration_seconds.labels(query_type=query_type).observe(duration)


def update_active_users(count: int) -> None:
    """
    Update active users gauge.

    Args:
        count: Number of currently active users
    """
    active_users.set(count)


def record_dashboard_view(dashboard_name: str) -> None:
    """
    Record dashboard view.

    Args:
        dashboard_name: Name of the dashboard viewed
    """
    dashboard_views_total.labels(dashboard_name=dashboard_name).inc()


def update_db_connections(count: int) -> None:
    """
    Update active database connections gauge.

    Args:
        count: Number of active connections
    """
    db_connections_active.set(count)
