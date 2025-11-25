"""Filter components for interactive dashboards."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from dash import html, dcc


def create_date_range_filter(
    component_id: str = 'date-range',
    default_days: int = 30
) -> html.Div:
    """Create date range picker filter.

    Args:
        component_id: HTML component ID
        default_days: Default number of days to show

    Returns:
        Dash HTML Div with date picker
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=default_days)

    return html.Div([
        html.Label('Date Range:', className='form-label'),
        dcc.DatePickerRange(
            id=component_id,
            start_date=start_date.date(),
            end_date=end_date.date(),
            display_format='YYYY-MM-DD',
            className='form-control'
        )
    ], className='mb-3')


def create_dropdown_filter(
    component_id: str,
    label: str,
    options: List[dict],
    multi: bool = False,
    placeholder: str = 'Select...'
) -> html.Div:
    """Create dropdown filter.

    Args:
        component_id: HTML component ID
        label: Filter label
        options: List of options (dict with 'label' and 'value')
        multi: Allow multiple selections
        placeholder: Placeholder text

    Returns:
        Dash HTML Div with dropdown
    """
    return html.Div([
        html.Label(label, className='form-label'),
        dcc.Dropdown(
            id=component_id,
            options=options,
            multi=multi,
            placeholder=placeholder,
            className='form-select'
        )
    ], className='mb-3')
