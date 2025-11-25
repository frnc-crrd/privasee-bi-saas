"""Callbacks for sales dashboard interactivity."""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import dash
from dash.dependencies import Input, Output
from dash import html

from app.dashboard.components.charts import (
    create_sales_trend_chart,
    create_product_performance_chart,
    create_kpi_card
)
from app.dashboard.components.tables import create_data_table
from app.services.analytics_service import AnalyticsService


# Initialize analytics service
analytics_service = AnalyticsService()


def register_sales_callbacks(dash_app: dash.Dash) -> None:
    """Register all sales dashboard callbacks.

    Args:
        dash_app: Dash application instance
    """

    @dash_app.callback(
        [
            Output('kpi-total-sales', 'children'),
            Output('kpi-total-orders', 'children'),
            Output('kpi-avg-order', 'children'),
            Output('kpi-growth', 'children'),
            Output('sales-trend-chart', 'children'),
            Output('product-performance-chart', 'children'),
            Output('sales-data-table', 'children'),
        ],
        [
            Input('sales-date-range', 'start_date'),
            Input('sales-date-range', 'end_date'),
            Input('category-filter', 'value')
        ]
    )
    def update_dashboard(
        start_date: str,
        end_date: str,
        category: str
    ) -> Tuple:
        """Update all dashboard components based on filters.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            category: Category filter value

        Returns:
            Tuple of updated components
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

            # Calculate growth (placeholder - would need historical data)
            growth_rate = 12.5

            # Create KPI cards
            kpi_total_sales = html.Div(
                create_kpi_card(total_sales, 'Total Sales', 'fa-dollar-sign', growth_rate),
                className='card'
            )
            kpi_total_orders = html.Div(
                create_kpi_card(order_count, 'Total Orders', 'fa-shopping-cart', 5.2, prefix=''),
                className='card'
            )
            kpi_avg_order = html.Div(
                create_kpi_card(avg_order, 'Avg Order Value', 'fa-chart-line', 3.1),
                className='card'
            )
            kpi_growth = html.Div(
                create_kpi_card(growth_rate, 'Growth Rate', 'fa-percent', None, prefix='', suffix='%'),
                className='card'
            )

            # Get sales trends
            trends = analytics_service.get_sales_trends(
                period='daily',
                start_date=start_date,
                end_date=end_date
            )
            sales_trend_chart = create_sales_trend_chart(trends if trends else [])

            # Get product performance
            products = analytics_service.get_product_performance(
                limit=10,
                start_date=start_date,
                end_date=end_date
            )
            product_chart = create_product_performance_chart(
                products if products else [],
                chart_type='bar'
            )

            # Create data table
            table_data = products[:20] if products else []
            table_columns = ['product', 'sales', 'quantity'] if table_data else []
            data_table = create_data_table(table_data, table_columns)

            return (
                kpi_total_sales,
                kpi_total_orders,
                kpi_avg_order,
                kpi_growth,
                sales_trend_chart,
                product_chart,
                data_table
            )

        except Exception as e:
            # Return error state
            error_msg = html.Div([
                html.I(className='fas fa-exclamation-triangle text-warning me-2'),
                f'Error loading data: {str(e)}'
            ], className='alert alert-warning')

            return (
                error_msg, error_msg, error_msg, error_msg,
                error_msg, error_msg, error_msg
            )
