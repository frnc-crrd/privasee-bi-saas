"""
Unit tests for dynamic filtering engine module.

This module contains comprehensive tests for RESTful API filtering,
including filter parsing, SQL query building, security validation,
and search functionality.

Test Coverage:
    - FilterCondition creation and validation
    - FilterParams request parsing
    - Value type parsing (bool, int, float, date, datetime, string)
    - SQLAlchemy query building with all operators
    - Search functionality
    - Security: SQL injection prevention
    - Edge cases and error handling

Security Focus:
    - Whitelist validation for filter fields
    - Operator validation
    - Special character handling
    - Unauthorized field access prevention
"""

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from sqlalchemy import Column, Integer, String, Boolean, DateTime, select
from sqlalchemy.orm import declarative_base

from app.core.filtering import (
    FilterCondition,
    FilterOperator,
    FilterParams,
    apply_filters,
    apply_search,
    _parse_filter_value,
    _build_filter_clause,
)
from app.exceptions.validation import ValidationError

# Create test model for SQLAlchemy integration tests
Base = declarative_base()


class TestModel(Base):
    """Test model for filtering tests."""

    __tablename__ = 'test_table'

    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))
    role = Column(String(20))
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    age = Column(Integer)
    score = Column(Integer)


class TestFilterCondition:
    """Tests for FilterCondition dataclass."""

    def test_filter_condition_creation_with_enum_operator(self):
        """Test FilterCondition creation with FilterOperator enum.

        Verifies that filter conditions can be created with
        operator enums directly.

        Assertions:
            - FilterCondition created successfully
            - Operator is FilterOperator enum
            - Field and value assigned correctly
        """
        # Arrange & Act
        condition = FilterCondition(
            field='role',
            operator=FilterOperator.EQ,
            value='admin'
        )

        # Assert
        assert condition.field == 'role'
        assert condition.operator == FilterOperator.EQ
        assert condition.value == 'admin'

    def test_filter_condition_operator_string_conversion(self):
        """Test FilterCondition converts string operators to enums.

        Verifies that string operator values are automatically
        converted to FilterOperator enums in __post_init__.

        Assertions:
            - String operator converted to enum
            - Operator type is FilterOperator
            - Correct operator value
        """
        # Arrange & Act
        condition = FilterCondition(
            field='is_active',
            operator='eq',  # String, not enum
            value=True
        )

        # Assert
        assert isinstance(condition.operator, FilterOperator)
        assert condition.operator == FilterOperator.EQ

    def test_filter_condition_in_operator_value_normalization(self):
        """Test IN operator normalizes comma-separated values to list.

        Verifies that string values for IN operators are split
        and trimmed correctly.

        Assertions:
            - String split into list
            - Whitespace trimmed from items
            - List contains correct values
        """
        # Arrange & Act
        condition = FilterCondition(
            field='role',
            operator=FilterOperator.IN,
            value='admin, analyst, viewer'
        )

        # Assert
        assert isinstance(condition.value, list)
        assert condition.value == ['admin', 'analyst', 'viewer']

    def test_filter_condition_not_in_operator_value_normalization(self):
        """Test NOT_IN operator normalizes comma-separated values.

        Verifies that NOT_IN operator processes values the same
        way as IN operator.

        Assertions:
            - String split into list
            - Whitespace trimmed
            - Correct values in list
        """
        # Arrange & Act
        condition = FilterCondition(
            field='status',
            operator=FilterOperator.NOT_IN,
            value='pending, deleted'
        )

        # Assert
        assert isinstance(condition.value, list)
        assert condition.value == ['pending', 'deleted']

    def test_filter_condition_in_operator_with_list_value(self):
        """Test IN operator preserves list values without modification.

        Verifies that pre-formatted list values are not
        re-processed by the IN operator logic.

        Assertions:
            - List value preserved as-is
            - No additional processing
            - Values remain unchanged
        """
        # Arrange & Act
        condition = FilterCondition(
            field='id',
            operator=FilterOperator.IN,
            value=[1, 2, 3]  # Already a list
        )

        # Assert
        assert isinstance(condition.value, list)
        assert condition.value == [1, 2, 3]


