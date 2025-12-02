"""
Audit Log routes for querying security events.

Endpoints:
- GET /api/v1/audit/logs - List audit logs (with filters, pagination)
- GET /api/v1/audit/logs/<id> - Get specific audit log entry

Security:
- Admin users can view all audit logs
- Non-admin users can only view their own logs
"""

import json
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt
from sqlalchemy import and_, or_

from app.core.pagination import paginate_query
from app.core.responses import success_response, error_response
from app.middleware.auth_middleware import jwt_required_custom
from app.middleware.rbac_middleware import require_role
from app.models import AuditLog, AuditEventType, AuditSeverity
from app.extensions import db, cache


# Create blueprint
audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/logs', methods=['GET'])
@jwt_required_custom()
def get_audit_logs():
    """
    Query audit logs with advanced filtering, pagination, and role-based access control.
    ---
    tags:
      - Audit Logs
    summary: List audit logs
    description: |
      Retrieves security audit logs with comprehensive filtering capabilities. Audit logs track all
      security-relevant events including authentication, authorization, and data access operations.

      **Features:**
      - Comprehensive event tracking (login, logout, password changes, data access)
      - Multi-dimensional filtering (user, event type, severity, time range, IP address)
      - Pagination for large result sets
      - Role-based access control (admins see all, users see own logs)
      - Timestamp ordering (newest first)

      **Use Cases:**
      - Security incident investigation
      - Compliance auditing (SOC 2, HIPAA, GDPR)
      - User activity monitoring
      - Threat detection and analysis
      - Forensic investigation post-breach

      **Authorization Rules:**
      - Admin users: Can view all audit logs across all users
      - Non-admin users: Can only view their own audit logs (automatic filtering by user_id)

      **Event Types:**
      - login: User authentication events
      - logout: User logout events
      - password_change: Password modification
      - password_reset: Password reset operations
      - user_created: New user registration
      - user_updated: User profile modifications
      - user_deleted: User deactivation
      - permission_denied: Authorization failures
      - data_access: Sensitive data access

      **Severity Levels:**
      - info: Normal operations (successful login)
      - warning: Suspicious activity (failed login attempts)
      - critical: Security incidents (unauthorized access attempts)
    security:
      - Bearer: []
    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number (starts at 1)
        example: 1
      - in: query
        name: limit
        type: integer
        required: false
        default: 20
        description: Items per page (maximum 100)
        example: 20
      - in: query
        name: user_id
        type: integer
        required: false
        description: Filter by user ID (admin only - returns 403 for non-admins)
        example: 42
      - in: query
        name: event_type
        type: string
        required: false
        enum: [login, logout, password_change, password_reset, user_created, user_updated, user_deleted, permission_denied, data_access]
        description: Filter by event type
        example: "login"
      - in: query
        name: severity
        type: string
        required: false
        enum: [info, warning, critical]
        description: Filter by severity level
        example: "warning"
      - in: query
        name: start_date
        type: string
        format: date-time
        required: false
        description: Filter events after this timestamp (ISO 8601 format)
        example: "2024-01-01T00:00:00Z"
      - in: query
        name: end_date
        type: string
        format: date-time
        required: false
        description: Filter events before this timestamp (ISO 8601 format)
        example: "2024-12-31T23:59:59Z"
      - in: query
        name: ip_address
        type: string
        required: false
        description: Filter by source IP address
        example: "192.168.1.100"
    responses:
      200:
        description: Audit logs retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Retrieved 15 audit log(s)"
            data:
              type: object
              properties:
                logs:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                        example: 1234
                        description: Audit log entry ID
                      event_type:
                        type: string
                        example: "login"
                        description: Type of security event
                      severity:
                        type: string
                        example: "info"
                        description: Event severity level
                      user_id:
                        type: integer
                        example: 42
                        description: User who triggered the event
                      username:
                        type: string
                        example: "john.doe"
                        description: Username
                      ip_address:
                        type: string
                        example: "192.168.1.100"
                        description: Source IP address
                      user_agent:
                        type: string
                        example: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        description: Client user agent string
                      endpoint:
                        type: string
                        example: "/api/v1/auth/login"
                        description: API endpoint accessed
                      method:
                        type: string
                        example: "POST"
                        description: HTTP method
                      status_code:
                        type: integer
                        example: 200
                        description: HTTP response status code
                      details:
                        type: object
                        example: {"login_method": "email"}
                        description: Additional event-specific metadata (JSON)
                      timestamp:
                        type: string
                        format: date-time
                        example: "2024-03-15T14:30:00Z"
                        description: Event timestamp (ISO 8601)
                pagination:
                  type: object
                  properties:
                    page:
                      type: integer
                      example: 1
                    per_page:
                      type: integer
                      example: 20
                    total_items:
                      type: integer
                      example: 150
                    total_pages:
                      type: integer
                      example: 8
      400:
        description: Validation error (invalid event_type, severity, or date format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid event_type: invalid_type"
            details:
              type: object
              properties:
                valid_types:
                  type: array
                  items:
                    type: string
                  example: ["login", "logout", "password_change"]
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (non-admin trying to filter by user_id)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Only administrators can filter by user_id"
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve audit logs"
    """
    try:
        # Get current user info
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        current_user_role = claims.get('role', 'viewer')

        # Build base query
        query = AuditLog.query

        # Non-admin users can only see their own logs
        if current_user_role != 'admin':
            query = query.filter(AuditLog.user_id == current_user_id)

        # Apply filters
        filters = []

        # User ID filter (admin only)
        user_id_filter = request.args.get('user_id', type=int)
        if user_id_filter:
            if current_user_role != 'admin':
                return error_response(
                    message="Only administrators can filter by user_id",
                    status_code=403
                )
            filters.append(AuditLog.user_id == user_id_filter)

        # Event type filter
        event_type_filter = request.args.get('event_type')
        if event_type_filter:
            try:
                event_enum = AuditEventType(event_type_filter)
                filters.append(AuditLog.event_type == event_enum)
            except ValueError:
                return error_response(
                    message=f"Invalid event_type: {event_type_filter}",
                    details={"valid_types": [e.value for e in AuditEventType]},
                    status_code=400
                )

        # Severity filter
        severity_filter = request.args.get('severity')
        if severity_filter:
            try:
                severity_enum = AuditSeverity(severity_filter)
                filters.append(AuditLog.severity == severity_enum)
            except ValueError:
                return error_response(
                    message=f"Invalid severity: {severity_filter}",
                    details={"valid_severities": [s.value for s in AuditSeverity]},
                    status_code=400
                )

        # Date range filters
        start_date_str = request.args.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                filters.append(AuditLog.timestamp >= start_date)
            except ValueError:
                return error_response(
                    message="Invalid start_date format. Use ISO 8601 format.",
                    status_code=400
                )

        end_date_str = request.args.get('end_date')
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                filters.append(AuditLog.timestamp <= end_date)
            except ValueError:
                return error_response(
                    message="Invalid end_date format. Use ISO 8601 format.",
                    status_code=400
                )

        # IP address filter
        ip_filter = request.args.get('ip_address')
        if ip_filter:
            filters.append(AuditLog.ip_address == ip_filter)

        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))

        # Order by timestamp (newest first)
        query = query.order_by(AuditLog.timestamp.desc())

        # Pagination
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Cap at 100 items per page

        from app.core.pagination import PaginationParams
        pagination_params = PaginationParams(page=page, per_page=limit)
        items, pagination_meta = paginate_query(query, pagination_params)

        pagination_result = {
            'items': items,
            'page': pagination_meta.page,
            'per_page': pagination_meta.per_page,
            'total': pagination_meta.total,
            'pages': pagination_meta.total_pages
        }

        # Serialize audit logs
        logs = [
            {
                'id': log.id,
                'event_type': log.event_type.value,
                'severity': log.severity.value,
                'user_id': log.user_id,
                'username': log.username,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'endpoint': log.endpoint,
                'method': log.method,
                'status_code': log.status_code,
                'details': json.loads(log.details) if log.details else None,
                'timestamp': log.timestamp.isoformat()
            }
            for log in pagination_result['items']
        ]

        return success_response(
            data={
                'logs': logs,
                'pagination': {
                    'page': pagination_result['page'],
                    'per_page': pagination_result['per_page'],
                    'total_items': pagination_result['total'],
                    'total_pages': pagination_result['pages']
                }
            },
            message=f"Retrieved {len(logs)} audit log(s)"
        )

    except Exception as e:
        current_app.logger.error(f"Error retrieving audit logs: {str(e)}")
        return error_response(
            message="Failed to retrieve audit logs",
            status_code=500
        )


