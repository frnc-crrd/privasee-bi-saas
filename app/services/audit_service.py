# app/services/audit_service.py
"""
Audit Service
-------------
Centralized service for logging security-relevant events to the audit trail.
Provides high-level methods for common audit scenarios and automatic request
context capture.
"""

import json
from typing import Any, Dict, Optional

from flask import Request, g, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import AuditEventType, AuditLog, AuditSeverity


class AuditService:
    """
    Audit Service for security event logging.

    Provides methods to log authentication, authorization, and data access
    events with automatic request context capture (IP, user agent, endpoint).

    Usage:
        # Automatic context capture from Flask request
        AuditService.log_login(user_id=1, username="admin")

        # Custom event with details
        AuditService.log_event(
            event_type=AuditEventType.DATA_EXPORT,
            severity=AuditSeverity.WARNING,
            user_id=1,
            details={"table": "users", "rows": 1000}
        )
    """

    @staticmethod
    def _get_request_context(req: Optional[Request] = None) -> Dict[str, Optional[str]]:
        """
        Extract request context for audit logging.

        Args:
            req: Flask request object (defaults to current request)

        Returns:
            Dictionary with ip_address, user_agent, endpoint, method
        """
        if req is None:
            req = request

        # Extract real IP (considering reverse proxy headers)
        ip_address = (
            req.headers.get("X-Real-IP")
            or req.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or req.remote_addr
        )

        return {
            "ip_address": ip_address,
            "user_agent": req.headers.get("User-Agent"),
            "endpoint": req.endpoint,
            "method": req.method,
        }

    @staticmethod
    def log_event(
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log a security event to the audit trail.

        Args:
            event_type: Type of security event
            severity: Event severity level (default: INFO)
            user_id: User ID who triggered the event
            username: Username at event time
            status_code: HTTP response status code
            details: Dictionary with event-specific metadata
            req: Flask request object (defaults to current request)

        Returns:
            True if event was logged successfully, False otherwise

        Note:
            Database errors are caught and logged to prevent audit failures
            from disrupting application flow. However, this means audit logs
            are best-effort only.
        """
        try:
            # Get request context
            context = AuditService._get_request_context(req)

            # Serialize details as JSON
            details_json = json.dumps(details) if details else None

            # Create audit log entry
            audit_log = AuditLog(
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                username=username,
                ip_address=context["ip_address"],
                user_agent=context["user_agent"],
                endpoint=context["endpoint"],
                method=context["method"],
                status_code=status_code,
                details=details_json,
            )

            db.session.add(audit_log)
            db.session.commit()
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            # Log to application logger (avoid circular dependency)
            print(f"[AUDIT ERROR] Failed to log {event_type.value}: {str(e)}")
            return False

    # =========================================================================
    # Authentication Events
    # =========================================================================

    @staticmethod
    def log_login(
        user_id: int,
        username: str,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log successful user login.

        Args:
            user_id: User ID who logged in
            username: Username of logged in user
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully
        """
        return AuditService.log_event(
            event_type=AuditEventType.LOGIN,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            req=req,
        )

    @staticmethod
    def log_logout(
        user_id: int,
        username: str,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log user logout.

        Args:
            user_id: User ID who logged out
            username: Username of logged out user
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully
        """
        return AuditService.log_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            req=req,
        )

    @staticmethod
    def log_login_failed(
        username: Optional[str] = None,
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log failed login attempt.

        Args:
            username: Username that attempted login (if known)
            status_code: HTTP status code (default: 401)
            details: Additional details (e.g., reason for failure)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Security:
            Failed login attempts are logged with WARNING severity for
            detection of brute force attacks and credential stuffing.
        """
        return AuditService.log_event(
            event_type=AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.WARNING,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    @staticmethod
    def log_password_change(
        user_id: int,
        username: str,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log password change event.

        Args:
            user_id: User ID who changed password
            username: Username of user
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully
        """
        return AuditService.log_event(
            event_type=AuditEventType.PASSWORD_CHANGE,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            req=req,
        )

    @staticmethod
    def log_password_reset(
        user_id: int,
        username: str,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log password reset event.

        Args:
            user_id: User ID who reset password
            username: Username of user
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Security:
            Password resets are logged with INFO severity but should be
            monitored for unauthorized account takeover attempts.
        """
        return AuditService.log_event(
            event_type=AuditEventType.PASSWORD_RESET,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            req=req,
        )

    # =========================================================================
    # Authorization Events
    # =========================================================================

    @staticmethod
    def log_role_change(
        user_id: int,
        username: str,
        details: Dict[str, Any],
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log user role change event.

        Args:
            user_id: User ID whose role changed
            username: Username of user
            details: Dictionary with old_role and new_role
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Example:
            AuditService.log_role_change(
                user_id=5,
                username="analyst1",
                details={"old_role": "viewer", "new_role": "analyst"}
            )
        """
        return AuditService.log_event(
            event_type=AuditEventType.ROLE_CHANGE,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    @staticmethod
    def log_permission_denied(
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 403,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log permission denied event.

        Args:
            user_id: User ID who was denied access
            username: Username of user
            details: Dictionary with required_role and user_role
            status_code: HTTP status code (default: 403)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Security:
            Permission denials are logged with WARNING severity to detect
            privilege escalation attempts.
        """
        return AuditService.log_event(
            event_type=AuditEventType.PERMISSION_DENIED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    # =========================================================================
    # Account Management Events
    # =========================================================================

    @staticmethod
    def log_user_created(
        user_id: int,
        username: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 201,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log user creation event.

        Args:
            user_id: ID of newly created user
            username: Username of new user
            details: Dictionary with role and created_by
            status_code: HTTP status code (default: 201)
            req: Flask request object (optional)

        Returns:
            True if logged successfully
        """
        return AuditService.log_event(
            event_type=AuditEventType.USER_CREATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    @staticmethod
    def log_user_deleted(
        user_id: int,
        username: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log user deletion event.

        Args:
            user_id: ID of deleted user
            username: Username of deleted user
            details: Dictionary with deleted_by
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Security:
            User deletions are logged with INFO severity but should be
            reviewed for unauthorized account removals.
        """
        return AuditService.log_event(
            event_type=AuditEventType.USER_DELETED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    @staticmethod
    def log_account_disabled(
        user_id: int,
        username: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log account disable event.

        Args:
            user_id: User ID whose account was disabled
            username: Username of user
            details: Dictionary with reason and disabled_by
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully
        """
        return AuditService.log_event(
            event_type=AuditEventType.ACCOUNT_DISABLED,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )

    # =========================================================================
    # Data Access Events
    # =========================================================================

    @staticmethod
    def log_data_export(
        user_id: int,
        username: str,
        details: Dict[str, Any],
        status_code: int = 200,
        req: Optional[Request] = None,
    ) -> bool:
        """
        Log data export event.

        Args:
            user_id: User ID who exported data
            username: Username of user
            details: Dictionary with table, rows, format
            status_code: HTTP status code (default: 200)
            req: Flask request object (optional)

        Returns:
            True if logged successfully

        Example:
            AuditService.log_data_export(
                user_id=3,
                username="analyst",
                details={"table": "sales", "rows": 5000, "format": "csv"}
            )
        """
        return AuditService.log_event(
            event_type=AuditEventType.DATA_EXPORT,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            username=username,
            status_code=status_code,
            details=details,
            req=req,
        )
