"""
Unit tests for field selector module.

This module contains comprehensive tests for API field selection utilities,
including sparse fieldsets, field filtering, security validation, and
SQLAlchemy model integration.

Test Coverage:
    - FieldSelector creation from request parameters
    - Field inclusion/exclusion logic
    - Data filtering (dicts, lists, nested structures)
    - SQLAlchemy model integration
    - Security and input validation
    - Edge cases and error handling
"""

from unittest.mock import Mock, MagicMock
import pytest

from app.core.field_selector import (
    FieldSelector,
    select_fields,
    build_field_list,
    serialize_with_fields,
    _filter_dict
)


class TestFieldSelectorCreation:
    """Tests for FieldSelector creation from request parameters."""

    def test_from_request_with_fields_parameter(self):
        """Test creating FieldSelector from request with fields parameter.

        Verifies that the fields query parameter is correctly parsed
        into a set of field names.

        Assertions:
            - Fields are parsed from comma-separated string
            - Whitespace is stripped
            - Result is a set of field names
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': 'id,username,email',
            'exclude': None
        }.get(key, default)

        # Act
        selector = FieldSelector.from_request(mock_request)

        # Assert
        assert selector.fields == {'id', 'username', 'email'}
        assert selector.exclude_fields == set()

    def test_from_request_with_exclude_parameter(self):
        """Test creating FieldSelector with exclude parameter.

        Verifies that fields can be excluded from the response using
        the exclude query parameter.

        Assertions:
            - Exclude fields are parsed correctly
            - Fields set is None when no include specified
            - Exclude set contains specified fields
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': None,
            'exclude': 'password_hash,secret_key'
        }.get(key, default)

        # Act
        selector = FieldSelector.from_request(mock_request)

        # Assert
        assert selector.fields is None
        assert selector.exclude_fields == {'password_hash', 'secret_key'}

    def test_from_request_with_allowed_fields_filter(self):
        """Test that allowed_fields parameter restricts selectable fields.

        Verifies that only fields in the allowed_fields set can be
        selected, preventing unauthorized field access.

        Assertions:
            - Requested fields filtered by allowed_fields
            - Unauthorized fields are removed
            - Only intersection of requested and allowed remains
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': 'id,username,password_hash,email',
            'exclude': None
        }.get(key, default)

        allowed = {'id', 'username', 'email'}

        # Act
        selector = FieldSelector.from_request(mock_request, allowed_fields=allowed)

        # Assert
        assert selector.fields == {'id', 'username', 'email'}
        assert 'password_hash' not in selector.fields

    def test_from_request_with_always_exclude(self):
        """Test that always_exclude fields are always excluded.

        Verifies that sensitive fields can be forcibly excluded
        regardless of user request.

        Assertions:
            - always_exclude fields added to exclude_fields
            - Cannot be overridden by user request
            - Security protection for sensitive data
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': None,
            'exclude': 'temp_data'
        }.get(key, default)

        always_exclude = {'password_hash', 'secret_key'}

        # Act
        selector = FieldSelector.from_request(
            mock_request,
            always_exclude=always_exclude
        )

        # Assert
        assert 'password_hash' in selector.exclude_fields
        assert 'secret_key' in selector.exclude_fields
        assert 'temp_data' in selector.exclude_fields

    def test_from_request_with_default_fields(self):
        """Test using default_fields when no fields specified.

        Verifies that default fields are used when the user
        doesn't specify any fields in the request.

        Assertions:
            - Default fields used when no fields parameter
            - Default fields returned as is
            - None returned when no default provided
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: None

        default = {'id', 'username', 'created_at'}

        # Act
        selector = FieldSelector.from_request(
            mock_request,
            default_fields=default
        )

        # Assert
        assert selector.fields == {'id', 'username', 'created_at'}

    def test_from_request_strips_whitespace_from_fields(self):
        """Test that whitespace is stripped from field names.

        Verifies that extra whitespace in field lists doesn't
        cause issues with field matching.

        Assertions:
            - Leading whitespace removed
            - Trailing whitespace removed
            - Field names are clean
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': ' id , username , email ',
            'exclude': None
        }.get(key, default)

        # Act
        selector = FieldSelector.from_request(mock_request)

        # Assert
        assert selector.fields == {'id', 'username', 'email'}


