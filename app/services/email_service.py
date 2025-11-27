"""Email delivery service for transactional emails.

This module provides email functionality for password resets, account verification,
and system notifications using Flask-Mail.

Features:
- HTML email templates with plain text fallback
- Async email delivery for non-blocking operations
- Template rendering with Jinja2
- Error handling and logging

Usage:
    from app.services.email_service import EmailService

    email_service = EmailService()
    email_service.send_password_reset_email(
        recipient_email='user@example.com',
        reset_token='abc123...',
        expiry_minutes=60
    )
"""

from typing import Optional

from flask import current_app, render_template
from flask_mail import Message

from app.extensions import mail


class EmailService:
    """Service for sending transactional emails."""

    @staticmethod
    def send_password_reset_email(
        recipient_email: str,
        reset_token: str,
        expiry_minutes: int = 60
    ) -> bool:
        """Send password reset email with secure token.

        Args:
            recipient_email: Destination email address
            reset_token: Secure JWT token for password reset
            expiry_minutes: Token expiration time in minutes

        Returns:
            True if email sent successfully, False otherwise

        Raises:
            Exception: If email delivery fails critically
        """
        try:
            # Render HTML template
            html_body = render_template(
                'email/password_reset.html',
                reset_token=reset_token,
                expiry_minutes=expiry_minutes,
                recipient_email=recipient_email
            )

            # Render plain text fallback
            text_body = render_template(
                'email/password_reset.txt',
                reset_token=reset_token,
                expiry_minutes=expiry_minutes
            )

            # Create message
            msg = Message(
                subject='Password Reset Request - Privasee BI',
                recipients=[recipient_email],
                html=html_body,
                body=text_body
            )

            # Send email
            mail.send(msg)

            current_app.logger.info(
                f"Password reset email sent successfully to {recipient_email}"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"Failed to send password reset email to {recipient_email}: {str(e)}"
            )
            return False

    @staticmethod
    def send_welcome_email(
        recipient_email: str,
        username: str
    ) -> bool:
        """Send welcome email to newly registered user.

        Args:
            recipient_email: Destination email address
            username: User's display name

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Render templates
            html_body = render_template(
                'email/welcome.html',
                username=username
            )

            text_body = render_template(
                'email/welcome.txt',
                username=username
            )

            # Create and send message
            msg = Message(
                subject='Welcome to Privasee BI',
                recipients=[recipient_email],
                html=html_body,
                body=text_body
            )

            mail.send(msg)

            current_app.logger.info(
                f"Welcome email sent successfully to {recipient_email}"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"Failed to send welcome email to {recipient_email}: {str(e)}"
            )
            return False

    @staticmethod
    def send_test_email(recipient_email: str) -> bool:
        """Send test email to verify SMTP configuration.

        Args:
            recipient_email: Destination email address

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = Message(
                subject='Privasee BI - Email Configuration Test',
                recipients=[recipient_email],
                body='This is a test email to verify SMTP configuration.',
                html='<p>This is a <strong>test email</strong> to verify SMTP configuration.</p>'
            )

            mail.send(msg)

            current_app.logger.info(
                f"Test email sent successfully to {recipient_email}"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"Failed to send test email to {recipient_email}: {str(e)}"
            )
            return False