@audit_bp.route('/logs/<int:log_id>', methods=['GET'])
@jwt_required_custom()
def get_audit_log(log_id: int):
    """
    Retrieve detailed information for a specific audit log entry by ID.
    ---
    tags:
      - Audit Logs
    summary: Get audit log by ID
    description: |
      Retrieves complete details for a single audit log entry, including event metadata,
      user information, network details, and event-specific context.

      **Features:**
      - Full audit log record with all metadata
      - Role-based access control (RBAC)
      - Detailed event context (JSON details field)
      - Network information (IP, user agent)
      - HTTP request metadata (endpoint, method, status code)

      **Use Cases:**
      - Deep-dive investigation of specific security event
      - Incident response and forensics
      - Compliance audit trail review
      - User activity verification
      - Dispute resolution (prove/disprove user actions)

      **Authorization Rules:**
      - Admin users: Can view any audit log entry (no restrictions)
      - Non-admin users: Can only view their own audit logs (403 if accessing another user's log)

      **Security Considerations:**
      - Audit logs are immutable (cannot be modified or deleted)
      - Sensitive data in details field is logged for security purposes
      - Access to audit logs is itself audited
    security:
      - Bearer: []
    parameters:
      - in: path
        name: log_id
        type: integer
        required: true
        description: Unique audit log entry identifier
        example: 1234
    responses:
      200:
        description: Audit log entry retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Audit log retrieved successfully"
            data:
              type: object
              properties:
                log:
                  type: object
                  properties:
                    id:
                      type: integer
                      example: 1234
                      description: Audit log entry ID
                    event_type:
                      type: string
                      example: "login"
                      description: Type of security event
                    severity:
                      type: string
                      example: "info"
                      description: Event severity level (info, warning, critical)
                    user_id:
                      type: integer
                      example: 42
                      description: User who triggered the event
                    username:
                      type: string
                      example: "john.doe"
                      description: Username at time of event
                    ip_address:
                      type: string
                      example: "192.168.1.100"
                      description: Source IP address
                    user_agent:
                      type: string
                      example: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                      description: Client user agent string
                    endpoint:
                      type: string
                      example: "/api/v1/auth/login"
                      description: API endpoint accessed
                    method:
                      type: string
                      example: "POST"
                      description: HTTP method (GET, POST, PUT, DELETE, etc.)
                    status_code:
                      type: integer
                      example: 200
                      description: HTTP response status code
                    details:
                      type: object
                      example: {"login_method": "email", "two_factor_used": false}
                      description: Event-specific metadata and context (JSON object)
                    timestamp:
                      type: string
                      format: date-time
                      example: "2024-03-15T14:30:00Z"
                      description: Event timestamp in ISO 8601 format (UTC)
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (non-admin user attempting to access another user's log)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "You do not have permission to view this audit log"
      404:
        description: Audit log entry not found
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Audit log 9999 not found"
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve audit log"
    """
    try:
        # Get current user info
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        current_user_role = claims.get('role', 'viewer')

        # Find audit log
        audit_log = AuditLog.query.get(log_id)

        if not audit_log:
            return error_response(
                message=f"Audit log {log_id} not found",
                status_code=404
            )

        # Permission check: non-admins can only see their own logs
        if current_user_role != 'admin' and audit_log.user_id != current_user_id:
            return error_response(
                message="You do not have permission to view this audit log",
                status_code=403
            )

        # Serialize audit log
        log_data = {
            'id': audit_log.id,
            'event_type': audit_log.event_type.value,
            'severity': audit_log.severity.value,
            'user_id': audit_log.user_id,
            'username': audit_log.username,
            'ip_address': audit_log.ip_address,
            'user_agent': audit_log.user_agent,
            'endpoint': audit_log.endpoint,
            'method': audit_log.method,
            'status_code': audit_log.status_code,
            'details': json.loads(audit_log.details) if audit_log.details else None,
            'timestamp': audit_log.timestamp.isoformat()
        }

        return success_response(
            data={'log': log_data},
            message="Audit log retrieved successfully"
        )

    except Exception as e:
        current_app.logger.error(f"Error retrieving audit log {log_id}: {str(e)}")
        return error_response(
            message="Failed to retrieve audit log",
            status_code=500
        )