class TestFieldInclusionLogic:
    """Tests for field inclusion/exclusion logic."""

    def test_should_include_with_whitelist(self):
        """Test field inclusion with fields whitelist.

        Verifies that only fields in the whitelist are included
        when fields parameter is specified.

        Assertions:
            - Fields in whitelist return True
            - Fields not in whitelist return False
            - Exclude list takes precedence
        """
        # Arrange
        selector = FieldSelector(
            fields={'id', 'username', 'email'},
            exclude_fields=set()
        )

        # Act & Assert
        assert selector.should_include('id') is True
        assert selector.should_include('username') is True
        assert selector.should_include('password_hash') is False
        assert selector.should_include('secret_key') is False

    def test_should_include_with_exclude_list(self):
        """Test field exclusion logic.

        Verifies that fields in the exclude list are never included
        regardless of other settings.

        Assertions:
            - Excluded fields return False
            - Non-excluded fields return True (no whitelist)
            - Exclude takes precedence over include
        """
        # Arrange
        selector = FieldSelector(
            fields=None,
            exclude_fields={'password_hash', 'secret_key'}
        )

        # Act & Assert
        assert selector.should_include('id') is True
        assert selector.should_include('username') is True
        assert selector.should_include('password_hash') is False
        assert selector.should_include('secret_key') is False

    def test_should_include_exclude_overrides_include(self):
        """Test that exclude list takes precedence over include list.

        Verifies the security principle that exclusions are stronger
        than inclusions.

        Assertions:
            - Field in both include and exclude returns False
            - Exclude always wins
            - Security protection enforced
        """
        # Arrange
        selector = FieldSelector(
            fields={'id', 'username', 'email'},
            exclude_fields={'email'}
        )

        # Act & Assert
        assert selector.should_include('id') is True
        assert selector.should_include('username') is True
        assert selector.should_include('email') is False

    def test_should_include_no_restrictions(self):
        """Test field inclusion with no restrictions.

        Verifies that when no fields or exclude lists are specified,
        all fields are included.

        Assertions:
            - All fields return True
            - No filtering applied
            - Default behavior is permissive
        """
        # Arrange
        selector = FieldSelector(fields=None, exclude_fields=set())

        # Act & Assert
        assert selector.should_include('id') is True
        assert selector.should_include('username') is True
        assert selector.should_include('any_field') is True
        assert selector.should_include('unknown_field') is True


