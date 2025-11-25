"""
Routes initialization.

This module registers all API blueprints.
"""

from flask import Flask
from app.routes.v1 import api_v1_bp


def register_blueprints(app: Flask) -> None:
    """
    Register all application blueprints.

    Args:
        app: Flask application instance

    Example:
        >>> from app.routes import register_blueprints
        >>> register_blueprints(app)
    """
    # Register API v1 blueprint
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

    app.logger.info("All blueprints registered successfully")
