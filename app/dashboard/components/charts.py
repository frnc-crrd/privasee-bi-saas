"""Reusable Plotly chart components for dashboards.

This module provides factory functions for creating common chart types:
- Sales trends (line charts)
- Product performance (bar/pie charts)
- Geographic distribution (maps)
- KPI cards

All charts follow consistent styling and support dark mode.
"""

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc


def create_sales_trend_chart(
    data: List[Dict[str, Any]],
    x_field: str = 'date',
    y_field: str = 'sales',
    title: str = 'Sales Trends Over Time',
    height: int = 400
) -> dcc.Graph:
    """Create a line chart for sales trends.

    Args:
        data: List of data dictionaries
        x_field: Field name for x-axis (typically date/time)
        y_field: Field name for y-axis (sales value)
        title: Chart title
        height: Chart height in pixels

    Returns:
        Dash Graph component with line chart

    Example:
        >>> data = [
        ...     {'date': '2024-01', 'sales': 10000},
        ...     {'date': '2024-02', 'sales': 15000}
        ... ]
        >>> chart = create_sales_trend_chart(data)
    """
    if not data:
        # Return empty chart if no data
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray")
        )
    else:
        # Extract data
        x_values = [item[x_field] for item in data]
        y_values = [item[y_field] for item in data]

        # Create line chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',
            name='Sales',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Sales: $%{y:,.0f}<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title=x_field.capitalize(),
        yaxis_title=y_field.capitalize(),
        height=height,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': True, 'displaylogo': False}
    )


def create_product_performance_chart(
    data: List[Dict[str, Any]],
    chart_type: str = 'bar',
    top_n: int = 10,
    title: str = 'Top Products by Sales',
    height: int = 400
) -> dcc.Graph:
    """Create bar or pie chart for product performance.

    Args:
        data: List of product data dictionaries
        chart_type: 'bar' or 'pie'
        top_n: Number of top products to show
        title: Chart title
        height: Chart height in pixels

    Returns:
        Dash Graph component

    Example:
        >>> data = [
        ...     {'product': 'Product A', 'sales': 5000, 'quantity': 100},
        ...     {'product': 'Product B', 'sales': 3000, 'quantity': 75}
        ... ]
        >>> chart = create_product_performance_chart(data, chart_type='bar')
    """
    if not data:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
    else:
        # Limit to top N
        data = data[:top_n]

        if chart_type == 'pie':
            # Pie chart
            fig = go.Figure(data=[go.Pie(
                labels=[item.get('product', item.get('name', 'Unknown')) for item in data],
                values=[item.get('sales', item.get('value', 0)) for item in data],
                hole=0.4,
                marker=dict(colors=px.colors.qualitative.Set3),
                hovertemplate='<b>%{label}</b><br>Sales: $%{value:,.0f}<br>%{percent}<extra></extra>'
            )])
        else:
            # Bar chart
            products = [item.get('product', item.get('name', 'Unknown')) for item in data]
            sales = [item.get('sales', item.get('value', 0)) for item in data]

            fig = go.Figure(data=[go.Bar(
                x=products,
                y=sales,
                marker=dict(
                    color=sales,
                    colorscale='Blues',
                    showscale=False
                ),
                hovertemplate='<b>%{x}</b><br>Sales: $%{y:,.0f}<extra></extra>'
            )])

    # Update layout
    fig.update_layout(
        title=title,
        height=height,
        template='plotly_white',
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=chart_type == 'pie'
    )

    if chart_type == 'bar':
        fig.update_xaxis(title='Product', tickangle=-45)
        fig.update_yaxis(title='Sales ($)')

    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': True, 'displaylogo': False}
    )


def create_location_map(
    data: List[Dict[str, Any]],
    title: str = 'Sales by Location',
    height: int = 500
) -> dcc.Graph:
    """Create a geographic map visualization.

    Args:
        data: List of location data with lat, lon, and value
        title: Chart title
        height: Chart height in pixels

    Returns:
        Dash Graph component with map

    Example:
        >>> data = [
        ...     {'location': 'Store 1', 'lat': 40.7128, 'lon': -74.0060, 'sales': 5000},
        ...     {'location': 'Store 2', 'lat': 34.0522, 'lon': -118.2437, 'sales': 3000}
        ... ]
        >>> chart = create_location_map(data)
    """
    if not data or not any('lat' in item and 'lon' in item for item in data):
        # No geographic data, create simple bar chart
        fig = go.Figure(data=[go.Bar(
            x=[item.get('location', item.get('name', 'Unknown')) for item in data],
            y=[item.get('sales', item.get('value', 0)) for item in data],
            marker=dict(color='#A23B72')
        )])
        fig.update_layout(
            title=title,
            xaxis_title='Location',
            yaxis_title='Sales',
            height=height,
            template='plotly_white'
        )
    else:
        # Create scatter map
        fig = go.Figure(data=go.Scattergeo(
            lon=[item['lon'] for item in data if 'lon' in item],
            lat=[item['lat'] for item in data if 'lat' in item],
            text=[item.get('location', 'Unknown') for item in data],
            marker=dict(
                size=[item.get('sales', item.get('value', 0)) / 100 for item in data],
                color=[item.get('sales', item.get('value', 0)) for item in data],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Sales ($)")
            ),
            hovertemplate='<b>%{text}</b><br>Sales: $%{marker.color:,.0f}<extra></extra>'
        ))

        fig.update_layout(
            title=title,
            height=height,
            geo=dict(
                scope='north america',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                coastlinecolor='rgb(204, 204, 204)',
            )
        )

    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': True, 'displaylogo': False}
    )


def create_kpi_card(
    value: float,
    title: str,
    icon: str = 'fa-chart-line',
    change: Optional[float] = None,
    prefix: str = '$',
    suffix: str = ''
) -> html.Div:
    """Create a KPI card component.

    Args:
        value: KPI value
        title: KPI title
        icon: Font Awesome icon class
        change: Percentage change (optional)
        prefix: Value prefix (e.g., '$')
        suffix: Value suffix (e.g., '%')

    Returns:
        Dash HTML Div component

    Example:
        >>> card = create_kpi_card(
        ...     value=150000,
        ...     title='Total Sales',
        ...     icon='fa-dollar-sign',
        ...     change=12.5
        ... )
    """
    # Format value
    if value >= 1_000_000:
        formatted_value = f"{prefix}{value / 1_000_000:.1f}M{suffix}"
    elif value >= 1_000:
        formatted_value = f"{prefix}{value / 1_000:.1f}K{suffix}"
    else:
        formatted_value = f"{prefix}{value:,.0f}{suffix}"

    # Change indicator
    change_html = []
    if change is not None:
        change_color = 'success' if change >= 0 else 'danger'
        change_icon = 'fa-arrow-up' if change >= 0 else 'fa-arrow-down'
        change_html = [
            html.Span([
                html.I(className=f'fas {change_icon} me-1'),
                f'{abs(change):.1f}%'
            ], className=f'badge bg-{change_color}')
        ]

    return html.Div([
        html.Div([
            html.Div([
                html.I(className=f'fas {icon} fa-2x text-primary')
            ], className='col-auto'),
            html.Div([
                html.H3(formatted_value, className='mb-0'),
                html.P([title] + change_html, className='text-muted mb-0')
            ], className='col')
        ], className='row align-items-center')
    ], className='card-body')