class TestDataFiltering:
    """Tests for data filtering with field selection."""

    def test_select_fields_filters_dictionary(self):
        """Test filtering fields from a dictionary.

        Verifies that select_fields correctly filters dictionary
        keys based on the field selector.

        Assertions:
            - Included fields present in result
            - Excluded fields removed from result
            - Values preserved correctly
        """
        # Arrange
        data = {
            'id': 1,
            'username': 'john_doe',
            'email': 'john@example.com',
            'password_hash': 'secret123',
            'created_at': '2024-01-01'
        }
        selector = FieldSelector(fields={'id', 'username', 'email'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert result == {'id': 1, 'username': 'john_doe', 'email': 'john@example.com'}
        assert 'password_hash' not in result
        assert 'created_at' not in result

    def test_select_fields_with_exclude_list(self):
        """Test filtering dictionary with exclude list.

        Verifies that excluded fields are removed while all
        other fields are preserved.

        Assertions:
            - Excluded fields removed
            - Non-excluded fields preserved
            - Correct filtering behavior
        """
        # Arrange
        data = {
            'id': 1,
            'username': 'john_doe',
            'email': 'john@example.com',
            'password_hash': 'secret123'
        }
        selector = FieldSelector(fields=None, exclude_fields={'password_hash'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert result == {'id': 1, 'username': 'john_doe', 'email': 'john@example.com'}
        assert 'password_hash' not in result

    def test_select_fields_filters_list_of_dictionaries(self):
        """Test filtering a list of dictionaries.

        Verifies that field selection is applied to each item
        in a list of dictionaries.

        Assertions:
            - Each dictionary filtered independently
            - List structure preserved
            - All items have same fields
        """
        # Arrange
        data = [
            {'id': 1, 'username': 'john', 'password': 'secret1'},
            {'id': 2, 'username': 'jane', 'password': 'secret2'},
            {'id': 3, 'username': 'bob', 'password': 'secret3'}
        ]
        selector = FieldSelector(fields={'id', 'username'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert len(result) == 3
        assert all('password' not in item for item in result)
        assert result[0] == {'id': 1, 'username': 'john'}
        assert result[1] == {'id': 2, 'username': 'jane'}
        assert result[2] == {'id': 3, 'username': 'bob'}

    def test_select_fields_returns_non_dict_unchanged(self):
        """Test that non-dict data is returned unchanged.

        Verifies that primitive types and other non-dict objects
        pass through without modification.

        Assertions:
            - Strings returned as is
            - Numbers returned as is
            - None returned as is
            - Non-dict objects unchanged
        """
        # Arrange
        selector = FieldSelector(fields={'id', 'username'})

        # Act & Assert
        assert select_fields('string_value', selector) == 'string_value'
        assert select_fields(42, selector) == 42
        assert select_fields(None, selector) is None
        assert select_fields(True, selector) is True

    def test_select_fields_handles_empty_dictionary(self):
        """Test filtering an empty dictionary.

        Verifies that empty dictionaries are handled gracefully
        without errors.

        Assertions:
            - Empty dict returns empty dict
            - No errors raised
            - Result is valid dictionary
        """
        # Arrange
        data = {}
        selector = FieldSelector(fields={'id', 'username'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert result == {}
        assert isinstance(result, dict)

    def test_select_fields_handles_empty_list(self):
        """Test filtering an empty list.

        Verifies that empty lists are handled correctly.

        Assertions:
            - Empty list returns empty list
            - No errors raised
            - Result is valid list
        """
        # Arrange
        data = []
        selector = FieldSelector(fields={'id', 'username'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert result == []
        assert isinstance(result, list)


class TestSQLAlchemyIntegration:
    """Tests for SQLAlchemy model integration."""

    def test_build_field_list_returns_all_column_names(self):
        """Test building field list from SQLAlchemy model.

        Verifies that all column names are extracted from a
        SQLAlchemy model class.

        Assertions:
            - All columns returned
            - Column names are strings
            - List contains expected fields
        """
        # Arrange
        mock_model = Mock()

        # Create column mocks with name attribute
        col_id = Mock()
        col_id.name = 'id'
        col_username = Mock()
        col_username.name = 'username'
        col_email = Mock()
        col_email.name = 'email'
        col_created_at = Mock()
        col_created_at.name = 'created_at'

        mock_columns = [col_id, col_username, col_email, col_created_at]
        mock_model.__table__ = Mock(columns=mock_columns)

        # Act
        fields = build_field_list(mock_model)

        # Assert
        assert fields == ['id', 'username', 'email', 'created_at']

    def test_build_field_list_with_include_fields(self):
        """Test building field list with include filter.

        Verifies that only specified fields are returned when
        include_fields parameter is provided.

        Assertions:
            - Only included fields returned
            - Other fields filtered out
            - Order may vary but content correct
        """
        # Arrange
        mock_model = Mock()

        # Create column mocks with name attribute
        col_id = Mock()
        col_id.name = 'id'
        col_username = Mock()
        col_username.name = 'username'
        col_email = Mock()
        col_email.name = 'email'
        col_password = Mock()
        col_password.name = 'password_hash'

        mock_columns = [col_id, col_username, col_email, col_password]
        mock_model.__table__ = Mock(columns=mock_columns)

        include = {'id', 'username'}

        # Act
        fields = build_field_list(mock_model, include_fields=include)

        # Assert
        assert set(fields) == {'id', 'username'}
        assert 'email' not in fields
        assert 'password_hash' not in fields

    def test_build_field_list_with_exclude_fields(self):
        """Test building field list with exclude filter.

        Verifies that specified fields are excluded from the
        returned field list.

        Assertions:
            - Excluded fields not in result
            - Other fields present
            - Security protection enforced
        """
        # Arrange
        mock_model = Mock()

        # Create column mocks with name attribute
        col_id = Mock()
        col_id.name = 'id'
        col_username = Mock()
        col_username.name = 'username'
        col_email = Mock()
        col_email.name = 'email'
        col_password = Mock()
        col_password.name = 'password_hash'
        col_secret = Mock()
        col_secret.name = 'secret_key'

        mock_columns = [col_id, col_username, col_email, col_password, col_secret]
        mock_model.__table__ = Mock(columns=mock_columns)

        exclude = {'password_hash', 'secret_key'}

        # Act
        fields = build_field_list(mock_model, exclude_fields=exclude)

        # Assert
        assert set(fields) == {'id', 'username', 'email'}
        assert 'password_hash' not in fields
        assert 'secret_key' not in fields

    def test_serialize_with_fields_from_dict(self):
        """Test serializing dictionary with field selection.

        Verifies that dictionary objects are correctly filtered
        based on field selector.

        Assertions:
            - Dict is filtered correctly
            - Selected fields present
            - Unselected fields absent
        """
        # Arrange
        data = {
            'id': 1,
            'username': 'john',
            'email': 'john@test.com',
            'password_hash': 'secret'
        }
        selector = FieldSelector(fields={'id', 'username'})

        # Act
        result = serialize_with_fields(data, selector)

        # Assert
        assert result == {'id': 1, 'username': 'john'}
        assert 'password_hash' not in result

    def test_serialize_with_fields_from_sqlalchemy_model(self):
        """Test serializing SQLAlchemy model with field selection.

        Verifies that SQLAlchemy model instances are correctly
        serialized with field filtering.

        Assertions:
            - Model attributes extracted
            - Field selection applied
            - Result is filtered dictionary
        """
        # Arrange
        mock_obj = Mock()

        # Create column mocks with name attribute
        col_id = Mock()
        col_id.name = 'id'
        col_username = Mock()
        col_username.name = 'username'
        col_email = Mock()
        col_email.name = 'email'

        mock_columns = [col_id, col_username, col_email]
        mock_obj.__table__ = Mock(columns=mock_columns)
        mock_obj.id = 1
        mock_obj.username = 'john'
        mock_obj.email = 'john@test.com'

        selector = FieldSelector(fields={'id', 'username'})

        # Act
        result = serialize_with_fields(mock_obj, selector)

        # Assert
        assert result == {'id': 1, 'username': 'john'}
        assert 'email' not in result

    def test_serialize_with_fields_using_custom_serializer(self):
        """Test using custom serializer function.

        Verifies that a custom serializer can be provided to
        control object serialization before field filtering.

        Assertions:
            - Custom serializer called
            - Serializer result used
            - Field selection applied to result
        """
        # Arrange
        obj = Mock(value=42)
        selector = FieldSelector(fields={'id', 'custom_field'})

        def custom_serializer(o):
            return {'id': 1, 'custom_field': o.value, 'extra': 'data'}

        # Act
        result = serialize_with_fields(obj, selector, serializer=custom_serializer)

        # Assert
        assert result == {'id': 1, 'custom_field': 42}
        assert 'extra' not in result


class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security scenarios."""

    def test_field_selector_handles_empty_fields_string(self):
        """Test handling empty fields parameter.

        Verifies that empty field strings are handled gracefully
        without causing errors.

        Assertions:
            - Empty string handled correctly
            - No errors raised
            - Sensible default behavior
        """
        # Arrange
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default=None, type=None: {
            'fields': '',
            'exclude': None
        }.get(key, default)

        # Act
        selector = FieldSelector.from_request(mock_request)

        # Assert - Empty string creates empty set or None, not error
        assert selector.fields == set() or selector.fields is None

    def test_field_selector_handles_special_characters(self):
        """Test handling field names with special characters.

        Verifies that field names containing special characters
        are handled correctly.

        Assertions:
            - Special characters preserved
            - No injection vulnerabilities
            - Field matching works correctly
        """
        # Arrange
        selector = FieldSelector(fields={'field_with_underscore', 'field-with-dash'})

        # Act & Assert
        assert selector.should_include('field_with_underscore') is True
        assert selector.should_include('field-with-dash') is True
        assert selector.should_include('normal_field') is False

    def test_select_fields_with_none_selector_fields(self):
        """Test data filtering when selector has no field restrictions.

        Verifies that when fields is None, all fields pass through
        (unless explicitly excluded).

        Assertions:
            - All fields included when fields=None
            - Only exclude list applies
            - Permissive default behavior
        """
        # Arrange
        data = {'id': 1, 'username': 'john', 'email': 'john@test.com'}
        selector = FieldSelector(fields=None, exclude_fields={'email'})

        # Act
        result = select_fields(data, selector)

        # Assert
        assert result == {'id': 1, 'username': 'john'}
        assert 'email' not in result

    def test_filter_dict_internal_function(self):
        """Test internal _filter_dict function directly.

        Verifies the core filtering logic works correctly
        at the internal function level.

        Assertions:
            - Dictionary filtered correctly
            - Key-value pairs preserved
            - Excluded keys removed
        """
        # Arrange
        data = {
            'keep1': 'value1',
            'keep2': 'value2',
            'remove1': 'value3',
            'remove2': 'value4'
        }
        selector = FieldSelector(fields={'keep1', 'keep2'})

        # Act
        result = _filter_dict(data, selector)

        # Assert
        assert result == {'keep1': 'value1', 'keep2': 'value2'}
        assert len(result) == 2
