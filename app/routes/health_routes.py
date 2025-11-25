"""Health check and monitoring endpoints."""

from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check() -> tuple[Dict[str, Any], int]:
    """
    Overall system health check.

    Checks all critical components (database, cache, etc.) and returns
    aggregated health status.

    Returns:
        JSON response with health status and component details
    """
    checks = {
        'database': _check_database(),
        'application': _check_application()
    }

    # Overall status is healthy only if all components are healthy
    overall_status = 'healthy' if all(
        check['status'] == 'healthy' for check in checks.values()
    ) else 'unhealthy'

    response = {
        'status': overall_status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': checks
    }

    status_code = 200 if overall_status == 'healthy' else 503
    return jsonify(response), status_code


@health_bp.route('/health/readiness', methods=['GET'])
def readiness_check() -> tuple[Dict[str, Any], int]:
    """
    Readiness probe for Kubernetes/load balancers.

    Indicates whether the application is ready to serve traffic.
    Checks if all dependencies are available and responding.

    Returns:
        JSON response with readiness status
    """
    db_check = _check_database()

    is_ready = db_check['status'] == 'healthy'

    response = {
        'status': 'ready' if is_ready else 'not_ready',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': {
            'database': db_check
        }
    }

    status_code = 200 if is_ready else 503
    return jsonify(response), status_code


@health_bp.route('/health/liveness', methods=['GET'])
def liveness_check() -> tuple[Dict[str, Any], int]:
    """
    Liveness probe for Kubernetes.

    Indicates whether the application is alive and running.
    This is a lightweight check that always succeeds if the process is running.

    Returns:
        JSON response with liveness status
    """
    response = {
        'status': 'alive',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return jsonify(response), 200


def _check_database() -> Dict[str, Any]:
    """
    Check database connectivity and responsiveness.

    Returns:
        Dictionary with status and optional error message
    """
    try:
        # Simple query to verify database connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()

        return {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }


def _check_application() -> Dict[str, Any]:
    """
    Check application-level health.

    Returns:
        Dictionary with status and application info
    """
    return {
        'status': 'healthy',
        'message': 'Application running normally',
        'uptime': _get_uptime()
    }


def _get_uptime() -> str:
    """
    Get application uptime.

    Returns:
        Human-readable uptime string
    """
    # This is a placeholder - in production, track actual startup time
    return 'N/A'
