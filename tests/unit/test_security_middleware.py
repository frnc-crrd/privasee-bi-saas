"""
Unit tests for security middleware module.

This module contains comprehensive tests for HTTP security headers,
request tracking, and input validation.

Test Coverage:
    - Security header application
    - Request context tracking (X-Request-ID)
    - Request and response logging
    - Content-Type validation decorator
    - CORS configuration
    - Input sanitization
    - Security configuration constants

Business Value:
    - Ensures security headers protect against common attacks
    - Validates request tracking for debugging
    - Confirms input sanitization prevents injection
"""

from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest
from flask import Flask, Response, g

from app.middleware.security_middleware import (
    apply_security_headers,
    track_request_context,
    log_request_info,
    log_response_info,
    validate_content_type,
    cors_config,
    sanitize_input,
    SecurityConfig,
)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['DEBUG'] = False
    return app


@pytest.fixture
def app_debug():
    """Create Flask app in debug mode."""
    app = Flask(__name__)
    app.config['DEBUG'] = True
    return app


class TestSecurityHeaders:
    """Tests for security header application."""

    def test_apply_security_headers_all_headers_present(self, app):
        """Test all security headers are applied.

        Args:
            app: Flask application fixture

        Assertions:
            - All required security headers present
            - Header values are correct
        """
        with app.app_context():
            response = Response("test")
            response = apply_security_headers(response)

            assert response.headers['X-Content-Type-Options'] == 'nosniff'
            assert response.headers['X-Frame-Options'] == 'DENY'
            assert response.headers['X-XSS-Protection'] == '1; mode=block'
            assert 'Content-Security-Policy' in response.headers
            assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
            assert 'Permissions-Policy' in response.headers

    def test_apply_security_headers_hsts_in_production(self, app):
        """Test HSTS header applied in production mode.

        Args:
            app: Flask application fixture

        Assertions:
            - HSTS header present when DEBUG=False
        """
        with app.app_context():
            response = Response("test")
            response = apply_security_headers(response)

            assert 'Strict-Transport-Security' in response.headers
            assert 'max-age=31536000' in response.headers['Strict-Transport-Security']
            assert 'includeSubDomains' in response.headers['Strict-Transport-Security']

    def test_apply_security_headers_no_hsts_in_debug(self, app_debug):
        """Test HSTS header not applied in debug mode.

        Args:
            app_debug: Flask application in debug mode

        Assertions:
            - HSTS header not present when DEBUG=True
        """
        with app_debug.app_context():
            response = Response("test")
            response = apply_security_headers(response)

            assert 'Strict-Transport-Security' not in response.headers

    def test_apply_security_headers_csp_policy(self, app):
        """Test Content Security Policy header content.

        Args:
            app: Flask application fixture

        Assertions:
            - CSP policy includes expected directives
        """
        with app.app_context():
            response = Response("test")
            response = apply_security_headers(response)

            csp = response.headers['Content-Security-Policy']
            assert "default-src 'self'" in csp
            assert "frame-ancestors 'none'" in csp

    def test_apply_security_headers_permissions_policy(self, app):
        """Test Permissions Policy header content.

        Args:
            app: Flask application fixture

        Assertions:
            - Permissions policy restricts sensitive features
        """
        with app.app_context():
            response = Response("test")
            response = apply_security_headers(response)

            permissions = response.headers['Permissions-Policy']
            assert 'geolocation=()' in permissions
            assert 'microphone=()' in permissions
            assert 'camera=()' in permissions


class TestRequestTracking:
    """Tests for request context tracking."""

    def test_track_request_context_generates_request_id(self, app):
        """Test request ID generation when not provided.

        Args:
            app: Flask application fixture

        Assertions:
            - Request ID generated and stored in g
            - Request metadata stored
        """
        with app.test_request_context('/test', method='GET'):
            track_request_context()

            assert hasattr(g, 'request_id')
            assert isinstance(g.request_id, str)
            assert len(g.request_id) > 0
            assert hasattr(g, 'request_start_time')
            assert hasattr(g, 'request_method')
            assert g.request_method == 'GET'
            assert hasattr(g, 'request_path')
            assert g.request_path == '/test'

    def test_track_request_context_preserves_client_request_id(self, app):
        """Test client-provided request ID is preserved.

        Args:
            app: Flask application fixture

        Assertions:
            - Client request ID used instead of generating new one
        """
        client_request_id = 'custom-request-id-12345'
        with app.test_request_context(
            '/test',
            headers={'X-Request-ID': client_request_id}
        ):
            track_request_context()

            assert g.request_id == client_request_id

    def test_track_request_context_stores_metadata(self, app):
        """Test request metadata is correctly stored.

        Args:
            app: Flask application fixture

        Assertions:
            - Start time is datetime object
            - Method and path match request
        """
        with app.test_request_context('/api/users', method='POST'):
            track_request_context()

            assert isinstance(g.request_start_time, datetime)
            assert g.request_method == 'POST'
            assert g.request_path == '/api/users'


