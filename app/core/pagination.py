"""Pagination utilities for RESTful API responses.

This module provides pagination helpers for list endpoints:
- Offset-based pagination (limit/offset)
- Cursor-based pagination (for large datasets)
- Pagination metadata calculation
- PaginatedResponse builder

Usage:
    from app.core.pagination import paginate_query, PaginationParams

    # Parse pagination params from request
    pagination = PaginationParams.from_request(request)

    # Apply to SQLAlchemy query
    results, meta = paginate_query(query, pagination)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypeVar

from flask import Request
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Query

from app.extensions import db

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Pagination parameters from request.

    Attributes:
        page: Page number (1-indexed)
        per_page: Items per page
        offset: Offset for database query
        limit: Limit for database query
        cursor: Optional cursor for cursor-based pagination
    """

    page: int = 1
    per_page: int = 20
    offset: int = 0
    limit: int = 20
    cursor: Optional[str] = None

    def __post_init__(self) -> None:
        """Calculate offset from page and per_page."""
        self.page = max(1, self.page)
        self.per_page = min(100, max(1, self.per_page))
        self.limit = self.per_page
        self.offset = (self.page - 1) * self.per_page

    @classmethod
    def from_request(
        cls,
        request: Request,
        default_per_page: int = 20,
        max_per_page: int = 100
    ) -> "PaginationParams":
        """Parse pagination parameters from Flask request.

        Args:
            request: Flask request object
            default_per_page: Default items per page
            max_per_page: Maximum items per page

        Returns:
            PaginationParams instance

        Example:
            >>> pagination = PaginationParams.from_request(request)
            >>> pagination.page
            1
            >>> pagination.per_page
            20
        """
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', default_per_page, type=int)
        cursor = request.args.get('cursor', None, type=str)

        # Enforce limits
        per_page = min(max_per_page, max(1, per_page))

        return cls(
            page=page,
            per_page=per_page,
            cursor=cursor
        )


@dataclass
class PaginationMeta:
    """Pagination metadata for API responses.

    Attributes:
        page: Current page number
        per_page: Items per page
        total_items: Total number of items
        total_pages: Total number of pages
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page
        next_page: Next page number (if exists)
        prev_page: Previous page number (if exists)
    """

    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response.

        Returns:
            Dictionary with pagination metadata

        Example:
            >>> meta = PaginationMeta(page=1, per_page=20, total_items=100, ...)
            >>> meta.to_dict()
            {'page': 1, 'per_page': 20, 'total_items': 100, ...}
        """
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total_items': self.total_items,
            'total_pages': self.total_pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev,
            'next_page': self.next_page,
            'prev_page': self.prev_page,
        }


def calculate_pagination_meta(
    total_items: int,
    page: int,
    per_page: int
) -> PaginationMeta:
    """Calculate pagination metadata.

    Args:
        total_items: Total number of items
        page: Current page number (1-indexed)
        per_page: Items per page

    Returns:
        PaginationMeta instance

    Example:
        >>> meta = calculate_pagination_meta(total_items=100, page=1, per_page=20)
        >>> meta.total_pages
        5
        >>> meta.has_next
        True
    """
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    has_next = page < total_pages
    has_prev = page > 1

    return PaginationMeta(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=page + 1 if has_next else None,
        prev_page=page - 1 if has_prev else None,
    )


def paginate_query(
    query: Select,
    pagination: PaginationParams,
    count_query: Optional[Select] = None
) -> Tuple[List[Any], PaginationMeta]:
    """Paginate a SQLAlchemy query with metadata.

    Args:
        query: SQLAlchemy Select statement
        pagination: Pagination parameters
        count_query: Optional separate count query (for optimization)

    Returns:
        Tuple of (items list, pagination metadata)

    Example:
        >>> from sqlalchemy import select
        >>> query = select(User).where(User.is_active == True)
        >>> pagination = PaginationParams(page=1, per_page=20)
        >>> items, meta = paginate_query(query, pagination)
        >>> len(items)
        20
        >>> meta.total_items
        100
    """
    # Get total count
    if count_query is not None:
        count_result = db.session.execute(count_query)
        total_items = count_result.scalar()
    else:
        # Build count query from original query
        count_stmt = select(func.count()).select_from(query.alias())
        count_result = db.session.execute(count_stmt)
        total_items = count_result.scalar()

    # Apply pagination
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)

    # Execute query
    result = db.session.execute(paginated_query)
    items = list(result.scalars().all())

    # Calculate metadata
    meta = calculate_pagination_meta(
        total_items=total_items or 0,
        page=pagination.page,
        per_page=pagination.per_page
    )

    return items, meta


def build_pagination_links(
    base_url: str,
    meta: PaginationMeta,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[str]]:
    """Build pagination links for HATEOAS responses.

    Args:
        base_url: Base URL for the endpoint
        meta: Pagination metadata
        query_params: Additional query parameters to preserve

    Returns:
        Dictionary with self, first, prev, next, last links

    Example:
        >>> meta = PaginationMeta(page=2, per_page=20, total_items=100, ...)
        >>> links = build_pagination_links('/api/v1/users', meta)
        >>> links['next']
        '/api/v1/users?page=3&per_page=20'
    """
    query_params = query_params or {}

    def build_url(page: int) -> str:
        params = {**query_params, 'page': page, 'per_page': meta.per_page}
        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    return {
        'self': build_url(meta.page),
        'first': build_url(1),
        'prev': build_url(meta.prev_page) if meta.has_prev else None,
        'next': build_url(meta.next_page) if meta.has_next else None,
        'last': build_url(meta.total_pages),
    }