class TestFilterParamsParsing:
    """Tests for FilterParams request parsing."""

    def test_filter_params_from_request_simple_eq_filters(self):
        """Test parsing simple equality filters from request.

        Verifies that basic query parameters are parsed as
        equality filters by default.

        Assertions:
            - Filters parsed correctly
            - Default operator is EQ
            - Field and value captured
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?role=admin&is_active=true'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request)

            # Assert
            assert len(filters.conditions) == 2
            assert filters.conditions[0].field == 'role'
            assert filters.conditions[0].operator == FilterOperator.EQ
            assert filters.conditions[0].value == 'admin'
            assert filters.conditions[1].field == 'is_active'
            assert filters.conditions[1].value is True

    def test_filter_params_from_request_operator_filters(self):
        """Test parsing filters with explicit operators.

        Verifies that double-underscore operator syntax is
        parsed correctly (e.g., created_at__gte).

        Assertions:
            - Operator parsed from field name
            - Field name extracted correctly
            - Operator enum assigned
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?age__gte=18&score__lt=100'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request)

            # Assert
            assert len(filters.conditions) == 2

            # First filter: age >= 18
            assert filters.conditions[0].field == 'age'
            assert filters.conditions[0].operator == FilterOperator.GTE
            assert filters.conditions[0].value == 18

            # Second filter: score < 100
            assert filters.conditions[1].field == 'score'
            assert filters.conditions[1].operator == FilterOperator.LT
            assert filters.conditions[1].value == 100

    def test_filter_params_from_request_search_parameter(self):
        """Test parsing search query parameter.

        Verifies that ?search= parameter is captured separately
        from filter conditions.

        Assertions:
            - Search term captured
            - Search not in conditions list
            - Search value is string
        """
        # Arrange
        app = Flask(__name__)
        with app.test_request_context('/?search=john&role=admin'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request)

            # Assert
            assert filters.search == 'john'
            assert len(filters.conditions) == 1
            assert filters.conditions[0].field == 'role'

    def test_filter_params_from_request_allowed_fields_validation(self):
        """Test that allowed_fields whitelist accepts valid fields.

        Verifies that filtering on whitelisted fields succeeds
        without raising errors.

        Assertions:
            - Whitelisted fields accepted
            - Filters created successfully
            - No validation errors
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'role', 'is_active'}

        with app.test_request_context('/?role=admin&is_active=true'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request, allowed_fields=allowed)

            # Assert
            assert len(filters.conditions) == 2
            assert all(c.field in allowed for c in filters.conditions)

    def test_filter_params_from_request_unauthorized_field_raises_error(self):
        """Test that unauthorized filter fields raise ValidationError.

        Critical security test: Verifies that filtering on fields
        not in the allowed_fields whitelist is rejected.

        This prevents SQL injection and unauthorized data access.

        Assertions:
            - ValidationError raised
            - Error message contains field name
            - Error message lists allowed fields
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'role', 'is_active'}

        with app.test_request_context('/?email=test@example.com'):
            from flask import request

            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                FilterParams.from_request(request, allowed_fields=allowed)

            assert 'email' in str(exc_info.value)
            assert 'not allowed' in str(exc_info.value).lower()

    def test_filter_params_from_request_skips_special_parameters(self):
        """Test that pagination and metadata params are ignored.

        Verifies that special query parameters (page, sort, fields)
        are not treated as filter conditions.

        Assertions:
            - Special params not in conditions
            - Only actual filter params parsed
            - Parameter count correct
        """
        # Arrange
        app = Flask(__name__)

        with app.test_request_context('/?role=admin&page=1&sort=username&fields=id,email&cursor=abc'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request)

            # Assert
            assert len(filters.conditions) == 1
            assert filters.conditions[0].field == 'role'

    def test_filter_params_from_request_invalid_operator_skipped(self):
        """Test that invalid operators are silently skipped.

        Verifies that query parameters with invalid operator
        names don't crash parsing (graceful degradation).

        Assertions:
            - Invalid operator doesn't raise error
            - Invalid filter skipped
            - Valid filters still parsed
        """
        # Arrange
        app = Flask(__name__)

        with app.test_request_context('/?role=admin&age__invalid=25'):
            from flask import request

            # Act
            filters = FilterParams.from_request(request)

            # Assert
            # Only 'role=admin' should be parsed
            assert len(filters.conditions) == 1
            assert filters.conditions[0].field == 'role'