class TestRequestLogging:
    """Tests for request and response logging."""

    @patch('app.middleware.security_middleware.current_app')
    def test_log_request_info_logs_correct_data(self, mock_app, app):
        """Test request information is logged correctly.

        Args:
            mock_app: Mocked Flask application
            app: Flask application fixture

        Assertions:
            - Logger called with request details
            - Log includes method, path, IP, request ID
        """
        with app.test_request_context(
            '/api/test',
            method='GET',
            environ_base={'REMOTE_ADDR': '192.168.1.1'},
            headers={'User-Agent': 'TestAgent/1.0'}
        ):
            g.request_id = 'test-request-123'

            log_request_info()

            mock_app.logger.info.assert_called_once()
            log_message = mock_app.logger.info.call_args[0][0]
            assert 'GET' in log_message
            assert '/api/test' in log_message
            assert '192.168.1.1' in log_message
            assert 'test-request-123' in log_message
            assert 'TestAgent/1.0' in log_message

    @patch('app.middleware.security_middleware.current_app')
    def test_log_response_info_logs_status_and_timing(self, mock_app, app):
        """Test response information is logged with execution time.

        Args:
            mock_app: Mocked Flask application
            app: Flask application fixture

        Assertions:
            - Logger called with response details
            - Execution time calculated
            - Request ID added to response headers
        """
        with app.test_request_context('/test'):
            g.request_id = 'test-response-456'
            g.request_start_time = datetime.utcnow()

            response = Response("test", status=200)
            response = log_response_info(response)

            mock_app.logger.info.assert_called_once()
            log_message = mock_app.logger.info.call_args[0][0]
            assert '200' in log_message
            assert 'test-response-456' in log_message
            assert 'ms' in log_message

            assert response.headers['X-Request-ID'] == 'test-response-456'

    @patch('app.middleware.security_middleware.current_app')
    def test_log_response_info_handles_missing_start_time(self, mock_app, app):
        """Test response logging handles missing start time.

        Args:
            mock_app: Mocked Flask application
            app: Flask application fixture

        Assertions:
            - Execution time shows as unknown
            - No errors raised
        """
        with app.test_request_context('/test'):
            g.request_id = 'test-789'

            response = Response("test", status=200)
            response = log_response_info(response)

            log_message = mock_app.logger.info.call_args[0][0]
            assert 'unknown' in log_message


class TestContentTypeValidation:
    """Tests for content type validation decorator."""

    def test_validate_content_type_allows_json(self, app):
        """Test decorator allows JSON content type.

        Args:
            app: Flask application fixture

        Assertions:
            - Function executes for valid content type
        """
        @validate_content_type(['application/json'])
        def test_route():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            content_type='application/json'
        ):
            result = test_route()

            assert result == {'message': 'success'}

    def test_validate_content_type_rejects_invalid(self, app):
        """Test decorator rejects invalid content type.

        Args:
            app: Flask application fixture

        Assertions:
            - 415 status returned
            - Error message explains allowed types
        """
        @validate_content_type(['application/json'])
        def test_route():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            content_type='text/plain'
        ):
            result, status = test_route()

            assert status == 415
            assert 'error' in result
            assert 'Content-Type' in result['error']

    def test_validate_content_type_skips_get_requests(self, app):
        """Test decorator skips validation for GET requests.

        Args:
            app: Flask application fixture

        Assertions:
            - GET requests bypass content type check
        """
        @validate_content_type(['application/json'])
        def test_route():
            return {'message': 'success'}

        with app.test_request_context('/test', method='GET'):
            result = test_route()

            assert result == {'message': 'success'}

    def test_validate_content_type_default_allows_json(self, app):
        """Test decorator defaults to allowing JSON.

        Args:
            app: Flask application fixture

        Assertions:
            - JSON allowed when no types specified
        """
        @validate_content_type()
        def test_route():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            content_type='application/json'
        ):
            result = test_route()

            assert result == {'message': 'success'}


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_config_returns_dict(self):
        """Test CORS config returns dictionary.

        Assertions:
            - Returns dictionary
            - Contains required keys
        """
        config = cors_config()

        assert isinstance(config, dict)
        assert 'origins' in config
        assert 'methods' in config
        assert 'allow_headers' in config

    def test_cors_config_includes_localhost(self):
        """Test CORS config includes localhost origins.

        Assertions:
            - Localhost URLs present
            - Both ports 3000 and 5000 included
        """
        config = cors_config()

        assert 'http://localhost:3000' in config['origins']
        assert 'http://localhost:5000' in config['origins']

    def test_cors_config_includes_standard_methods(self):
        """Test CORS config includes standard HTTP methods.

        Assertions:
            - GET, POST, PUT, DELETE included
            - OPTIONS included for preflight
        """
        config = cors_config()

        assert 'GET' in config['methods']
        assert 'POST' in config['methods']
        assert 'PUT' in config['methods']
        assert 'DELETE' in config['methods']
        assert 'OPTIONS' in config['methods']

    def test_cors_config_allows_auth_headers(self):
        """Test CORS config allows Authorization header.

        Assertions:
            - Authorization in allowed headers
            - Content-Type in allowed headers
        """
        config = cors_config()

        assert 'Authorization' in config['allow_headers']
        assert 'Content-Type' in config['allow_headers']

    def test_cors_config_exposes_request_id(self):
        """Test CORS config exposes X-Request-ID header.

        Assertions:
            - X-Request-ID in exposed headers
        """
        config = cors_config()

        assert 'X-Request-ID' in config['expose_headers']

    def test_cors_config_supports_credentials(self):
        """Test CORS config supports credentials.

        Assertions:
            - supports_credentials is True
        """
        config = cors_config()

        assert config['supports_credentials'] is True


