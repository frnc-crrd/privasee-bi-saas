"""Data table components for dashboards."""

from typing import Any, Dict, List

from dash import dash_table, html


def create_data_table(
    data: List[Dict[str, Any]],
    columns: List[str],
    table_id: str = 'data-table',
    page_size: int = 10
) -> html.Div:
    """Create interactive data table.

    Args:
        data: List of data dictionaries
        columns: List of column names to display
        table_id: HTML component ID
        page_size: Number of rows per page

    Returns:
        Dash HTML Div with data table
    """
    if not data:
        return html.Div(
            html.P('No data available', className='text-muted text-center'),
            className='p-4'
        )

    # Build column definitions
    column_defs = [{'name': col.replace('_', ' ').title(), 'id': col} for col in columns]

    return html.Div([
        dash_table.DataTable(
            id=table_id,
            columns=column_defs,
            data=data,
            page_size=page_size,
            page_action='native',
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': 'Arial, sans-serif'
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'borderBottom': '2px solid #dee2e6'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ]
        )
    ])
