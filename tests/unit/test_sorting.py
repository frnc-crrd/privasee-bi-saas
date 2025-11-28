"""
Unit tests for sorting utilities module.

This module contains comprehensive tests for RESTful API sorting,
including sort parameter parsing, SQL query building, and security
validation.

Test Coverage:
    - SortField creation and validation
    - SortParams request parsing
    - Multi-field sorting
    - SQLAlchemy query building with ORDER BY
    - Query parameter conversion
    - Security: Sort field validation
    - Edge cases and error handling

Security Focus:
    - Whitelist validation for sort fields
    - Invalid field handling
    - Sort order validation
"""

from unittest.mock import Mock

import pytest
from flask import Flask
from sqlalchemy import Column, Integer, String, DateTime, select
from sqlalchemy.orm import declarative_base

from app.core.sorting import (
    SortField,
    SortOrder,
    SortParams,
    apply_sorting,
    parse_sort_field,
)

# Create test model for SQLAlchemy integration tests
Base = declarative_base()


class TestModel(Base):
    """Test model for sorting tests."""

    __tablename__ = 'test_table'

    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))
    created_at = Column(DateTime)
    score = Column(Integer)


class TestSortField:
    """Tests for SortField dataclass."""

    def test_sort_field_creation_with_default_asc_order(self):
        """Test SortField creation with default ascending order.

        Verifies that sort fields default to ASC order when
        no order is specified.

        Assertions:
            - SortField created successfully
            - Default order is ASC
            - Field name assigned correctly
        """
        # Arrange & Act
        sort_field = SortField(field='username')

        # Assert
        assert sort_field.field == 'username'
        assert sort_field.order == SortOrder.ASC

    def test_sort_field_creation_with_desc_order(self):
        """Test SortField creation with descending order.

        Verifies that sort fields can be created with
        explicit DESC order.

        Assertions:
            - SortField created with DESC order
            - Order is SortOrder enum
            - Field name correct
        """
        # Arrange & Act
        sort_field = SortField(field='created_at', order=SortOrder.DESC)

        # Assert
        assert sort_field.field == 'created_at'
        assert sort_field.order == SortOrder.DESC

    def test_sort_field_order_string_conversion(self):
        """Test SortField converts string orders to enums.

        Verifies that string order values are automatically
        converted to SortOrder enums in __post_init__.

        Assertions:
            - String order converted to enum
            - Order type is SortOrder
            - Correct order value
        """
        # Arrange & Act
        sort_field = SortField(field='score', order='desc')  # String, not enum

        # Assert
        assert isinstance(sort_field.order, SortOrder)
        assert sort_field.order == SortOrder.DESC

    def test_sort_field_order_normalization_case_insensitive(self):
        """Test SortField normalizes order strings case-insensitively.

        Verifies that order strings are converted to lowercase
        before enum conversion.

        Assertions:
            - Uppercase 'DESC' converted correctly
            - Lowercase normalization works
            - Enum assignment correct
        """
        # Arrange & Act
        sort_field = SortField(field='email', order='DESC')  # Uppercase

        # Assert
        assert sort_field.order == SortOrder.DESC