class TestInputSanitization:
    """Tests for input sanitization."""

    def test_sanitize_input_removes_null_bytes(self):
        """Test sanitization removes null bytes.

        Assertions:
            - Null bytes removed from string
        """
        dirty_input = "test\x00string"
        clean = sanitize_input(dirty_input)

        assert '\x00' not in clean
        assert clean == 'teststring'

    def test_sanitize_input_strips_whitespace(self):
        """Test sanitization strips leading/trailing whitespace.

        Assertions:
            - Whitespace removed from ends
        """
        dirty_input = "  test string  "
        clean = sanitize_input(dirty_input)

        assert clean == 'test string'

    def test_sanitize_input_enforces_max_length(self):
        """Test sanitization enforces maximum length.

        Assertions:
            - String truncated to max length
        """
        long_input = 'a' * 2000
        clean = sanitize_input(long_input, max_length=100)

        assert len(clean) == 100

    def test_sanitize_input_handles_empty_string(self):
        """Test sanitization handles empty string.

        Assertions:
            - Empty string returned for empty input
        """
        clean = sanitize_input("")

        assert clean == ''

    def test_sanitize_input_handles_none(self):
        """Test sanitization handles None input.

        Assertions:
            - Empty string returned for None
        """
        clean = sanitize_input(None)

        assert clean == ''

    def test_sanitize_input_preserves_valid_content(self):
        """Test sanitization preserves valid content.

        Assertions:
            - Valid content unchanged
        """
        valid_input = "Hello, World!"
        clean = sanitize_input(valid_input)

        assert clean == valid_input


class TestSecurityConfig:
    """Tests for security configuration class."""

    def test_security_config_max_content_length(self):
        """Test max content length constant.

        Assertions:
            - Constant defined
            - Reasonable size (16 MB)
        """
        assert SecurityConfig.MAX_CONTENT_LENGTH == 16 * 1024 * 1024

    def test_security_config_session_cookies_secure(self):
        """Test session cookie security settings.

        Assertions:
            - Secure flag enabled
            - HttpOnly flag enabled
            - SameSite set to Lax
        """
        assert SecurityConfig.SESSION_COOKIE_SECURE is True
        assert SecurityConfig.SESSION_COOKIE_HTTPONLY is True
        assert SecurityConfig.SESSION_COOKIE_SAMESITE == 'Lax'

    def test_security_config_jwt_expiration(self):
        """Test JWT token expiration settings.

        Assertions:
            - Access token expires in 1 hour
            - Refresh token expires in 7 days
        """
        assert SecurityConfig.JWT_ACCESS_TOKEN_EXPIRES == 3600
        assert SecurityConfig.JWT_REFRESH_TOKEN_EXPIRES == 604800

    def test_security_config_rate_limits(self):
        """Test rate limiting configuration.

        Assertions:
            - Default rate limit defined
            - Auth rate limit more restrictive
        """
        assert SecurityConfig.RATE_LIMIT_DEFAULT == '100/minute'
        assert SecurityConfig.RATE_LIMIT_AUTH == '5/minute'

    def test_security_config_allowed_extensions(self):
        """Test allowed file upload extensions.

        Assertions:
            - Common document types allowed
        """
        assert 'pdf' in SecurityConfig.ALLOWED_EXTENSIONS
        assert 'xlsx' in SecurityConfig.ALLOWED_EXTENSIONS
        assert 'csv' in SecurityConfig.ALLOWED_EXTENSIONS

    def test_is_safe_url_same_domain(self, app):
        """Test safe URL check for same domain.

        Args:
            app: Flask application fixture

        Assertions:
            - Same domain URLs are safe
        """
        with app.test_request_context('/', base_url='http://localhost:5000'):
            assert SecurityConfig.is_safe_url('/dashboard') is True
            assert SecurityConfig.is_safe_url('http://localhost:5000/users') is True

    def test_is_safe_url_different_domain(self, app):
        """Test safe URL check rejects different domains.

        Args:
            app: Flask application fixture

        Assertions:
            - Different domain URLs are unsafe
        """
        with app.test_request_context('/', base_url='http://localhost:5000'):
            assert SecurityConfig.is_safe_url('http://evil.com/phishing') is False

    def test_is_safe_url_relative_path(self, app):
        """Test safe URL check allows relative paths.

        Args:
            app: Flask application fixture

        Assertions:
            - Relative paths are safe
        """
        with app.test_request_context('/', base_url='http://localhost:5000'):
            assert SecurityConfig.is_safe_url('/api/users') is True
            assert SecurityConfig.is_safe_url('../admin') is True
