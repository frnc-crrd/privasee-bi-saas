"""Sorting utilities for RESTful API queries.

This module provides utilities for dynamic query sorting:
- Multi-field sorting
- Ascending/descending order
- Safe field validation
- Sort parameter parsing from requests

Usage:
    from app.core.sorting import SortParams, apply_sorting

    # Parse sort params from request
    sort_params = SortParams.from_request(request, allowed_fields=['created_at', 'username'])

    # Apply to query
    query = apply_sorting(query, User, sort_params)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

from flask import Request
from sqlalchemy import Select, asc, desc


class SortOrder(str, Enum):
    """Sort order direction."""

    ASC = 'asc'
    DESC = 'desc'


@dataclass
class SortField:
    """Single sort field specification.

    Attributes:
        field: Field name to sort by
        order: Sort order (ascending/descending)
    """

    field: str
    order: SortOrder = SortOrder.ASC

    def __post_init__(self) -> None:
        """Normalize sort order."""
        if isinstance(self.order, str):
            self.order = SortOrder(self.order.lower())


@dataclass
class SortParams:
    """Sort parameters parsed from request.

    Attributes:
        fields: List of fields to sort by (in priority order)
    """

    fields: List[SortField] = field(default_factory=list)

    @classmethod
    def from_request(
        cls,
        request: Request,
        allowed_fields: Optional[Set[str]] = None,
        default_sort: Optional[List[SortField]] = None
    ) -> "SortParams":
        """Parse sort parameters from Flask request.

        Supports multiple sort formats:
        - Single field: ?sort=created_at
        - With order: ?sort=-created_at (- prefix for DESC)
        - Multiple: ?sort=role,created_at or ?sort=-created_at,username

        Args:
            request: Flask request object
            allowed_fields: Set of fields that can be sorted (None = all allowed)
            default_sort: Default sort if none specified

        Returns:
            SortParams instance

        Example:
            >>> sort = SortParams.from_request(
            ...     request,
            ...     allowed_fields={'created_at', 'username', 'email'}
            ... )
        """
        sort_param = request.args.get('sort', None, type=str)

        if not sort_param:
            # Use default sort if provided
            if default_sort:
                return cls(fields=default_sort)
            return cls()

        fields = []
        for field_spec in sort_param.split(','):
            field_spec = field_spec.strip()

            # Parse order from prefix
            if field_spec.startswith('-'):
                field_name = field_spec[1:]
                order = SortOrder.DESC
            elif field_spec.startswith('+'):
                field_name = field_spec[1:]
                order = SortOrder.ASC
            else:
                field_name = field_spec
                order = SortOrder.ASC

            # Check if field is allowed
            if allowed_fields and field_name not in allowed_fields:
                continue

            fields.append(SortField(field=field_name, order=order))

        return cls(fields=fields)

    def to_query_param(self) -> str:
        """Convert sort params back to query parameter string.

        Returns:
            Query parameter string

        Example:
            >>> sort = SortParams(fields=[
            ...     SortField('created_at', SortOrder.DESC),
            ...     SortField('username', SortOrder.ASC)
            ... ])
            >>> sort.to_query_param()
            '-created_at,username'
        """
        parts = []
        for sort_field in self.fields:
            prefix = '-' if sort_field.order == SortOrder.DESC else ''
            parts.append(f"{prefix}{sort_field.field}")
        return ','.join(parts)


def apply_sorting(
    query: Select,
    model: type,
    sort_params: SortParams
) -> Select:
    """Apply sorting to SQLAlchemy query.

    Args:
        query: SQLAlchemy Select statement
        model: SQLAlchemy model class
        sort_params: Parsed sort parameters

    Returns:
        Modified query with sorting applied

    Example:
        >>> query = select(User)
        >>> sort = SortParams(fields=[
        ...     SortField('role', SortOrder.ASC),
        ...     SortField('created_at', SortOrder.DESC)
        ... ])
        >>> query = apply_sorting(query, User, sort)
    """
    for sort_field in sort_params.fields:
        # Get model attribute
        try:
            attr = getattr(model, sort_field.field)
        except AttributeError:
            # Field doesn't exist on model, skip
            continue

        # Apply sort order
        if sort_field.order == SortOrder.DESC:
            query = query.order_by(desc(attr))
        else:
            query = query.order_by(asc(attr))

    return query


def parse_sort_field(sort_spec: str) -> SortField:
    """Parse a single sort field specification.

    Args:
        sort_spec: Sort specification (e.g., '-created_at', 'username')

    Returns:
        SortField instance

    Example:
        >>> field = parse_sort_field('-created_at')
        >>> field.field
        'created_at'
        >>> field.order
        <SortOrder.DESC: 'desc'>
    """
    if sort_spec.startswith('-'):
        return SortField(field=sort_spec[1:], order=SortOrder.DESC)
    elif sort_spec.startswith('+'):
        return SortField(field=sort_spec[1:], order=SortOrder.ASC)
    else:
        return SortField(field=sort_spec, order=SortOrder.ASC)