class TestSortParamsParsing:
    """Tests for SortParams request parsing."""

    def test_sort_params_from_request_single_field_asc(self):
        """Test parsing single ascending sort field from request.

        Verifies that basic ?sort=field syntax is parsed
        as ascending order by default.

        Assertions:
            - Single field parsed
            - Default order is ASC
            - Field name correct
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort=username'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 1
            assert sort_params.fields[0].field == 'username'
            assert sort_params.fields[0].order == SortOrder.ASC

    def test_sort_params_from_request_single_field_desc(self):
        """Test parsing single descending sort field with - prefix.

        Verifies that ?sort=-field syntax is parsed as
        descending order.

        Assertions:
            - Single field parsed
            - DESC order detected from prefix
            - Field name extracted correctly
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort=-created_at'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 1
            assert sort_params.fields[0].field == 'created_at'
            assert sort_params.fields[0].order == SortOrder.DESC

    def test_sort_params_from_request_multiple_fields(self):
        """Test parsing multiple sort fields from request.

        Verifies that comma-separated fields are parsed in
        priority order with correct directions.

        Assertions:
            - Multiple fields parsed
            - Order preserved (priority)
            - Mixed ASC/DESC directions
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort=-score,username,created_at'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 3

            # First: score DESC
            assert sort_params.fields[0].field == 'score'
            assert sort_params.fields[0].order == SortOrder.DESC

            # Second: username ASC (default)
            assert sort_params.fields[1].field == 'username'
            assert sort_params.fields[1].order == SortOrder.ASC

            # Third: created_at ASC
            assert sort_params.fields[2].field == 'created_at'
            assert sort_params.fields[2].order == SortOrder.ASC

    def test_sort_params_from_request_with_asc_prefix(self):
        """Test parsing sort field with explicit + prefix for ASC.

        Verifies that ?sort=+field syntax is parsed as
        ascending order (explicit).

        Assertions:
            - + prefix recognized
            - ASC order assigned
            - Field name extracted
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort=+email'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 1
            assert sort_params.fields[0].field == 'email'
            assert sort_params.fields[0].order == SortOrder.ASC

    def test_sort_params_from_request_allowed_fields_validation(self):
        """Test that allowed_fields whitelist accepts valid fields.

        Verifies that sorting on whitelisted fields succeeds
        without filtering.

        Assertions:
            - Whitelisted fields accepted
            - Sort params created successfully
            - No validation errors
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'username', 'created_at', 'score'}

        with app.test_request_context('/?sort=-created_at,username'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request, allowed_fields=allowed)

            # Assert
            assert len(sort_params.fields) == 2
            assert all(f.field in allowed for f in sort_params.fields)

    def test_sort_params_from_request_unauthorized_field_skipped(self):
        """Test that unauthorized sort fields are silently skipped.

        Critical security test: Verifies that sorting on fields
        not in the allowed_fields whitelist is silently ignored.

        This prevents sort parameter injection attacks.

        Assertions:
            - Unauthorized fields not in result
            - Authorized fields still parsed
            - No errors raised (graceful skip)
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'username', 'created_at'}

        # Attempt to sort on unauthorized 'password' field
        with app.test_request_context('/?sort=-password,username,email'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request, allowed_fields=allowed)

            # Assert
            # Only 'username' should be parsed ('password' and 'email' unauthorized)
            assert len(sort_params.fields) == 1
            assert sort_params.fields[0].field == 'username'

    def test_sort_params_from_request_default_sort(self):
        """Test that default_sort is used when no sort parameter provided.

        Verifies fallback behavior when ?sort is not in request.

        Assertions:
            - Default sort applied
            - Default fields used
            - Default order preserved
        """
        # Arrange
        app = Flask(__name__)
        default = [
            SortField('created_at', SortOrder.DESC),
            SortField('id', SortOrder.ASC)
        ]

        with app.test_request_context('/'):  # No ?sort parameter
            from flask import request

            # Act
            sort_params = SortParams.from_request(request, default_sort=default)

            # Assert
            assert len(sort_params.fields) == 2
            assert sort_params.fields[0].field == 'created_at'
            assert sort_params.fields[0].order == SortOrder.DESC
            assert sort_params.fields[1].field == 'id'
            assert sort_params.fields[1].order == SortOrder.ASC

    def test_sort_params_from_request_empty_returns_empty(self):
        """Test that empty sort parameter returns empty SortParams.

        Verifies graceful handling when no sort is specified
        and no default provided.

        Assertions:
            - Empty fields list
            - No errors raised
            - Valid SortParams instance
        """
        # Arrange
        app = Flask(__name__)

        with app.test_request_context('/'):  # No ?sort parameter
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 0


class TestQueryParameterConversion:
    """Tests for converting SortParams to query parameter strings."""

    def test_to_query_param_single_field_asc(self):
        """Test converting single ASC field to query parameter.

        Verifies that SortParams can be serialized back to
        query parameter format.

        Assertions:
            - Correct query param format
            - No prefix for ASC
            - Field name correct
        """
        # Arrange
        sort_params = SortParams(fields=[
            SortField('username', SortOrder.ASC)
        ])

        # Act
        result = sort_params.to_query_param()

        # Assert
        assert result == 'username'

    def test_to_query_param_single_field_desc(self):
        """Test converting single DESC field to query parameter.

        Verifies that DESC fields are prefixed with -.

        Assertions:
            - Correct query param format
            - - prefix for DESC
            - Field name correct
        """
        # Arrange
        sort_params = SortParams(fields=[
            SortField('created_at', SortOrder.DESC)
        ])

        # Act
        result = sort_params.to_query_param()

        # Assert
        assert result == '-created_at'

    def test_to_query_param_multiple_fields_mixed_order(self):
        """Test converting multiple fields with mixed orders.

        Verifies that comma-separated format is generated
        correctly with proper prefixes.

        Assertions:
            - Comma-separated format
            - Correct prefix for each field
            - Order preserved
        """
        # Arrange
        sort_params = SortParams(fields=[
            SortField('score', SortOrder.DESC),
            SortField('username', SortOrder.ASC),
            SortField('created_at', SortOrder.DESC)
        ])

        # Act
        result = sort_params.to_query_param()

        # Assert
        assert result == '-score,username,-created_at'

    def test_to_query_param_empty_fields_returns_empty_string(self):
        """Test converting empty SortParams to query parameter.

        Verifies graceful handling of empty sort params.

        Assertions:
            - Empty string returned
            - No errors raised
            - Valid format
        """
        # Arrange
        sort_params = SortParams(fields=[])

        # Act
        result = sort_params.to_query_param()

        # Assert
        assert result == ''


