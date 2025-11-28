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
    Get audit logs with filtering and pagination.

    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 20, max: 100)
        - user_id: Filter by user ID
        - event_type: Filter by event type (login, logout, etc.)
        - severity: Filter by severity (info, warning, critical)
        - start_date: Filter events after this date (ISO 8601)
        - end_date: Filter events before this date (ISO 8601)
        - ip_address: Filter by IP address

    Returns:
        200: Paginated list of audit logs
        400: Invalid query parameters
        403: Insufficient permissions

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/audit/logs?event_type=login&page=1&limit=20" \\
          -H "Authorization: Bearer <access_token>"

    Security:
        - Admin users can view all logs
        - Non-admin users can only view their own logs
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
    Get a specific audit log entry by ID.

    Args:
        log_id: Audit log entry ID

    Returns:
        200: Audit log details
        404: Log not found
        403: Insufficient permissions

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/audit/logs/123" \\
          -H "Authorization: Bearer <access_token>"

    Security:
        - Admin users can view any log
        - Non-admin users can only view their own logs
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
    Get audit log statistics (admin only).

    Query Parameters:
        - start_date: Start date for stats (ISO 8601)
        - end_date: End date for stats (ISO 8601)

    Returns:
        200: Audit statistics
        403: Insufficient permissions

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/audit/stats" \\
          -H "Authorization: Bearer <access_token>"

    Security:
        - Admin only
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