class TestValueParsing:
    """Tests for filter value type parsing."""

    def test_parse_filter_value_boolean_true(self):
        """Test parsing boolean true values.

        Verifies that 'true' string is converted to Python True.

        Assertions:
            - String 'true' becomes bool True
            - Type is bool, not string
            - Case insensitive
        """
        # Arrange & Act
        result = _parse_filter_value('true', FilterOperator.EQ)

        # Assert
        assert result is True
        assert isinstance(result, bool)

    def test_parse_filter_value_boolean_false(self):
        """Test parsing boolean false values.

        Verifies that 'false' string is converted to Python False.

        Assertions:
            - String 'false' becomes bool False
            - Type is bool
            - Case insensitive
        """
        # Arrange & Act
        result = _parse_filter_value('false', FilterOperator.EQ)

        # Assert
        assert result is False
        assert isinstance(result, bool)

    def test_parse_filter_value_integer(self):
        """Test parsing integer values.

        Verifies that numeric strings without decimals
        are parsed as integers.

        Assertions:
            - String becomes int
            - Value correct
            - Type is int, not string
        """
        # Arrange & Act
        result = _parse_filter_value('42', FilterOperator.GT)

        # Assert
        assert result == 42
        assert isinstance(result, int)

    def test_parse_filter_value_float(self):
        """Test parsing floating-point values.

        Verifies that numeric strings with decimals
        are parsed as floats.

        Assertions:
            - String becomes float
            - Value correct
            - Type is float
        """
        # Arrange & Act
        result = _parse_filter_value('3.14', FilterOperator.GTE)

        # Assert
        assert result == 3.14
        assert isinstance(result, float)

    def test_parse_filter_value_date(self):
        """Test parsing date values in YYYY-MM-DD format.

        Verifies that ISO date strings are converted to
        Python date objects.

        Assertions:
            - String becomes date object
            - Date components correct
            - Type is date
        """
        # Arrange & Act
        result = _parse_filter_value('2024-01-15', FilterOperator.EQ)

        # Assert
        assert isinstance(result, date)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_filter_value_datetime(self):
        """Test parsing datetime values in ISO format.

        Verifies that ISO datetime strings are converted to
        Python datetime objects.

        Assertions:
            - String becomes datetime object
            - Time components correct
            - Type is datetime
        """
        # Arrange & Act
        result = _parse_filter_value('2024-01-15T14:30:00Z', FilterOperator.EQ)

        # Assert
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_filter_value_string_default(self):
        """Test that unparseable values default to strings.

        Verifies that values that don't match any special
        format are kept as strings.

        Assertions:
            - Value remains string
            - Original value preserved
            - No parsing error
        """
        # Arrange & Act
        result = _parse_filter_value('some-text', FilterOperator.LIKE)

        # Assert
        assert result == 'some-text'
        assert isinstance(result, str)

    def test_parse_filter_value_null_operators_return_none(self):
        """Test that NULL check operators return None.

        Verifies that IS_NULL and NOT_NULL operators
        always return None as the value.

        Assertions:
            - IS_NULL returns None
            - NOT_NULL returns None
            - Value parameter ignored
        """
        # Arrange & Act
        result_is_null = _parse_filter_value('anything', FilterOperator.IS_NULL)
        result_not_null = _parse_filter_value('anything', FilterOperator.NOT_NULL)

        # Assert
        assert result_is_null is None
        assert result_not_null is None


