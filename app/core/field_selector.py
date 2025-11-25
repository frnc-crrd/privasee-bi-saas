"""Field selection utilities for sparse fieldsets in API responses.

This module provides utilities for selecting specific fields in API responses:
- Reduce payload size by returning only requested fields
- Support for nested field selection
- Field allowlist/denylist validation

Usage:
    from app.core.field_selector import FieldSelector, select_fields

    # Parse fields from request
    selector = FieldSelector.from_request(request, allowed_fields=['id', 'username', 'email'])

    # Apply to data
    filtered_data = select_fields(data, selector)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from flask import Request


@dataclass
class FieldSelector:
    """Field selection parameters.

    Attributes:
        fields: Set of field names to include in response
        exclude_fields: Set of field names to exclude from response
    """

    fields: Optional[Set[str]] = None
    exclude_fields: Set[str] = field(default_factory=set)

    @classmethod
    def from_request(
        cls,
        request: Request,
        allowed_fields: Optional[Set[str]] = None,
        default_fields: Optional[Set[str]] = None,
        always_exclude: Optional[Set[str]] = None
    ) -> "FieldSelector":
        """Parse field selection from Flask request.

        Supports multiple formats:
        - Include specific fields: ?fields=id,username,email
        - Exclude specific fields: ?exclude=password_hash,secret_key

        Args:
            request: Flask request object
            allowed_fields: Set of fields that can be selected (None = all allowed)
            default_fields: Default fields if none specified
            always_exclude: Fields to always exclude (e.g., sensitive data)

        Returns:
            FieldSelector instance

        Example:
            >>> selector = FieldSelector.from_request(
            ...     request,
            ...     allowed_fields={'id', 'username', 'email', 'role'},
            ...     always_exclude={'password_hash'}
            ... )
        """
        # Parse include fields
        fields_param = request.args.get('fields', None, type=str)
        if fields_param:
            requested_fields = set(f.strip() for f in fields_param.split(','))

            # Filter by allowed fields
            if allowed_fields:
                fields_set = requested_fields & allowed_fields
            else:
                fields_set = requested_fields
        else:
            fields_set = default_fields

        # Parse exclude fields
        exclude_param = request.args.get('exclude', None, type=str)
        exclude_set = set()
        if exclude_param:
            exclude_set = set(f.strip() for f in exclude_param.split(','))

        # Add always excluded fields
        if always_exclude:
            exclude_set.update(always_exclude)

        return cls(fields=fields_set, exclude_fields=exclude_set)

    def should_include(self, field_name: str) -> bool:
        """Check if a field should be included in response.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field should be included, False otherwise

        Example:
            >>> selector = FieldSelector(fields={'id', 'username'}, exclude_fields={'email'})
            >>> selector.should_include('id')
            True
            >>> selector.should_include('email')
            False
            >>> selector.should_include('role')
            False
        """
        # Always exclude if in exclude list
        if field_name in self.exclude_fields:
            return False

        # If fields whitelist specified, only include those
        if self.fields is not None:
            return field_name in self.fields

        # Otherwise include (unless excluded)
        return True


def select_fields(
    data: Any,
    selector: FieldSelector
) -> Any:
    """Apply field selection to data.

    Args:
        data: Data to filter (dict, list of dicts, or any JSON-serializable object)
        selector: Field selector

    Returns:
        Filtered data with only selected fields

    Example:
        >>> data = {'id': 1, 'username': 'john', 'email': 'john@test.com', 'password': 'secret'}
        >>> selector = FieldSelector(fields={'id', 'username'})
        >>> select_fields(data, selector)
        {'id': 1, 'username': 'john'}
    """
    if isinstance(data, dict):
        return _filter_dict(data, selector)
    elif isinstance(data, list):
        return [select_fields(item, selector) for item in data]
    else:
        return data


def _filter_dict(data: Dict[str, Any], selector: FieldSelector) -> Dict[str, Any]:
    """Filter dictionary fields based on selector.

    Args:
        data: Dictionary to filter
        selector: Field selector

    Returns:
        Filtered dictionary
    """
    return {
        key: value
        for key, value in data.items()
        if selector.should_include(key)
    }


def build_field_list(
    model_class: type,
    include_fields: Optional[Set[str]] = None,
    exclude_fields: Optional[Set[str]] = None
) -> List[str]:
    """Build list of fields from SQLAlchemy model.

    Args:
        model_class: SQLAlchemy model class
        include_fields: Fields to include (None = all fields)
        exclude_fields: Fields to exclude

    Returns:
        List of field names

    Example:
        >>> fields = build_field_list(
        ...     User,
        ...     exclude_fields={'password_hash', 'secret_key'}
        ... )
        >>> 'username' in fields
        True
        >>> 'password_hash' in fields
        False
    """
    # Get all column names from model
    all_fields = [column.name for column in model_class.__table__.columns]

    # Apply include filter
    if include_fields:
        all_fields = [f for f in all_fields if f in include_fields]

    # Apply exclude filter
    if exclude_fields:
        all_fields = [f for f in all_fields if f not in exclude_fields]

    return all_fields


def serialize_with_fields(
    obj: Any,
    selector: FieldSelector,
    serializer: Optional[callable] = None
) -> Dict[str, Any]:
    """Serialize object with field selection.

    Args:
        obj: Object to serialize (SQLAlchemy model or dict)
        selector: Field selector
        serializer: Optional custom serializer function

    Returns:
        Serialized dictionary with selected fields

    Example:
        >>> user = User(id=1, username='john', email='john@test.com')
        >>> selector = FieldSelector(fields={'id', 'username'})
        >>> serialize_with_fields(user, selector)
        {'id': 1, 'username': 'john'}
    """
    # Use custom serializer if provided
    if serializer:
        data = serializer(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        # Try to convert to dict (works for SQLAlchemy models with __dict__)
        try:
            data = {
                column.name: getattr(obj, column.name)
                for column in obj.__table__.columns
            }
        except AttributeError:
            # Fallback to object __dict__
            data = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

    return _filter_dict(data, selector)
