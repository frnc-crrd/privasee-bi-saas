"""
Unit tests for email service module.

This module contains comprehensive tests for transactional email
functionality using Flask-Mail.

Test Coverage:
    - Password reset email delivery
    - Welcome email delivery
    - Test email for SMTP configuration
    - Template rendering (HTML and plain text)
    - Error handling and logging
    - Mail service integration

Business Value:
    - Secure password recovery
    - User onboarding communication
    - Email infrastructure validation
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from app.services.email_service import EmailService


class TestPasswordResetEmail:
    """Tests for password reset email delivery."""

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_password_reset_email_success(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test successful password reset email delivery.

        Verifies that password reset email is sent with correct
        token and expiry information.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Templates rendered with correct parameters
            - Email message created with correct subject and recipients
            - Mail service called to send email
            - Success logged
            - Returns True
        """
        # Arrange
        mock_render.side_effect = [
            '<html>Reset token: test-token</html>',  # HTML template
            'Reset token: test-token'  # Plain text template
        ]
        mock_mail.send = Mock()

        # Act
        result = EmailService.send_password_reset_email(
            recipient_email='user@example.com',
            reset_token='test-token-123',
            expiry_minutes=30
        )

        # Assert
        assert result is True

        # Verify HTML template rendered
        assert mock_render.call_count == 2
        html_call = mock_render.call_args_list[0]
        assert html_call[0][0] == 'email/password_reset.html'
        assert html_call[1]['reset_token'] == 'test-token-123'
        assert html_call[1]['expiry_minutes'] == 30
        assert html_call[1]['recipient_email'] == 'user@example.com'

        # Verify plain text template rendered
        text_call = mock_render.call_args_list[1]
        assert text_call[0][0] == 'email/password_reset.txt'
        assert text_call[1]['reset_token'] == 'test-token-123'

        # Verify email sent
        mock_mail.send.assert_called_once()
        msg = mock_mail.send.call_args[0][0]
        assert msg.subject == 'Password Reset Request - Privasee BI'
        assert msg.recipients == ['user@example.com']

        # Verify success logged
        mock_app.logger.info.assert_called_once()

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_password_reset_email_default_expiry(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test password reset email with default expiry time.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Default expiry of 60 minutes used
            - Email sent successfully
        """
        # Arrange
        mock_render.side_effect = ['<html>Reset</html>', 'Reset']

        # Act
        result = EmailService.send_password_reset_email(
            recipient_email='user@example.com',
            reset_token='token-456'
        )

        # Assert
        assert result is True
        html_call = mock_render.call_args_list[0]
        assert html_call[1]['expiry_minutes'] == 60

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_password_reset_email_template_error(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test error handling when template rendering fails.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Exception caught and logged
            - Returns False on failure
        """
        # Arrange
        mock_render.side_effect = Exception("Template not found")

        # Act
        result = EmailService.send_password_reset_email(
            recipient_email='user@example.com',
            reset_token='token-789'
        )

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'Failed to send password reset email' in error_msg
        assert 'user@example.com' in error_msg

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_password_reset_email_smtp_error(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test error handling when SMTP delivery fails.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Templates rendered successfully
            - SMTP error caught and logged
            - Returns False
        """
        # Arrange
        mock_render.side_effect = ['<html>Reset</html>', 'Reset']
        mock_mail.send.side_effect = Exception("SMTP connection failed")

        # Act
        result = EmailService.send_password_reset_email(
            recipient_email='user@example.com',
            reset_token='token-abc'
        )

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'SMTP connection failed' in error_msg


class TestWelcomeEmail:
    """Tests for welcome email delivery."""

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_welcome_email_success(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test successful welcome email delivery.

        Verifies that new users receive a welcome email
        with personalized content.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Templates rendered with username
            - Email sent with correct subject
            - Success logged
            - Returns True
        """
        # Arrange
        mock_render.side_effect = [
            '<html>Welcome, John</html>',
            'Welcome, John'
        ]

        # Act
        result = EmailService.send_welcome_email(
            recipient_email='john@example.com',
            username='John Doe'
        )

        # Assert
        assert result is True

        # Verify templates rendered
        assert mock_render.call_count == 2
        html_call = mock_render.call_args_list[0]
        assert html_call[0][0] == 'email/welcome.html'
        assert html_call[1]['username'] == 'John Doe'

        text_call = mock_render.call_args_list[1]
        assert text_call[0][0] == 'email/welcome.txt'
        assert text_call[1]['username'] == 'John Doe'

        # Verify email sent
        mock_mail.send.assert_called_once()
        msg = mock_mail.send.call_args[0][0]
        assert msg.subject == 'Welcome to Privasee BI'
        assert msg.recipients == ['john@example.com']

        # Verify success logged
        mock_app.logger.info.assert_called_once()

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.current_app')
    def test_send_welcome_email_error(
        self,
        mock_app,
        mock_render,
        mock_mail
    ):
        """Test error handling in welcome email delivery.

        Args:
            mock_app: Mocked Flask application
            mock_render: Mocked template renderer
            mock_mail: Mocked mail service

        Assertions:
            - Exception caught and logged
            - Returns False on failure
        """
        # Arrange
        mock_mail.send.side_effect = Exception("Network timeout")

        # Act
        result = EmailService.send_welcome_email(
            recipient_email='jane@example.com',
            username='Jane Smith'
        )

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'Failed to send welcome email' in error_msg
        assert 'jane@example.com' in error_msg


class TestEmailConfiguration:
    """Tests for email configuration validation."""

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.current_app')
    def test_send_test_email_success(
        self,
        mock_app,
        mock_mail
    ):
        """Test SMTP configuration validation email.

        Verifies that test emails can be sent to validate
        email infrastructure setup.

        Args:
            mock_app: Mocked Flask application
            mock_mail: Mocked mail service

        Assertions:
            - Test message created with correct content
            - Email sent successfully
            - Success logged
            - Returns True
        """
        # Arrange
        mock_mail.send = Mock()

        # Act
        result = EmailService.send_test_email(
            recipient_email='admin@example.com'
        )

        # Assert
        assert result is True

        # Verify email sent
        mock_mail.send.assert_called_once()
        msg = mock_mail.send.call_args[0][0]
        assert msg.subject == 'Privasee BI - Email Configuration Test'
        assert msg.recipients == ['admin@example.com']
        assert 'test email' in msg.body.lower()
        assert 'test email' in msg.html.lower()

        # Verify success logged
        mock_app.logger.info.assert_called_once()

    @patch('app.services.email_service.mail')
    @patch('app.services.email_service.current_app')
    def test_send_test_email_error(
        self,
        mock_app,
        mock_mail
    ):
        """Test error handling in test email delivery.

        Args:
            mock_app: Mocked Flask application
            mock_mail: Mocked mail service

        Assertions:
            - SMTP error caught and logged
            - Returns False
        """
        # Arrange
        mock_mail.send.side_effect = Exception("Authentication failed")

        # Act
        result = EmailService.send_test_email(
            recipient_email='admin@example.com'
        )

        # Assert
        assert result is False
        mock_app.logger.error.assert_called_once()
        error_msg = mock_app.logger.error.call_args[0][0]
        assert 'Failed to send test email' in error_msg
        assert 'admin@example.com' in error_msg
        assert 'Authentication failed' in error_msg
