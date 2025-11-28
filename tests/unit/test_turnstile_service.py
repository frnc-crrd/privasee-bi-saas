"""
Unit tests for Cloudflare Turnstile service module.

This module contains comprehensive tests for bot protection using
Cloudflare Turnstile challenge verification.

Test Coverage:
    - Turnstile enablement configuration
    - Token verification with Cloudflare API
    - Real IP address extraction from proxy headers
    - Error handling (timeout, request failures, parsing errors)
    - Detailed verification debugging
    - Security logging

Business Value:
    - Bot attack prevention
    - Automated abuse mitigation
    - User experience optimization (invisible CAPTCHA)
"""

from unittest.mock import Mock, patch, MagicMock
from flask import Flask

import pytest
import requests

from app.services.turnstile_service import TurnstileService


class TestTurnstileEnablement:
    """Tests for Turnstile service enablement configuration."""

    @patch('app.services.turnstile_service.get_settings')
    def test_is_enabled_when_turnstile_enabled(self, mock_get_settings):
        """Test Turnstile is reported as enabled in production.

        Args:
            mock_get_settings: Mocked settings provider

        Assertions:
            - Returns True when TURNSTILE_ENABLED is True
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_get_settings.return_value = mock_settings

        # Act
        result = TurnstileService.is_enabled()

        # Assert
        assert result is True

    @patch('app.services.turnstile_service.get_settings')
    def test_is_enabled_when_turnstile_disabled(self, mock_get_settings):
        """Test Turnstile is reported as disabled in development.

        Args:
            mock_get_settings: Mocked settings provider

        Assertions:
            - Returns False when TURNSTILE_ENABLED is False
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = False
        mock_get_settings.return_value = mock_settings

        # Act
        result = TurnstileService.is_enabled()

        # Assert
        assert result is False


