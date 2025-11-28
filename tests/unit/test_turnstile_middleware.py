"""
Unit tests for Turnstile middleware module.

This module contains comprehensive tests for Cloudflare Turnstile
bot verification decorators.

Test Coverage:
    - Turnstile verification decorator
    - Token extraction from different locations (form, json, args)
    - Verification bypass when disabled
    - Verification failure handling
    - Convenience decorators
    - Error handling for invalid configurations

Business Value:
    - Ensures bot protection for sensitive endpoints
    - Validates token verification flow
    - Confirms graceful degradation when disabled
"""

from unittest.mock import patch

import pytest
from flask import Flask

from app.middleware.turnstile_middleware import (
    require_turnstile,
    require_turnstile_json,
    require_turnstile_form,
)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


class TestRequireTurnstile:
    """Tests for require_turnstile decorator."""

    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_bypass_when_disabled(self, mock_is_enabled, app):
        """Test decorator bypasses verification when Turnstile is disabled.

        Args:
            mock_is_enabled: Mocked is_enabled method
            app: Flask application fixture

        Assertions:
            - Function executes without verification
            - Turnstile service not called
        """
        mock_is_enabled.return_value = False

        @require_turnstile()
        def protected_endpoint():
            return {'message': 'success'}

        with app.test_request_context('/test', method='POST'):
            result = protected_endpoint()

            assert result == {'message': 'success'}
            mock_is_enabled.assert_called_once()

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_form_token_extraction_success(self, mock_is_enabled, mock_verify, app):
        """Test token extraction from form data.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Token extracted from form data
            - Verification called with correct token
            - Endpoint executes on success
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile(token_location='form')
        def protected_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            data={'cf-turnstile-response': 'valid-token'}
        ):
            result = protected_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('valid-token')

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_json_token_extraction_success(self, mock_is_enabled, mock_verify, app):
        """Test token extraction from JSON body.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Token extracted from JSON data
            - Verification called with correct token
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile(token_location='json')
        def protected_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            json={'cf-turnstile-response': 'json-token'}
        ):
            result = protected_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('json-token')

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_args_token_extraction_success(self, mock_is_enabled, mock_verify, app):
        """Test token extraction from query parameters.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Token extracted from URL args
            - Verification called with correct token
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile(token_location='args')
        def protected_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/test?cf-turnstile-response=args-token',
            method='GET'
        ):
            result = protected_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('args-token')

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_custom_token_param_name(self, mock_is_enabled, mock_verify, app):
        """Test custom token parameter name.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Custom parameter name used for extraction
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile(token_param='custom-token', token_location='json')
        def protected_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/test',
            method='POST',
            json={'custom-token': 'my-token'}
        ):
            result = protected_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('my-token')

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_verification_failure_returns_403(self, mock_is_enabled, mock_verify, app):
        """Test verification failure returns 403 error.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - 403 status returned on verification failure
            - Error message user-friendly
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = False

        @require_turnstile(token_location='json')
        def protected_endpoint():
            return {'message': 'should not reach'}

        with app.test_request_context(
            '/test',
            method='POST',
            json={'cf-turnstile-response': 'invalid-token'}
        ):
            response, status_code = protected_endpoint()

            assert status_code == 403
            assert 'Verification failed' in response.get_json()['error']['message']

    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_invalid_token_location_raises_error(self, mock_is_enabled, app):
        """Test invalid token_location parameter raises ValueError.

        Args:
            mock_is_enabled: Mocked is_enabled method
            app: Flask application fixture

        Assertions:
            - ValueError raised for invalid location
            - Error message describes valid options
        """
        mock_is_enabled.return_value = True

        @require_turnstile(token_location='invalid')
        def protected_endpoint():
            return {'message': 'should not reach'}

        with app.test_request_context('/test', method='POST'):
            with pytest.raises(ValueError) as exc_info:
                protected_endpoint()

            assert 'Invalid token_location' in str(exc_info.value)
            assert 'form' in str(exc_info.value)
            assert 'json' in str(exc_info.value)
            assert 'args' in str(exc_info.value)

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_missing_token_fails_verification(self, mock_is_enabled, mock_verify, app):
        """Test missing token results in verification failure.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - None passed to verification when token missing
            - Verification fails
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = False

        @require_turnstile(token_location='json')
        def protected_endpoint():
            return {'message': 'should not reach'}

        with app.test_request_context(
            '/test',
            method='POST',
            json={}
        ):
            response, status_code = protected_endpoint()

            assert status_code == 403
            mock_verify.assert_called_once_with(None)

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_json_extraction_handles_invalid_json(self, mock_is_enabled, mock_verify, app):
        """Test JSON extraction handles invalid/missing JSON gracefully.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Empty dict used when JSON is invalid
            - Verification called with None
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = False

        @require_turnstile(token_location='json')
        def protected_endpoint():
            return {'message': 'should not reach'}

        with app.test_request_context(
            '/test',
            method='POST',
            data='not valid json',
            content_type='application/json'
        ):
            response, status_code = protected_endpoint()

            assert status_code == 403
            mock_verify.assert_called_once_with(None)


class TestConvenienceDecorators:
    """Tests for convenience decorator shortcuts."""

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_require_turnstile_json_decorator(self, mock_is_enabled, mock_verify, app):
        """Test require_turnstile_json convenience decorator.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Extracts token from JSON automatically
            - Functions same as require_turnstile(token_location='json')
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile_json()
        def api_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/api/test',
            method='POST',
            json={'cf-turnstile-response': 'api-token'}
        ):
            result = api_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('api-token')

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_require_turnstile_form_decorator(self, mock_is_enabled, mock_verify, app):
        """Test require_turnstile_form convenience decorator.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Extracts token from form data automatically
            - Functions same as require_turnstile(token_location='form')
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile_form()
        def form_endpoint():
            return {'message': 'success'}

        with app.test_request_context(
            '/form/test',
            method='POST',
            data={'cf-turnstile-response': 'form-token'}
        ):
            result = form_endpoint()

            assert result == {'message': 'success'}
            mock_verify.assert_called_once_with('form-token')


class TestDecoratorIntegration:
    """Tests for decorator integration scenarios."""

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_decorator_preserves_function_metadata(self, mock_is_enabled, mock_verify, app):
        """Test decorator preserves original function metadata.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Function name preserved
            - Docstring preserved
        """
        mock_is_enabled.return_value = False

        @require_turnstile()
        def my_endpoint():
            """Original docstring."""
            return {'message': 'success'}

        assert my_endpoint.__name__ == 'my_endpoint'
        assert 'Original docstring' in my_endpoint.__doc__

    @patch('app.middleware.turnstile_middleware.TurnstileService.verify_token')
    @patch('app.middleware.turnstile_middleware.TurnstileService.is_enabled')
    def test_decorator_allows_endpoint_arguments(self, mock_is_enabled, mock_verify, app):
        """Test decorator works with endpoints that take arguments.

        Args:
            mock_is_enabled: Mocked is_enabled method
            mock_verify: Mocked verify_token method
            app: Flask application fixture

        Assertions:
            - Arguments passed through correctly
            - Both positional and keyword arguments supported
        """
        mock_is_enabled.return_value = True
        mock_verify.return_value = True

        @require_turnstile(token_location='json')
        def endpoint_with_args(user_id, action='view'):
            return {'user_id': user_id, 'action': action}

        with app.test_request_context(
            '/test',
            method='POST',
            json={'cf-turnstile-response': 'token'}
        ):
            result = endpoint_with_args(123, action='edit')

            assert result == {'user_id': 123, 'action': 'edit'}