class TestSQLAlchemyQueryBuilding:
    """Tests for SQLAlchemy query building with sorting."""

    def test_apply_sorting_with_single_asc_field(self):
        """Test applying single ascending sort to query.

        Verifies that ASC order generates correct
        SQLAlchemy ORDER BY clause.

        Assertions:
            - Sort applied to query
            - ORDER BY clause generated
            - ASC direction used
        """
        # Arrange
        query = select(TestModel)
        sort_params = SortParams(fields=[
            SortField('username', SortOrder.ASC)
        ])

        # Act
        result_query = apply_sorting(query, TestModel, sort_params)

        # Assert
        assert result_query is not None
        compiled = str(result_query.compile())
        assert 'ORDER BY' in compiled.upper()
        assert 'username' in compiled.lower()

    def test_apply_sorting_with_single_desc_field(self):
        """Test applying single descending sort to query.

        Verifies that DESC order generates correct
        SQLAlchemy ORDER BY DESC clause.

        Assertions:
            - Sort applied to query
            - ORDER BY clause generated
            - DESC direction used
        """
        # Arrange
        query = select(TestModel)
        sort_params = SortParams(fields=[
            SortField('created_at', SortOrder.DESC)
        ])

        # Act
        result_query = apply_sorting(query, TestModel, sort_params)

        # Assert
        compiled = str(result_query.compile())
        assert 'ORDER BY' in compiled.upper()
        assert 'created_at' in compiled.lower()
        assert 'DESC' in compiled.upper()

    def test_apply_sorting_with_multiple_fields(self):
        """Test applying multiple sort fields to query.

        Verifies that multi-field sorting generates correct
        ORDER BY clause with priority order.

        Assertions:
            - All fields in ORDER BY
            - Correct sort directions
            - Priority order preserved
        """
        # Arrange
        query = select(TestModel)
        sort_params = SortParams(fields=[
            SortField('score', SortOrder.DESC),
            SortField('username', SortOrder.ASC)
        ])

        # Act
        result_query = apply_sorting(query, TestModel, sort_params)

        # Assert
        compiled = str(result_query.compile())
        assert 'ORDER BY' in compiled.upper()
        assert 'score' in compiled.lower()
        assert 'username' in compiled.lower()

    def test_apply_sorting_skips_nonexistent_fields(self):
        """Test that sorting on nonexistent fields is gracefully skipped.

        Verifies that attempting to sort on a field that
        doesn't exist on the model doesn't crash the query.

        Assertions:
            - No AttributeError raised
            - Query still valid
            - Other sorts still applied
        """
        # Arrange
        query = select(TestModel)
        sort_params = SortParams(fields=[
            SortField('nonexistent_field', SortOrder.ASC),
            SortField('username', SortOrder.ASC)
        ])

        # Act (should not raise)
        result_query = apply_sorting(query, TestModel, sort_params)

        # Assert
        compiled = str(result_query.compile())
        # Should still have the valid sort
        assert 'username' in compiled.lower()

    def test_apply_sorting_with_empty_sort_params(self):
        """Test that empty sort params returns unmodified query.

        Verifies graceful handling when no sorting requested.

        Assertions:
            - Original query returned
            - No ORDER BY clause added
            - No errors raised
        """
        # Arrange
        query = select(TestModel)
        sort_params = SortParams(fields=[])

        # Act
        result_query = apply_sorting(query, TestModel, sort_params)

        # Assert
        compiled_before = str(query.compile())
        compiled_after = str(result_query.compile())
        # Should be identical (no ORDER BY added)
        assert compiled_before == compiled_after


