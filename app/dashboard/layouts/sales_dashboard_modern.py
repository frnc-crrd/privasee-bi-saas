"""Modern sales dashboard layout with professional design and components.

This is an improved version of the sales dashboard featuring:
- Dash Bootstrap Components for modern UI
- Professional color scheme and gradients
- Enhanced typography and spacing
- Responsive grid layout
- Modern card designs with shadows and hover effects
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

from app.dashboard.components.charts import create_kpi_card
from app.dashboard.components.filters import create_date_range_filter, create_dropdown_filter


def get_modern_sales_dashboard_layout() -> html.Div:
    """
    Create modern sales dashboard layout with professional design.

    Returns:
        Dash HTML Div with enhanced dashboard layout
    """
    return dbc.Container([
        # Header Section with Gradient Background
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1(
                        'Sales Analytics Dashboard',
                        className='display-4 fw-bold text-white mb-2'
                    ),
                    html.P(
                        'Real-time sales performance metrics and insights',
                        className='lead text-white-50 mb-0'
                    )
                ], className='p-4 rounded-3', style={
                    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                })
            ], width=12)
        ], className='mb-4'),

        # Filters Section with Modern Card
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className='fas fa-filter me-2'),
                        html.Span('Data Filters', className='fw-bold')
                    ], className='bg-light'),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label('Date Range', className='fw-semibold text-muted small mb-2'),
                                create_date_range_filter('sales-date-range')
                            ], md=6, className='mb-3 mb-md-0'),
                            dbc.Col([
                                html.Label('Product Category', className='fw-semibold text-muted small mb-2'),
                                create_dropdown_filter(
                                    'category-filter',
                                    '',
                                    [
                                        {'label': '📊 All Categories', 'value': 'all'},
                                        {'label': '💻 Electrónica', 'value': 'electronics'},
                                        {'label': '👕 Ropa y Accesorios', 'value': 'clothing'},
                                        {'label': '🏠 Hogar y Decoración', 'value': 'home'},
                                        {'label': '⚽ Deportes', 'value': 'sports'},
                                        {'label': '🍎 Alimentos y Bebidas', 'value': 'food'}
                                    ]
                                )
                            ], md=6)
                        ])
                    ])
                ], className='shadow-sm')
            ], width=12)
        ], className='mb-4'),

        # KPI Cards Row with Modern Design
        dbc.Row([
            # Total Sales KPI
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-dollar-sign fa-2x')
                                ], className='rounded-circle p-3', style={
                                    'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                    'color': 'white',
                                    'width': '60px',
                                    'height': '60px',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center'
                                }),
                            ], className='mb-3'),
                            html.H3('$0', className='mb-1 fw-bold', id='kpi-value-sales'),
                            html.P('Total Sales', className='text-muted mb-2 small fw-semibold'),
                            html.Div([
                                html.Span([
                                    html.I(className='fas fa-arrow-up me-1'),
                                    '0%'
                                ], className='badge bg-success', id='kpi-change-sales')
                            ])
                        ])
                    ])
                ], className='h-100 shadow-sm border-0', style={'transition': 'transform 0.2s'}, id='card-total-sales')
            ], lg=3, md=6, className='mb-4'),

            # Total Orders KPI
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-shopping-cart fa-2x')
                                ], className='rounded-circle p-3', style={
                                    'background': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                    'color': 'white',
                                    'width': '60px',
                                    'height': '60px',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center'
                                }),
                            ], className='mb-3'),
                            html.H3('0', className='mb-1 fw-bold', id='kpi-value-orders'),
                            html.P('Total Orders', className='text-muted mb-2 small fw-semibold'),
                            html.Div([
                                html.Span([
                                    html.I(className='fas fa-arrow-up me-1'),
                                    '0%'
                                ], className='badge bg-info', id='kpi-change-orders')
                            ])
                        ])
                    ])
                ], className='h-100 shadow-sm border-0', style={'transition': 'transform 0.2s'}, id='card-total-orders')
            ], lg=3, md=6, className='mb-4'),

            # Average Order Value KPI
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-chart-line fa-2x')
                                ], className='rounded-circle p-3', style={
                                    'background': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                                    'color': 'white',
                                    'width': '60px',
                                    'height': '60px',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center'
                                }),
                            ], className='mb-3'),
                            html.H3('$0', className='mb-1 fw-bold', id='kpi-value-avg'),
                            html.P('Avg Order Value', className='text-muted mb-2 small fw-semibold'),
                            html.Div([
                                html.Span([
                                    html.I(className='fas fa-arrow-up me-1'),
                                    '0%'
                                ], className='badge bg-primary', id='kpi-change-avg')
                            ])
                        ])
                    ])
                ], className='h-100 shadow-sm border-0', style={'transition': 'transform 0.2s'}, id='card-avg-order')
            ], lg=3, md=6, className='mb-4'),

            # Growth Rate KPI
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-percent fa-2x')
                                ], className='rounded-circle p-3', style={
                                    'background': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                                    'color': 'white',
                                    'width': '60px',
                                    'height': '60px',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center'
                                }),
                            ], className='mb-3'),
                            html.H3('0%', className='mb-1 fw-bold', id='kpi-value-growth'),
                            html.P('Growth Rate', className='text-muted mb-2 small fw-semibold'),
                            html.Div([
                                html.Span([
                                    html.I(className='fas fa-arrow-up me-1'),
                                    'YoY'
                                ], className='badge bg-success', id='kpi-change-growth')
                            ])
                        ])
                    ])
                ], className='h-100 shadow-sm border-0', style={'transition': 'transform 0.2s'}, id='card-growth')
            ], lg=3, md=6, className='mb-4')
        ]),

        # Charts Row 1: Sales Trend (Full Width)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.Div([
                                html.I(className='fas fa-chart-area me-2 text-primary'),
                                html.Span('Sales Trends Over Time', className='fw-bold')
                            ]),
                            html.Small('Track your sales performance day by day', className='text-muted')
                        ], className='d-flex justify-content-between align-items-center')
                    ], className='bg-white border-0'),
                    dbc.CardBody([
                        dcc.Loading(
                            id='loading-sales-trend',
                            type='circle',
                            children=html.Div(id='sales-trend-chart')
                        )
                    ], className='p-4')
                ], className='shadow-sm border-0')
            ], width=12)
        ], className='mb-4'),

        # Charts Row 2: Product Performance and Category Breakdown
        dbc.Row([
            # Top Products Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className='fas fa-trophy me-2 text-warning'),
                        html.Span('Top Performing Products', className='fw-bold')
                    ], className='bg-white border-0'),
                    dbc.CardBody([
                        dcc.Loading(
                            id='loading-products',
                            type='circle',
                            children=html.Div(id='product-performance-chart')
                        )
                    ], className='p-4')
                ], className='shadow-sm border-0 h-100')
            ], lg=6, className='mb-4'),

            # Sales by Location
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className='fas fa-map-marker-alt me-2 text-danger'),
                        html.Span('Sales by Location', className='fw-bold')
                    ], className='bg-white border-0'),
                    dbc.CardBody([
                        dcc.Loading(
                            id='loading-locations',
                            type='circle',
                            children=html.Div(id='location-chart')
                        )
                    ], className='p-4')
                ], className='shadow-sm border-0 h-100')
            ], lg=6, className='mb-4')
        ]),

        # Data Table Section
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.Div([
                                html.I(className='fas fa-table me-2 text-info'),
                                html.Span('Detailed Sales Records', className='fw-bold')
                            ]),
                            dbc.Button([
                                html.I(className='fas fa-download me-2'),
                                'Export CSV'
                            ], color='primary', size='sm', outline=True, id='btn-export-csv')
                        ], className='d-flex justify-content-between align-items-center')
                    ], className='bg-white border-0'),
                    dbc.CardBody([
                        dcc.Loading(
                            id='loading-table',
                            type='circle',
                            children=html.Div(id='sales-data-table')
                        )
                    ], className='p-4')
                ], className='shadow-sm border-0')
            ], width=12)
        ], className='mb-4'),

        # Hidden stores
        html.Div(id='sales-data-store', style={'display': 'none'}),

        # Custom CSS for hover effects and animations
        html.Style("""
            /* Card Hover Effects */
            #card-total-sales:hover, #card-total-orders:hover,
            #card-avg-order:hover, #card-growth:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 16px rgba(0,0,0,0.15) !important;
            }

            /* Smooth transitions */
            .card {
                transition: all 0.3s ease;
            }

            /* Badge animations */
            .badge {
                animation: fadeIn 0.5s ease-in;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: scale(0.8); }
                to { opacity: 1; transform: scale(1); }
            }

            /* Custom scrollbar for tables */
            .dash-table-container::-webkit-scrollbar {
                height: 8px;
            }

            .dash-table-container::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }

            .dash-table-container::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 10px;
            }

            .dash-table-container::-webkit-scrollbar-thumb:hover {
                background: #555;
            }

            /* Typography improvements */
            body {
                font-family: 'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            }

            .display-4 {
                letter-spacing: -0.02em;
            }

            /* Loading spinner customization */
            ._dash-loading-callback {
                color: #667eea !important;
            }
        """)

    ], fluid=True, className='py-4', style={'backgroundColor': '#f8f9fa'})
