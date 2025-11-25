"""Dynamic filtering engine for RESTful API queries.

This module provides utilities for building dynamic filters from request parameters:
- Type-safe filter parsing
- Multiple operator support (eq, ne, gt, lt, like, in)
- Nested field filtering
- Date range filtering

Usage:
    from app.core.filtering import FilterParams, apply_filters

    # Parse filters from request
    filters = FilterParams.from_request(request, allowed_fields=['role', 'is_active'])

    # Apply to query
    query = apply_filters(query, User, filters)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from flask import Request
from sqlalchemy import Select, and_, or_
from sqlalchemy.orm import InstrumentedAttribute


class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQ = 'eq'           # Equal
    NE = 'ne'           # Not equal
    GT = 'gt'           # Greater than
    GTE = 'gte'         # Greater than or equal
    LT = 'lt'           # Less than
    LTE = 'lte'         # Less than or equal
    LIKE = 'like'       # SQL LIKE (case-insensitive)
    ILIKE = 'ilike'     # Case-insensitive LIKE
    IN = 'in'           # In list
    NOT_IN = 'not_in'   # Not in list
    IS_NULL = 'is_null' # Is NULL
    NOT_NULL = 'not_null' # Is not NULL


@dataclass
class FilterCondition:
    """Single filter condition.

    Attributes:
        field: Field name to filter on
        operator: Filter operator
        value: Filter value
    """

    field: str
    operator: FilterOperator
    value: Any

    def __post_init__(self) -> None:
        """Validate and normalize filter condition."""
        # Convert operator string to enum
        if isinstance(self.operator, str):
            self.operator = FilterOperator(self.operator)

        # Normalize value for IN/NOT_IN operators
        if self.operator in (FilterOperator.IN, FilterOperator.NOT_IN):
            if isinstance(self.value, str):
                self.value = [v.strip() for v in self.value.split(',')]


@dataclass
class FilterParams:
    """Filter parameters parsed from request.

    Attributes:
        conditions: List of filter conditions
        search: Optional search term for text fields
    """

    conditions: List[FilterCondition] = field(default_factory=list)
    search: Optional[str] = None

    @classmethod
    def from_request(
        cls,
        request: Request,
        allowed_fields: Optional[Set[str]] = None,
        search_fields: Optional[List[str]] = None
    ) -> "FilterParams":
        """Parse filter parameters from Flask request.

        Supports multiple filter formats:
        - Simple: ?role=admin&is_active=true
        - Operator: ?created_at__gte=2024-01-01
        - Search: ?search=john

        Args:
            request: Flask request object
            allowed_fields: Set of fields that can be filtered (None = all allowed)
            search_fields: List of fields to search in with ?search param

        Returns:
            FilterParams instance

        Example:
            >>> filters = FilterParams.from_request(
            ...     request,
            ...     allowed_fields={'role', 'is_active', 'created_at'}
            ... )
        """
        conditions = []
        search = request.args.get('search', None, type=str)

        for key, value in request.args.items():
            # Skip non-filter params
            if key in ('page', 'per_page', 'sort', 'fields', 'search', 'cursor'):
                continue

            # Parse operator from field name (e.g., created_at__gte)
            if '__' in key:
                field_name, operator_str = key.rsplit('__', 1)
                try:
                    operator = FilterOperator(operator_str)
                except ValueError:
                    # Invalid operator, skip
                    continue
            else:
                field_name = key
                operator = FilterOperator.EQ

            # Check if field is allowed
            if allowed_fields and field_name not in allowed_fields:
                continue

            # Parse value
            parsed_value = _parse_filter_value(value, operator)

            conditions.append(FilterCondition(
                field=field_name,
                operator=operator,
                value=parsed_value
            ))

        return cls(conditions=conditions, search=search)


def _parse_filter_value(value: str, operator: FilterOperator) -> Any:
    """Parse filter value to appropriate Python type.

    Args:
        value: Raw value from request
        operator: Filter operator

    Returns:
        Parsed value
    """
    # Boolean values
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'

    # Null checks
    if operator in (FilterOperator.IS_NULL, FilterOperator.NOT_NULL):
        return None

    # Numeric values
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # Date/datetime values
    try:
        # Try ISO format first
        if 'T' in value:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Try date only
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        pass

    # String value (default)
    return value


def apply_filters(
    query: Select,
    model: type,
    filter_params: FilterParams
) -> Select:
    """Apply filters to SQLAlchemy query.

    Args:
        query: SQLAlchemy Select statement
        model: SQLAlchemy model class
        filter_params: Parsed filter parameters

    Returns:
        Modified query with filters applied

    Example:
        >>> query = select(User)
        >>> filters = FilterParams(conditions=[
        ...     FilterCondition('role', FilterOperator.EQ, 'admin'),
        ...     FilterCondition('is_active', FilterOperator.EQ, True)
        ... ])
        >>> query = apply_filters(query, User, filters)
    """
    for condition in filter_params.conditions:
        # Get model attribute
        try:
            attr = getattr(model, condition.field)
        except AttributeError:
            # Field doesn't exist on model, skip
            continue

        # Build filter clause
        clause = _build_filter_clause(attr, condition.operator, condition.value)
        if clause is not None:
            query = query.where(clause)

    return query


def _build_filter_clause(
    attr: InstrumentedAttribute,
    operator: FilterOperator,
    value: Any
) -> Any:
    """Build SQLAlchemy filter clause for a condition.

    Args:
        attr: SQLAlchemy model attribute
        operator: Filter operator
        value: Filter value

    Returns:
        SQLAlchemy filter expression
    """
    if operator == FilterOperator.EQ:
        return attr == value
    elif operator == FilterOperator.NE:
        return attr != value
    elif operator == FilterOperator.GT:
        return attr > value
    elif operator == FilterOperator.GTE:
        return attr >= value
    elif operator == FilterOperator.LT:
        return attr < value
    elif operator == FilterOperator.LTE:
        return attr <= value
    elif operator == FilterOperator.LIKE:
        return attr.like(f'%{value}%')
    elif operator == FilterOperator.ILIKE:
        return attr.ilike(f'%{value}%')
    elif operator == FilterOperator.IN:
        return attr.in_(value)
    elif operator == FilterOperator.NOT_IN:
        return attr.not_in(value)
    elif operator == FilterOperator.IS_NULL:
        return attr.is_(None)
    elif operator == FilterOperator.NOT_NULL:
        return attr.is_not(None)

    return None


def apply_search(
    query: Select,
    model: type,
    search_term: str,
    search_fields: List[str]
) -> Select:
    """Apply search filter across multiple fields.

    Args:
        query: SQLAlchemy Select statement
        model: SQLAlchemy model class
        search_term: Search term
        search_fields: List of field names to search in

    Returns:
        Modified query with search applied

    Example:
        >>> query = select(User)
        >>> query = apply_search(query, User, 'john', ['username', 'email'])
    """
    if not search_term or not search_fields:
        return query

    # Build OR clause for all search fields
    search_clauses = []
    for field_name in search_fields:
        try:
            attr = getattr(model, field_name)
            search_clauses.append(attr.ilike(f'%{search_term}%'))
        except AttributeError:
            continue

    if search_clauses:
        query = query.where(or_(*search_clauses))

    return query
