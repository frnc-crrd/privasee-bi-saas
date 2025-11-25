"""Dashboard module for interactive BI visualizations.

This module provides Dash-based dashboards for data visualization:
- Sales performance dashboards
- Executive summaries
- Interactive filters and drill-downs
- Real-time data updates

Usage:
    from app.dashboard import create_dash_app

    # Create Dash app integrated with Flask
    dash_app = create_dash_app(flask_app)
"""

from app.dashboard.app_factory import create_dash_app

__all__ = ['create_dash_app']
