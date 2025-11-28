"""
API v1 routes initialization.

Combines all v1 route modules into a single blueprint.
"""

from flask import Blueprint
from app.routes.v1.auth_routes import auth_bp
from app.routes.v1.user_routes import user_bp
from app.routes.v1.analytics_routes import analytics_bp
from app.routes.v1.audit_routes import audit_bp


# Create main API v1 blueprint
api_v1_bp = Blueprint('api_v1', __name__)

# Register sub-blueprints
api_v1_bp.register_blueprint(auth_bp, url_prefix='/auth')
api_v1_bp.register_blueprint(user_bp, url_prefix='/users')
api_v1_bp.register_blueprint(analytics_bp, url_prefix='/analytics')
api_v1_bp.register_blueprint(audit_bp, url_prefix='/audit')


__all__ = ['api_v1_bp', 'auth_bp', 'user_bp', 'analytics_bp', 'audit_bp']