class TestTokenVerification:
    """Tests for Turnstile token verification with Cloudflare API."""

    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_when_disabled_returns_true(
        self,
        mock_app,
        mock_get_settings
    ):
        """Test token verification bypassed when Turnstile disabled.

        Security consideration: In development mode, allow requests
        through without verification to simplify testing.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider

        Assertions:
            - Returns True when TURNSTILE_ENABLED is False
            - Debug message logged
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = False
        mock_get_settings.return_value = mock_settings

        # Act
        result = TurnstileService.verify_token('any-token')

        # Assert
        assert result is True
        mock_app.logger.debug.assert_called_once()

    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_missing_token_returns_false(
        self,
        mock_app,
        mock_get_settings
    ):
        """Test verification fails when token is missing.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider

        Assertions:
            - Returns False when token is None
            - Warning logged
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_get_settings.return_value = mock_settings

        # Act
        result = TurnstileService.verify_token(None)

        # Assert
        assert result is False
        mock_app.logger.warning.assert_called_once()
        warning_msg = mock_app.logger.warning.call_args[0][0]
        assert 'missing' in warning_msg.lower()

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_success_with_valid_token(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test successful token verification with Cloudflare API.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - API called with correct payload
            - Returns True on successful verification
            - Success logged with IP address
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '192.168.1.100'

        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_requests_post.return_value = mock_response

        # Act
        result = TurnstileService.verify_token('valid-token-123')

        # Assert
        assert result is True

        # Verify API called correctly
        mock_requests_post.assert_called_once_with(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': 'test-secret',
                'response': 'valid-token-123',
                'remoteip': '192.168.1.100'
            },
            timeout=5
        )

        # Verify success logged
        mock_app.logger.info.assert_called_once()
        info_msg = mock_app.logger.info.call_args[0][0]
        assert 'succeeded' in info_msg.lower()
        assert '192.168.1.100' in info_msg

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_failure_with_error_codes(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test verification failure with error codes from Cloudflare.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Returns False when success is False
            - Error codes logged for debugging
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '10.0.0.1'

        mock_response = Mock()
        mock_response.json.return_value = {
            'success': False,
            'error-codes': ['invalid-input-response', 'timeout-or-duplicate']
        }
        mock_requests_post.return_value = mock_response

        # Act
        result = TurnstileService.verify_token('invalid-token')

        # Assert
        assert result is False

        # Verify error logged with codes
        mock_app.logger.warning.assert_called_once()
        warning_msg = mock_app.logger.warning.call_args[0][0]
        assert 'failed' in warning_msg.lower()
        assert 'invalid-input-response' in warning_msg

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_timeout_error(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test verification failure on timeout.

        Security consideration: Fail closed (reject) on timeout
        to prevent bypass attacks.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Returns False on timeout
            - Timeout logged with configured timeout value
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '172.16.0.1'

        mock_requests_post.side_effect = requests.exceptions.Timeout("Connection timeout")

        # Act
        result = TurnstileService.verify_token('token-123')

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'timeout' in error_msg.lower()

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_request_exception(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test verification failure on request exception.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Returns False on request error
            - Error logged
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '203.0.113.1'

        mock_requests_post.side_effect = requests.exceptions.RequestException("Network error")

        # Act
        result = TurnstileService.verify_token('token-456')

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_json_parsing_error(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test verification failure on JSON parsing error.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Returns False when response.json() raises ValueError
            - Error logged
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '198.51.100.1'

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_requests_post.return_value = mock_response

        # Act
        result = TurnstileService.verify_token('token-789')

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'parsing failed' in error_msg.lower()

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    @patch('app.services.turnstile_service.current_app')
    def test_verify_token_with_explicit_remote_ip(
        self,
        mock_app,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test token verification with explicitly provided IP.

        Args:
            mock_app: Mocked Flask application
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Explicit IP used instead of extracting from request
            - _get_real_ip not called
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_requests_post.return_value = mock_response

        # Act
        result = TurnstileService.verify_token(
            'token-explicit',
            remote_ip='203.0.113.50'
        )

        # Assert
        assert result is True
        mock_get_real_ip.assert_not_called()

        # Verify explicit IP used in API call
        call_data = mock_requests_post.call_args[1]['data']
        assert call_data['remoteip'] == '203.0.113.50'


class TestRealIPExtraction:
    """Tests for real client IP extraction from proxy headers."""

    def test_get_real_ip_from_x_real_ip_header(self):
        """Test IP extraction from X-Real-IP header (priority 1).

        Args:
            None (uses Flask test request context)

        Assertions:
            - X-Real-IP header takes precedence
            - Other headers ignored when X-Real-IP present
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            headers={
                'X-Real-IP': '192.0.2.100',
                'X-Forwarded-For': '203.0.113.1, 198.51.100.2'
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            # Act
            result = TurnstileService._get_real_ip()

            # Assert
            assert result == '192.0.2.100'

    def test_get_real_ip_from_x_forwarded_for_header(self):
        """Test IP extraction from X-Forwarded-For header (priority 2).

        Args:
            None (uses Flask test request context)

        Assertions:
            - First IP in X-Forwarded-For used
            - Whitespace stripped correctly
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            headers={
                'X-Forwarded-For': '203.0.113.50, 198.51.100.1, 192.0.2.1'
            },
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            # Act
            result = TurnstileService._get_real_ip()

            # Assert
            assert result == '203.0.113.50'

    def test_get_real_ip_from_remote_addr(self):
        """Test IP extraction from remote_addr fallback (priority 3).

        Args:
            None (uses Flask test request context)

        Assertions:
            - request.remote_addr used when no proxy headers
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context(
            '/',
            environ_base={'REMOTE_ADDR': '198.51.100.75'}
        ):
            # Act
            result = TurnstileService._get_real_ip()

            # Assert
            assert result == '198.51.100.75'

    def test_get_real_ip_fallback_to_default(self):
        """Test fallback when no IP available.

        Args:
            None (uses Flask test request context)

        Assertions:
            - Returns 0.0.0.0 when remote_addr is None
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/'):
            # Act
            result = TurnstileService._get_real_ip()

            # Assert
            assert result == '0.0.0.0'


class TestVerificationDetails:
    """Tests for detailed verification debugging."""

    @patch('app.services.turnstile_service.get_settings')
    def test_get_verification_details_when_disabled(self, mock_get_settings):
        """Test detailed verification when Turnstile disabled.

        Args:
            mock_get_settings: Mocked settings provider

        Assertions:
            - Returns success with development mode message
            - No API call made
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = False
        mock_get_settings.return_value = mock_settings

        # Act
        result = TurnstileService.get_verification_details('any-token')

        # Assert
        assert result['success'] is True
        assert 'disabled' in result['message'].lower()

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    def test_get_verification_details_success(
        self,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test detailed verification with successful response.

        Args:
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Full verification details returned
            - Challenge metadata included
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '192.0.2.1'

        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'challenge_ts': '2024-01-15T10:30:00Z',
            'hostname': 'example.com',
            'action': 'login'
        }
        mock_requests_post.return_value = mock_response

        # Act
        result = TurnstileService.get_verification_details('debug-token')

        # Assert
        assert result['success'] is True
        assert result['challenge_ts'] == '2024-01-15T10:30:00Z'
        assert result['hostname'] == 'example.com'

    @patch('app.services.turnstile_service.requests.post')
    @patch('app.services.turnstile_service.TurnstileService._get_real_ip')
    @patch('app.services.turnstile_service.get_settings')
    def test_get_verification_details_request_failure(
        self,
        mock_get_settings,
        mock_get_real_ip,
        mock_requests_post
    ):
        """Test detailed verification with request failure.

        Args:
            mock_get_settings: Mocked settings provider
            mock_get_real_ip: Mocked IP extraction
            mock_requests_post: Mocked HTTP client

        Assertions:
            - Returns error details on request failure
            - Error message included
        """
        # Arrange
        mock_settings = Mock()
        mock_settings.TURNSTILE_ENABLED = True
        mock_settings.TURNSTILE_SECRET_KEY = 'test-secret'
        mock_settings.TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        mock_settings.TURNSTILE_TIMEOUT = 5
        mock_get_settings.return_value = mock_settings

        mock_get_real_ip.return_value = '192.0.2.1'

        mock_requests_post.side_effect = requests.exceptions.RequestException("Connection failed")

        # Act
        result = TurnstileService.get_verification_details('failing-token')

        # Assert
        assert result['success'] is False
        assert 'request-failed' in result['error-codes']
        assert 'Connection failed' in result['message']
