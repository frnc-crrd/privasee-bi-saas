"""Dash application factory for BI dashboards.

This module creates a Dash app integrated with Flask for interactive visualizations.
The Dash app shares authentication and session management with the main Flask app.

Usage:
    from flask import Flask
    from app.dashboard import create_dash_app

    flask_app = Flask(__name__)
    dash_app = create_dash_app(flask_app, url_base_pathname='/dashboard/')
"""

from typing import Optional

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
from flask import Flask

from app.dashboard.layouts.sales_dashboard_modern import get_modern_sales_dashboard_layout
from app.dashboard.callbacks.sales_callbacks_modern import register_sales_callbacks


def create_dash_app(
    flask_app: Flask,
    url_base_pathname: str = '/dashboard/',
    title: str = 'Privasee BI Dashboard'
) -> Dash:
    """Create and configure Dash application integrated with Flask.

    Args:
        flask_app: Flask application instance
        url_base_pathname: Base URL path for Dash app
        title: Dashboard page title

    Returns:
        Configured Dash application instance

    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> dash_app = create_dash_app(app)
    """
    # Create Dash app with Flask server
    dash_app = Dash(
        __name__,
        server=flask_app,
        url_base_pathname=url_base_pathname,
        suppress_callback_exceptions=True,
        title=title,
        external_stylesheets=[
            # Dash Bootstrap Components theme (modern design)
            dbc.themes.BOOTSTRAP,
            # Font Awesome for icons
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
            # Google Fonts for better typography
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
        ],
        meta_tags=[
            # Responsive meta tag
            {'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}
        ]
    )

    # Set layout
    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ])

    # Register main layout callback
    @dash_app.callback(
        dash.dependencies.Output('page-content', 'children'),
        [dash.dependencies.Input('url', 'pathname')]
    )
    def display_page(pathname: Optional[str]) -> html.Div:
        """Route to appropriate dashboard based on URL path.

        Args:
            pathname: URL pathname

        Returns:
            Dashboard layout
        """
        if pathname == url_base_pathname or pathname == f'{url_base_pathname}sales':
            return get_modern_sales_dashboard_layout()
        else:
            return dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className='fas fa-exclamation-triangle fa-5x text-warning mb-4'),
                            html.H1('404: Page Not Found', className='display-4 fw-bold mb-3'),
                            html.P('The requested dashboard does not exist.', className='lead text-muted mb-4'),
                            dbc.Button([
                                html.I(className='fas fa-home me-2'),
                                'Go to Sales Dashboard'
                            ], href=f'{url_base_pathname}sales', color='primary', size='lg')
                        ], className='text-center py-5')
                    ], width=12)
                ])
            ], className='mt-5')

    # Register callbacks
    register_sales_callbacks(dash_app)

    return dash_app