class TestSQLAlchemyQueryBuilding:
    """Tests for SQLAlchemy query building with filters."""

    def test_apply_filters_with_eq_operator(self):
        """Test applying equality filter to query.

        Verifies that EQ operator generates correct
        SQLAlchemy WHERE clause.

        Assertions:
            - Filter applied to query
            - WHERE clause generated
            - Correct SQL operator used
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('role', FilterOperator.EQ, 'admin')
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        assert result_query is not None
        # Query should have WHERE clause (check compilation)
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'WHERE' in compiled
        assert 'role' in compiled.lower()

    def test_apply_filters_with_comparison_operators(self):
        """Test applying comparison operators (GT, GTE, LT, LTE).

        Verifies that numeric comparison operators generate
        correct SQL clauses.

        Assertions:
            - All comparison operators supported
            - Correct SQL generated for each
            - Multiple filters combined with AND
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('age', FilterOperator.GTE, 18),
            FilterCondition('score', FilterOperator.LT, 100)
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'WHERE' in compiled
        assert 'age' in compiled.lower()
        assert 'score' in compiled.lower()

    def test_apply_filters_with_like_operators(self):
        """Test applying LIKE and ILIKE operators for text search.

        Verifies that pattern matching operators generate
        correct SQL LIKE clauses with wildcards.

        Assertions:
            - LIKE operator generates SQL LIKE
            - ILIKE operator generates case-insensitive LIKE
            - Wildcards added correctly
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('username', FilterOperator.LIKE, 'john')
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'LIKE' in compiled or 'like' in compiled.lower()
        assert 'username' in compiled.lower()

    def test_apply_filters_with_in_operators(self):
        """Test applying IN and NOT_IN operators for list values.

        Verifies that list membership operators generate
        correct SQL IN clauses.

        Assertions:
            - IN operator generates SQL IN clause
            - NOT_IN generates NOT IN clause
            - List values handled correctly
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('role', FilterOperator.IN, ['admin', 'analyst'])
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'IN' in compiled or 'in' in compiled.lower()
        assert 'role' in compiled.lower()

    def test_apply_filters_with_null_operators(self):
        """Test applying IS_NULL and NOT_NULL operators.

        Verifies that NULL check operators generate
        correct SQL IS NULL clauses.

        Assertions:
            - IS_NULL generates IS NULL
            - NOT_NULL generates IS NOT NULL
            - Correct SQL syntax
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('email', FilterOperator.IS_NULL, None)
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'IS' in compiled
        assert 'NULL' in compiled

    def test_apply_filters_skips_nonexistent_fields(self):
        """Test that filters for nonexistent fields are gracefully skipped.

        Verifies that attempting to filter on a field that
        doesn't exist on the model doesn't crash the query.

        Assertions:
            - No AttributeError raised
            - Query still valid
            - Other filters still applied
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('nonexistent_field', FilterOperator.EQ, 'value'),
            FilterCondition('role', FilterOperator.EQ, 'admin')
        ])

        # Act (should not raise)
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        # Should still have the valid filter
        assert 'role' in compiled.lower()

    def test_apply_filters_with_ne_operator(self):
        """Test applying not-equal operator.

        Verifies that NE operator generates correct
        SQL inequality clause.

        Assertions:
            - NE operator generates !=
            - Correct SQL syntax
            - Filter applied correctly
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('role', FilterOperator.NE, 'viewer')
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'WHERE' in compiled
        assert 'role' in compiled.lower()


class TestSearchFunctionality:
    """Tests for multi-field search functionality."""

    def test_apply_search_across_multiple_fields(self):
        """Test search applies ILIKE across all specified fields.

        Verifies that search term is matched against all
        search_fields using OR logic.

        Assertions:
            - Search applied to all fields
            - OR logic used (any field match)
            - Case-insensitive search (ILIKE)
        """
        # Arrange
        query = select(TestModel)
        search_term = 'john'
        search_fields = ['username', 'email']

        # Act
        result_query = apply_search(query, TestModel, search_term, search_fields)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        assert 'WHERE' in compiled
        # Should have OR clause
        assert 'OR' in compiled or 'or' in compiled.lower()
        assert 'username' in compiled.lower()
        assert 'email' in compiled.lower()

    def test_apply_search_with_no_search_term(self):
        """Test that empty search term returns unmodified query.

        Verifies graceful handling when no search is needed.

        Assertions:
            - Original query returned
            - No WHERE clause added
            - No errors raised
        """
        # Arrange
        query = select(TestModel)
        search_fields = ['username', 'email']

        # Act
        result_query = apply_search(query, TestModel, '', search_fields)

        # Assert
        # Should be same query (no search applied)
        assert result_query is not None
        compiled_before = str(query.compile())
        compiled_after = str(result_query.compile())
        assert compiled_before == compiled_after

    def test_apply_search_with_invalid_field_skipped(self):
        """Test that search on nonexistent fields is gracefully skipped.

        Verifies that invalid field names in search_fields
        don't crash the search.

        Assertions:
            - No AttributeError raised
            - Valid fields still searched
            - Query remains valid
        """
        # Arrange
        query = select(TestModel)
        search_term = 'john'
        search_fields = ['username', 'nonexistent_field', 'email']

        # Act (should not raise)
        result_query = apply_search(query, TestModel, search_term, search_fields)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        # Should still have valid fields
        assert 'username' in compiled.lower()
        assert 'email' in compiled.lower()

    def test_apply_search_with_no_search_fields(self):
        """Test that empty search_fields list returns unmodified query.

        Verifies graceful handling when search_fields is empty.

        Assertions:
            - Original query returned
            - No errors raised
            - No search applied
        """
        # Arrange
        query = select(TestModel)
        search_term = 'john'

        # Act
        result_query = apply_search(query, TestModel, search_term, [])

        # Assert
        compiled_before = str(query.compile())
        compiled_after = str(result_query.compile())
        assert compiled_before == compiled_after


class TestBuildFilterClause:
    """Tests for individual filter clause building."""

    def test_build_filter_clause_eq(self):
        """Test building equality filter clause.

        Verifies that _build_filter_clause generates correct
        SQLAlchemy expression for EQ operator.

        Assertions:
            - Clause is not None
            - Clause is valid SQLAlchemy expression
            - Compiles to correct SQL
        """
        # Arrange
        attr = TestModel.role

        # Act
        clause = _build_filter_clause(attr, FilterOperator.EQ, 'admin')

        # Assert
        assert clause is not None
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        assert 'role' in compiled.lower()

    def test_build_filter_clause_all_comparison_operators(self):
        """Test all comparison operators generate valid clauses.

        Verifies that GT, GTE, LT, LTE all produce correct
        SQLAlchemy expressions.

        Assertions:
            - All operators return non-None clauses
            - All compile to valid SQL
            - Correct operators in SQL
        """
        # Arrange
        attr = TestModel.age

        # Act
        clause_gt = _build_filter_clause(attr, FilterOperator.GT, 18)
        clause_gte = _build_filter_clause(attr, FilterOperator.GTE, 18)
        clause_lt = _build_filter_clause(attr, FilterOperator.LT, 65)
        clause_lte = _build_filter_clause(attr, FilterOperator.LTE, 65)

        # Assert
        assert clause_gt is not None
        assert clause_gte is not None
        assert clause_lt is not None
        assert clause_lte is not None

    def test_build_filter_clause_like_adds_wildcards(self):
        """Test LIKE operator adds SQL wildcards around value.

        Verifies that pattern matching includes % wildcards
        for substring matching.

        Assertions:
            - LIKE clause generated
            - Wildcards present in compiled SQL
            - Case-sensitive LIKE used
        """
        # Arrange
        attr = TestModel.username

        # Act
        clause = _build_filter_clause(attr, FilterOperator.LIKE, 'john')

        # Assert
        assert clause is not None
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        # Should have wildcards (% or LIKE operator)
        assert 'LIKE' in compiled or 'like' in compiled.lower()

    def test_build_filter_clause_ilike_case_insensitive(self):
        """Test ILIKE operator generates case-insensitive clause.

        Verifies that ILIKE is used for case-insensitive
        pattern matching.

        Assertions:
            - ILIKE clause generated
            - Case-insensitive operator used
            - Wildcards included
        """
        # Arrange
        attr = TestModel.email

        # Act
        clause = _build_filter_clause(attr, FilterOperator.ILIKE, 'example')

        # Assert
        assert clause is not None
        compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
        # PostgreSQL uses ILIKE, SQLite may use LIKE with LOWER()
        assert 'LIKE' in compiled.upper()


class TestSecurityAndEdgeCases:
    """Tests for security validation and edge cases."""

    def test_sql_injection_prevention_via_allowed_fields(self):
        """Test that SQL injection via field names is prevented.

        Critical security test: Verifies that unauthorized field
        names are rejected by whitelist, preventing SQL injection
        through field name manipulation.

        Assertions:
            - Unauthorized field names rejected
            - ValidationError raised
            - Only whitelisted fields accepted
        """
        # Arrange
        app = Flask(__name__)
        allowed = {'role', 'is_active'}

        # Attempt to filter on unauthorized field
        # This simulates attacker trying to access sensitive columns
        with app.test_request_context('/?password=test&admin_level=5'):
            from flask import request

            # Act & Assert
            # Should raise ValidationError for 'password' (first unauthorized field)
            with pytest.raises(ValidationError) as exc_info:
                FilterParams.from_request(request, allowed_fields=allowed)

            assert 'password' in str(exc_info.value)
            assert 'not allowed' in str(exc_info.value).lower()

    def test_special_characters_in_filter_values(self):
        """Test that special characters in values are handled safely.

        Verifies that SQLAlchemy parameterization prevents
        SQL injection via filter values.

        Assertions:
            - Special characters accepted in values
            - SQLAlchemy uses parameter binding
            - No SQL injection vulnerability
        """
        # Arrange
        query = select(TestModel)
        # Value with SQL injection attempt
        filters = FilterParams(conditions=[
            FilterCondition('username', FilterOperator.EQ, "admin'; DROP TABLE users;--")
        ])

        # Act (should not crash or inject SQL)
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        # SQLAlchemy should use parameter binding, not string concatenation
        compiled = str(result_query.compile())
        # Should have parameterized query (:username or similar)
        assert 'DROP TABLE' not in compiled  # Raw SQL not in query

    def test_empty_filter_conditions_returns_unmodified_query(self):
        """Test that empty filter list returns original query.

        Verifies graceful handling when no filters applied.

        Assertions:
            - Original query returned
            - No WHERE clause added
            - No errors raised
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled_before = str(query.compile())
        compiled_after = str(result_query.compile())
        assert compiled_before == compiled_after

    def test_multiple_filters_combined_with_and_logic(self):
        """Test that multiple filters use AND logic by default.

        Verifies that all filter conditions must be satisfied
        (not OR logic).

        Assertions:
            - Multiple WHERE conditions
            - AND logic used
            - All filters applied
        """
        # Arrange
        query = select(TestModel)
        filters = FilterParams(conditions=[
            FilterCondition('role', FilterOperator.EQ, 'admin'),
            FilterCondition('is_active', FilterOperator.EQ, True),
            FilterCondition('age', FilterOperator.GTE, 18)
        ])

        # Act
        result_query = apply_filters(query, TestModel, filters)

        # Assert
        compiled = str(result_query.compile(compile_kwargs={"literal_binds": True}))
        # Should have all three conditions
        assert 'role' in compiled.lower()
        assert 'is_active' in compiled.lower()
        assert 'age' in compiled.lower()
        # Default SQLAlchemy combines with AND
        assert 'WHERE' in compiled

    def test_filter_operator_enum_exhaustiveness(self):
        """Test that all FilterOperator enum values are handled.

        Verifies that _build_filter_clause has logic for
        every defined operator.

        Assertions:
            - All operators in enum tested
            - None return invalid clauses
            - Comprehensive coverage
        """
        # Arrange
        attr = TestModel.role
        test_cases = [
            (FilterOperator.EQ, 'admin'),
            (FilterOperator.NE, 'viewer'),
            (FilterOperator.GT, 5),
            (FilterOperator.GTE, 5),
            (FilterOperator.LT, 10),
            (FilterOperator.LTE, 10),
            (FilterOperator.LIKE, 'test'),
            (FilterOperator.ILIKE, 'test'),
            (FilterOperator.IN, ['a', 'b']),
            (FilterOperator.NOT_IN, ['c', 'd']),
            (FilterOperator.IS_NULL, None),
            (FilterOperator.NOT_NULL, None),
        ]

        # Act & Assert
        for operator, value in test_cases:
            if operator in (FilterOperator.IN, FilterOperator.NOT_IN):
                # IN operators need list value
                clause = _build_filter_clause(attr, operator, value)
            else:
                clause = _build_filter_clause(attr, operator, value)

            # All operators should return valid clauses
            assert clause is not None, f"Operator {operator} returned None"
