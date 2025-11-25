"""Sales dashboard layout with KPIs, charts, and filters."""

from dash import html, dcc

from app.dashboard.components.charts import create_kpi_card
from app.dashboard.components.filters import create_date_range_filter, create_dropdown_filter


def get_sales_dashboard_layout() -> html.Div:
    """Create sales dashboard layout.

    Returns:
        Dash HTML Div with complete dashboard layout
    """
    return html.Div([
        # Header
        html.Div([
            html.H1('Sales Dashboard', className='mb-0'),
            html.P('Interactive sales performance analytics', className='text-muted')
        ], className='mb-4'),

        # Filters Row
        html.Div([
            html.Div([
                html.H5('Filters', className='mb-3'),
                html.Div([
                    # Date range filter
                    html.Div(
                        create_date_range_filter('sales-date-range'),
                        className='col-md-6'
                    ),
                    # Category filter
                    html.Div(
                        create_dropdown_filter(
                            'category-filter',
                            'Category',
                            [
                                {'label': 'All Categories', 'value': 'all'},
                                {'label': 'Electronics', 'value': 'electronics'},
                                {'label': 'Clothing', 'value': 'clothing'},
                                {'label': 'Food', 'value': 'food'}
                            ]
                        ),
                        className='col-md-6'
                    )
                ], className='row')
            ], className='card-body')
        ], className='card mb-4'),

        # KPI Cards Row
        html.Div([
            html.Div([
                html.Div(
                    create_kpi_card(0, 'Total Sales', 'fa-dollar-sign', 0),
                    className='card', id='kpi-total-sales'
                )
            ], className='col-md-3'),
            html.Div([
                html.Div(
                    create_kpi_card(0, 'Total Orders', 'fa-shopping-cart', 0, prefix=''),
                    className='card', id='kpi-total-orders'
                )
            ], className='col-md-3'),
            html.Div([
                html.Div(
                    create_kpi_card(0, 'Avg Order Value', 'fa-chart-line', 0),
                    className='card', id='kpi-avg-order'
                )
            ], className='col-md-3'),
            html.Div([
                html.Div(
                    create_kpi_card(0, 'Growth Rate', 'fa-percent', 0, prefix='', suffix='%'),
                    className='card', id='kpi-growth'
                )
            ], className='col-md-3')
        ], className='row mb-4', id='kpi-row'),

        # Charts Row 1: Sales Trend
        html.Div([
            html.Div([
                html.Div([
                    html.H5('Sales Trends', className='card-title'),
                    html.Div(id='sales-trend-chart')
                ], className='card-body')
            ], className='card')
        ], className='mb-4'),

        # Charts Row 2: Product Performance and Location
        html.Div([
            html.Div([
                html.Div([
                    html.H5('Top Products', className='card-title'),
                    html.Div(id='product-performance-chart')
                ], className='card-body')
            ], className='card', style={'height': '100%'})
        ], className='col-md-6 mb-4'),

        # Data Table
        html.Div([
            html.Div([
                html.Div([
                    html.H5('Sales Details', className='card-title'),
                    html.Div(id='sales-data-table')
                ], className='card-body')
            ], className='card')
        ], className='mb-4'),

        # Hidden div to store data
        html.Div(id='sales-data-store', style={'display': 'none'})

    ], className='container-fluid p-4')
