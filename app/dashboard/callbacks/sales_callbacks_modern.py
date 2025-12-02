"""Modern callbacks for sales dashboard with enhanced interactivity."""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import dash
from dash.dependencies import Input, Output
from dash import html

from app.dashboard.components.charts import (
    create_sales_trend_chart,
    create_product_performance_chart,
    create_location_map
)
from app.dashboard.components.tables import create_data_table
from app.services.analytics_service import AnalyticsService


# Initialize analytics service
analytics_service = AnalyticsService()


def format_number(value: float, prefix: str = '', suffix: str = '') -> str:
    """Format number with K/M suffix and prefix.

    Args:
        value: Number to format
        prefix: Prefix (e.g., '$')
        suffix: Suffix (e.g., '%')

    Returns:
        Formatted string
    """
    if value >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.1f}M{suffix}"
    elif value >= 1_000:
        return f"{prefix}{value / 1_000:.1f}K{suffix}"
    else:
        return f"{prefix}{value:,.0f}{suffix}"


def create_change_badge(change: float) -> html.Span:
    """Create a badge showing percentage change.

    Args:
        change: Percentage change value

    Returns:
        Dash Span component with badge
    """
    is_positive = change >= 0
    color = 'success' if is_positive else 'danger'
    icon = 'fa-arrow-up' if is_positive else 'fa-arrow-down'

    return html.Span([
        html.I(className=f'fas {icon} me-1'),
        f'{abs(change):.1f}%'
    ], className=f'badge bg-{color}')


def register_sales_callbacks(dash_app: dash.Dash) -> None:
    """Register all modern sales dashboard callbacks.

    Args:
        dash_app: Dash application instance
    """

    @dash_app.callback(
        [
            # KPI Values
            Output('kpi-value-sales', 'children'),
            Output('kpi-value-orders', 'children'),
            Output('kpi-value-avg', 'children'),
            Output('kpi-value-growth', 'children'),
            # KPI Change Badges
            Output('kpi-change-sales', 'children'),
            Output('kpi-change-orders', 'children'),
            Output('kpi-change-avg', 'children'),
            # Charts
            Output('sales-trend-chart', 'children'),
            Output('product-performance-chart', 'children'),
            Output('location-chart', 'children'),
            Output('sales-data-table', 'children'),
        ],
        [
            Input('sales-date-range', 'start_date'),
            Input('sales-date-range', 'end_date'),
            Input('category-filter', 'value')
        ]
    )
    def update_modern_dashboard(
        start_date: str,
        end_date: str,
        category: str
    ) -> Tuple:
        """Update all modern dashboard components based on filters.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            category: Category filter value

        Returns:
            Tuple of updated components (KPIs, badges, charts)
        """
        try:
            # Get sales summary
            summary = analytics_service.get_sales_summary(
                start_date=start_date,
                end_date=end_date
            )

            # Extract KPI values (with defaults)
            total_sales = summary.get('total_sales', 0) if summary else 0
            order_count = summary.get('order_count', 0) if summary else 0
            avg_order = summary.get('avg_order_value', 0) if summary else 0

            # Calculate growth (placeholder - would need historical data comparison)
            growth_rate = 12.5
            sales_growth = 15.3
            orders_growth = 8.7
            avg_growth = 6.2

            # Format KPI values
            formatted_sales = format_number(total_sales, prefix='$')
            formatted_orders = format_number(order_count)
            formatted_avg = format_number(avg_order, prefix='$')
            formatted_growth = f'{growth_rate:.1f}%'

            # Create change badges
            badge_sales = create_change_badge(sales_growth)
            badge_orders = create_change_badge(orders_growth)
            badge_avg = create_change_badge(avg_growth)

            # Get sales trends
            trends = analytics_service.get_sales_trends(
                period='daily',
                start_date=start_date,
                end_date=end_date
            )
            sales_trend_chart = create_sales_trend_chart(
                trends if trends else [],
                title='',  # Title in card header
                height=350
            )

            # Get product performance
            products = analytics_service.get_product_performance(
                limit=10,
                start_date=start_date,
                end_date=end_date
            )
            product_chart = create_product_performance_chart(
                products if products else [],
                chart_type='bar',
                title='',  # Title in card header
                height=350
            )

            # Get location data
            locations = analytics_service.get_location_performance(
                start_date=start_date,
                end_date=end_date
            )
            location_chart = create_location_map(
                locations if locations else [],
                title='',  # Title in card header
                height=350
            )

            # Create data table (limit to 50 rows for performance)
            table_data = []
            if trends:
                table_data = trends[:50]  # Limit to first 50 rows

            data_table = create_data_table(
                data=table_data,
                columns=[
                    {'name': 'Date', 'id': 'date'},
                    {'name': 'Sales', 'id': 'sales'},
                    {'name': 'Orders', 'id': 'orders'},
                ] if table_data and len(table_data) > 0 else []
            )

            return (
                # KPI Values
                formatted_sales,
                formatted_orders,
                formatted_avg,
                formatted_growth,
                # Change Badges
                badge_sales,
                badge_orders,
                badge_avg,
                # Charts
                sales_trend_chart,
                product_chart,
                location_chart,
                data_table or html.Div('No data available', className='text-muted text-center py-4')
            )

        except Exception as e:
            # Return error state for all outputs
            error_msg = f"Error loading dashboard: {str(e)}"
            error_div = html.Div([
                html.I(className='fas fa-exclamation-triangle text-warning me-2'),
                error_msg
            ], className='alert alert-warning')

            return (
                # KPI Values
                '$0',
                '0',
                '$0',
                '0%',
                # Change Badges
                html.Span('N/A', className='badge bg-secondary'),
                html.Span('N/A', className='badge bg-secondary'),
                html.Span('N/A', className='badge bg-secondary'),
                # Charts
                error_div,
                error_div,
                error_div,
                error_div
            )