@audit_bp.route('/stats', methods=['GET'])
@jwt_required_custom()
@require_role('admin')
@cache.cached(timeout=300, query_string=True)
def get_audit_stats():
    """
    Get comprehensive audit log statistics and analytics (admin only).
    ---
    tags:
      - Audit Logs
    summary: Get audit statistics
    description: |
      Retrieves aggregate statistics and analytics from audit logs, including event counts by type,
      severity distribution, and top active users. Useful for security monitoring and compliance reporting.

      **Features:**
      - Total event count
      - Event distribution by type (login, logout, password_change, etc.)
      - Severity breakdown (info, warning, critical)
      - Top 10 users by event count
      - Date range filtering
      - Cached for 5 minutes (performance optimization)

      **Use Cases:**
      - Security dashboard metrics
      - Compliance reporting (SOC 2, HIPAA, GDPR)
      - User activity analysis
      - Threat detection (unusual activity spikes)
      - Capacity planning (system usage trends)
      - Executive summaries and KPIs

      **Authorization:**
      Requires admin role (non-admins receive 403 Forbidden).

      **Performance:**
      Results are cached for 5 minutes. For real-time stats, cache can be invalidated
      or wait for cache expiration.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: start_date
        type: string
        format: date-time
        required: false
        description: Filter events after this timestamp (ISO 8601 format)
        example: "2024-01-01T00:00:00Z"
      - in: query
        name: end_date
        type: string
        format: date-time
        required: false
        description: Filter events before this timestamp (ISO 8601 format)
        example: "2024-12-31T23:59:59Z"
    responses:
      200:
        description: Audit statistics retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Audit statistics retrieved successfully"
            data:
              type: object
              properties:
                total_events:
                  type: integer
                  example: 15420
                  description: Total number of audit events in the specified period
                events_by_type:
                  type: object
                  example: {"login": 5200, "logout": 4800, "password_change": 150, "user_created": 42}
                  description: Event count grouped by event type
                events_by_severity:
                  type: object
                  example: {"info": 14500, "warning": 850, "critical": 70}
                  description: Event count grouped by severity level
                top_users:
                  type: array
                  items:
                    type: object
                    properties:
                      username:
                        type: string
                        example: "john.doe"
                        description: Username
                      event_count:
                        type: integer
                        example: 450
                        description: Number of events triggered by this user
                  description: Top 10 most active users by event count
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (requires admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Admin role required"
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve audit statistics"
    """
    try:
        from sqlalchemy import func

        # Build base query
        base_query = db.session.query(AuditLog)

        # Apply date filters if provided
        start_date_str = request.args.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            base_query = base_query.filter(AuditLog.timestamp >= start_date)

        end_date_str = request.args.get('end_date')
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            base_query = base_query.filter(AuditLog.timestamp <= end_date)

        # Total events
        total_events = base_query.count()

        # Count events by type using single query with group_by
        event_type_results = (
            db.session.query(
                AuditLog.event_type,
                func.count(AuditLog.id).label('count')
            )
            .filter(*base_query.whereclause.clauses if base_query.whereclause is not None else [])
            .group_by(AuditLog.event_type)
            .all()
        )
        event_counts = {
            event_type.value: count
            for event_type, count in event_type_results
        }

        # Count events by severity using single query with group_by
        severity_results = (
            db.session.query(
                AuditLog.severity,
                func.count(AuditLog.id).label('count')
            )
            .filter(*base_query.whereclause.clauses if base_query.whereclause is not None else [])
            .group_by(AuditLog.severity)
            .all()
        )
        severity_counts = {
            severity.value: count
            for severity, count in severity_results
        }

        # Top users by event count (limit to 10)
        top_users = (
            db.session.query(
                AuditLog.username,
                func.count(AuditLog.id).label('event_count')
            )
            .filter(AuditLog.username.isnot(None))
            .filter(*base_query.whereclause.clauses if base_query.whereclause is not None else [])
            .group_by(AuditLog.username)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
            .all()
        )

        top_users_list = [
            {'username': username, 'event_count': count}
            for username, count in top_users
        ]

        return success_response(
            data={
                'total_events': total_events,
                'events_by_type': event_counts,
                'events_by_severity': severity_counts,
                'top_users': top_users_list
            },
            message="Audit statistics retrieved successfully"
        )

    except Exception as e:
        current_app.logger.error(f"Error retrieving audit stats: {str(e)}")
        return error_response(
            message="Failed to retrieve audit statistics",
            status_code=500
        )