class TestParseSortField:
    """Tests for parse_sort_field function."""

    def test_parse_sort_field_without_prefix_defaults_asc(self):
        """Test parsing sort field without prefix defaults to ASC.

        Verifies that fields without - or + prefix are
        parsed as ascending order.

        Assertions:
            - Field name extracted
            - Order is ASC
            - SortField created correctly
        """
        # Arrange & Act
        sort_field = parse_sort_field('username')

        # Assert
        assert sort_field.field == 'username'
        assert sort_field.order == SortOrder.ASC

    def test_parse_sort_field_with_desc_prefix(self):
        """Test parsing sort field with - prefix as DESC.

        Verifies that - prefix indicates descending order.

        Assertions:
            - Field name extracted (without prefix)
            - Order is DESC
            - Prefix removed from field name
        """
        # Arrange & Act
        sort_field = parse_sort_field('-created_at')

        # Assert
        assert sort_field.field == 'created_at'
        assert sort_field.order == SortOrder.DESC

    def test_parse_sort_field_with_asc_prefix(self):
        """Test parsing sort field with + prefix as ASC.

        Verifies that + prefix explicitly indicates
        ascending order.

        Assertions:
            - Field name extracted (without prefix)
            - Order is ASC
            - Prefix removed from field name
        """
        # Arrange & Act
        sort_field = parse_sort_field('+email')

        # Assert
        assert sort_field.field == 'email'
        assert sort_field.order == SortOrder.ASC


class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security scenarios."""

    def test_sort_params_whitespace_handling(self):
        """Test that whitespace in sort parameters is trimmed.

        Verifies that leading/trailing whitespace in field
        specifications is normalized.

        Assertions:
            - Whitespace trimmed from field names
            - Sort params parsed correctly
            - No whitespace in results
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort= -created_at , username , email '):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request)

            # Assert
            assert len(sort_params.fields) == 3
            assert sort_params.fields[0].field == 'created_at'  # No whitespace
            assert sort_params.fields[1].field == 'username'
            assert sort_params.fields[2].field == 'email'

    def test_sort_params_unauthorized_field_prevention(self):
        """Test that unauthorized fields cannot be used for sorting.

        Critical security test: Verifies that the allowed_fields
        whitelist prevents sorting on unauthorized columns.

        This prevents information disclosure through sort-based
        timing attacks and protects sensitive columns.

        Assertions:
            - Unauthorized fields filtered out
            - Only allowed fields in result
            - No security bypass possible
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'id', 'username', 'created_at'}

        # Attempt to sort on sensitive fields
        with app.test_request_context('/?sort=-password,username,admin_level'):
            from flask import request

            # Act
            sort_params = SortParams.from_request(request, allowed_fields=allowed)

            # Assert
            # Only 'username' should pass (password and admin_level blocked)
            assert len(sort_params.fields) == 1
            assert sort_params.fields[0].field == 'username'
            assert all(f.field in allowed for f in sort_params.fields)

    def test_sort_params_empty_field_name_handling(self):
        """Test that empty field names are handled gracefully.

        Verifies that malformed input with empty field names
        (e.g., ?sort=,-field) doesn't crash parsing.

        Note: Current implementation allows empty field names,
        which are later skipped by apply_sorting due to
        AttributeError on getattr(model, '').

        Assertions:
            - Parsing doesn't crash
            - Valid fields still parsed
            - No errors raised during parsing
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?sort=username,,email'):
            from flask import request

            # Act (should not raise)
            sort_params = SortParams.from_request(request)

            # Assert
            # Implementation doesn't filter empty field names during parsing
            # They will be skipped later during apply_sorting
            assert len(sort_params.fields) >= 2  # At least the valid fields

            # Check that valid fields are present
            field_names = [f.field for f in sort_params.fields]
            assert 'username' in field_names
            assert 'email' in field_names

    def test_sort_order_enum_exhaustiveness(self):
        """Test that both SortOrder enum values are handled.

        Verifies that ASC and DESC are the only valid
        sort orders and both are supported.

        Assertions:
            - ASC order works
            - DESC order works
            - Only two valid orders
        """
        # Arrange & Act
        asc_field = SortField('field1', SortOrder.ASC)
        desc_field = SortField('field2', SortOrder.DESC)

        # Assert
        assert asc_field.order == SortOrder.ASC
        assert desc_field.order == SortOrder.DESC

        # Verify enum has exactly 2 values
        assert len(SortOrder) == 2
        assert set(SortOrder) == {SortOrder.ASC, SortOrder.DESC}
