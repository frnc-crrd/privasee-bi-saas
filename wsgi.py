"""
WSGI entry point for production deployment.

This module creates the Flask application instance for use with WSGI servers
like Gunicorn, uWSGI, or mod_wsgi.

Usage:
    gunicorn wsgi:application
    uwsgi --http :5000 --wsgi-file wsgi.py --callable application
"""

from app import create_app

# Create application instance
# Configuration is loaded from environment variables via Pydantic Settings
application = create_app()

if __name__ == "__main__":
    # For development only - use gunicorn in production
    application.run()
