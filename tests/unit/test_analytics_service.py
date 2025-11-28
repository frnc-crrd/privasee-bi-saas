"""
Unit tests for analytics service module.

This module contains comprehensive tests for business intelligence
and analytics operations using DuckDB and Ibis Framework.

Test Coverage:
    - Sales summary with date range filtering
    - Product performance analysis
    - Location-based analytics
    - Time-series trends with period validation
    - Category breakdown
    - Table schema operations
    - Custom query execution
    - Date validation
    - Error handling and logging

Business Value:
    - Data-driven decision making
    - Performance metrics tracking
    - Sales trend analysis
"""

from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
from functools import wraps

import pytest
from flask import Flask

from app.services.analytics_service import AnalyticsService
from app.exceptions.base import DatabaseException
from app.exceptions.validation import ValidationError


@pytest.fixture(autouse=True)
def mock_cache():
    """Mock the cache object to bypass caching in tests."""
    mock_cache_obj = Mock()
    mock_cache_obj.get.return_value = None  # Always return cache miss
    mock_cache_obj.set.return_value = None  # Do nothing on set

    with patch('app.core.cache.cache', mock_cache_obj):
        yield mock_cache_obj


class TestSalesSummary:
    """Tests for sales summary analytics."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_summary_success_with_date_range(self, mock_repo_class):
        """Test retrieving sales summary with date range filtering.

        Verifies that sales summary query works correctly with
        start and end date parameters.

        Args:
            mock_repo_class: Mocked AnalyticsRepository class

        Assertions:
            - Repository method called with correct parameters
            - Summary data returned
            - Date range applied correctly
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_summary.return_value = {
            'total_sales': 150000.50,
            'order_count': 350,
            'avg_order_value': 428.57
        }
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_sales_summary(
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

        # Assert
        assert result['total_sales'] == 150000.50
        assert result['order_count'] == 350
        mock_repo.get_sales_summary.assert_called_once_with(
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_summary_without_date_filter(self, mock_repo_class):
        """Test retrieving sales summary without date filtering.

        Verifies that summary query works when no dates provided
        (returns all-time data).

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Repository called with None dates
            - All-time data returned
            - No validation errors
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_summary.return_value = {
            'total_sales': 500000.00,
            'order_count': 1000,
            'avg_order_value': 500.00
        }
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_sales_summary()

        # Assert
        assert result['total_sales'] == 500000.00
        mock_repo.get_sales_summary.assert_called_once_with(
            start_date=None,
            end_date=None
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_summary_invalid_date_format_raises_error(self, mock_repo_class):
        """Test that invalid date format raises ValidationError.

        Verifies date validation prevents malformed date strings
        from reaching the database layer.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError raised for invalid date
            - Error message contains date format info
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.get_sales_summary(start_date='2024/01/01')  # Wrong format

        assert 'Invalid date format' in str(exc_info.value)
        assert 'YYYY-MM-DD' in str(exc_info.value)
        mock_repo.get_sales_summary.assert_not_called()

    @patch('app.services.analytics_service.current_app')
    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_summary_database_error_handling(self, mock_repo_class, mock_app):
        """Test error handling when database query fails.

        Verifies that database errors are caught, logged, and
        re-raised as DatabaseException.

        Args:
            mock_repo_class: Mocked repository
            mock_app: Mocked Flask app

        Assertions:
            - DatabaseException raised
            - Error logged
            - Original exception wrapped
        """
        # Arrange
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_repo = Mock()
        mock_repo.get_sales_summary.side_effect = Exception('DuckDB connection lost')
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_sales_summary()

        assert 'Failed to retrieve sales summary' in str(exc_info.value)
        mock_logger.error.assert_called_once()


class TestProductPerformance:
    """Tests for product performance analytics."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_product_performance_success_with_limit(self, mock_repo_class):
        """Test retrieving top performing products with limit.

        Verifies that product performance query respects the
        limit parameter for top N products.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Repository called with correct limit
            - Product list returned
            - Limit respected
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_top_products.return_value = [
            {'product_id': 1, 'name': 'Product A', 'sales': 50000},
            {'product_id': 2, 'name': 'Product B', 'sales': 40000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_product_performance(limit=10, start_date='2024-01-01')

        # Assert
        assert len(result) == 2
        assert result[0]['name'] == 'Product A'
        mock_repo.get_top_products.assert_called_once_with(
            limit=10,
            start_date='2024-01-01',
            end_date=None
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_product_performance_invalid_limit_zero(self, mock_repo_class):
        """Test that limit of zero raises ValidationError.

        Verifies that invalid limit values are rejected before
        querying the database.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError raised for limit=0
            - Error message descriptive
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.get_product_performance(limit=0)

        assert 'Limit must be between 1 and 1000' in str(exc_info.value)
        mock_repo.get_top_products.assert_not_called()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_product_performance_invalid_limit_exceeds_maximum(self, mock_repo_class):
        """Test that limit exceeding 1000 raises ValidationError.

        Prevents excessively large result sets that could
        impact performance.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError raised for limit > 1000
            - Maximum limit enforced
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.get_product_performance(limit=1500)

        assert 'Limit must be between 1 and 1000' in str(exc_info.value)
        mock_repo.get_top_products.assert_not_called()

    @patch('app.services.analytics_service.current_app')
    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_product_performance_database_error(self, mock_repo_class, mock_app):
        """Test database error handling in product performance query.

        Args:
            mock_repo_class: Mocked repository
            mock_app: Mocked app

        Assertions:
            - DatabaseException raised
            - Error logged
            - Graceful failure
        """
        # Arrange
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_repo = Mock()
        mock_repo.get_top_products.side_effect = Exception('Query timeout')
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_product_performance(limit=10)

        assert 'Failed to retrieve product performance' in str(exc_info.value)
        mock_logger.error.assert_called_once()


class TestLocationPerformance:
    """Tests for location-based analytics."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_location_performance_success(self, mock_repo_class):
        """Test retrieving sales performance by location.

        Verifies that location performance query returns
        sales data grouped by Sucursal.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Location data returned
            - Repository called with correct params
            - Data structured correctly
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_location.return_value = [
            {'location': 'Sucursal A', 'sales': 100000},
            {'location': 'Sucursal B', 'sales': 85000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_location_performance(limit=20)

        # Assert
        assert len(result) == 2
        assert result[0]['location'] == 'Sucursal A'
        mock_repo.get_sales_by_location.assert_called_once()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_location_performance_invalid_limit(self, mock_repo_class):
        """Test limit validation for location performance.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError for invalid limit
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError):
            service.get_location_performance(limit=-5)

        mock_repo.get_sales_by_location.assert_not_called()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_location_performance_with_date_range(self, mock_repo_class):
        """Test location performance with date filtering.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Date validation applied
            - Repository called with date parameters
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_location.return_value = [
            {'location': 'Sucursal A', 'total_sales': 50000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_location_performance(
            limit=10,
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

        # Assert
        assert len(result) == 1
        mock_repo.get_sales_by_location.assert_called_once_with(
            limit=10,
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    @patch('app.services.analytics_service.current_app')
    def test_get_location_performance_database_error(self, mock_app, mock_repo_class):
        """Test database error handling in location performance.

        Args:
            mock_app: Mocked Flask app
            mock_repo_class: Mocked repository

        Assertions:
            - DatabaseException raised on error
            - Error logged
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_location.side_effect = Exception("Database connection failed")
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_location_performance(limit=10)

        assert "Failed to retrieve location performance" in str(exc_info.value)
        mock_app.logger.error.assert_called_once()


class TestSalesTrends:
    """Tests for time-series sales trend analysis."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_trends_monthly_period(self, mock_repo_class):
        """Test retrieving sales trends with monthly aggregation.

        Verifies that time-series data is correctly aggregated
        by month.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Monthly trends returned
            - Repository called with correct period
            - Time-series structure valid
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_trends.return_value = [
            {'period': '2024-01', 'sales': 50000},
            {'period': '2024-02', 'sales': 55000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_sales_trends(period='monthly', start_date='2024-01-01')

        # Assert
        assert len(result) == 2
        assert result[0]['period'] == '2024-01'
        mock_repo.get_sales_trends.assert_called_once_with(
            period='monthly',
            start_date='2024-01-01',
            end_date=None
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_trends_daily_period(self, mock_repo_class):
        """Test retrieving sales trends with daily aggregation.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Daily trends returned
            - Correct period parameter
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_trends.return_value = [
            {'period': '2024-01-01', 'sales': 2000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_sales_trends(period='daily')

        # Assert
        assert len(result) == 1
        mock_repo.get_sales_trends.assert_called_once()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_trends_invalid_period_raises_error(self, mock_repo_class):
        """Test that invalid period raises ValidationError.

        Verifies that only allowed period values are accepted
        (daily, weekly, monthly, yearly).

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError raised for invalid period
            - Error message lists valid options
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.get_sales_trends(period='hourly')  # Invalid period

        assert 'Invalid period' in str(exc_info.value)
        assert 'daily, weekly, monthly, yearly' in str(exc_info.value)
        mock_repo.get_sales_trends.assert_not_called()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_sales_trends_with_date_range(self, mock_repo_class):
        """Test sales trends with date filtering.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Date validation applied
            - Repository called with date parameters
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_trends.return_value = [
            {'period': '2024-01', 'sales': 50000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_sales_trends(
            period='monthly',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

        # Assert
        assert len(result) == 1
        mock_repo.get_sales_trends.assert_called_once_with(
            period='monthly',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    @patch('app.services.analytics_service.current_app')
    def test_get_sales_trends_database_error(self, mock_app, mock_repo_class):
        """Test database error handling in sales trends.

        Args:
            mock_app: Mocked Flask app
            mock_repo_class: Mocked repository

        Assertions:
            - DatabaseException raised on error
            - Error logged
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_trends.side_effect = Exception("Query timeout")
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_sales_trends(period='daily')

        assert "Failed to retrieve sales trends" in str(exc_info.value)
        mock_app.logger.error.assert_called_once()


class TestCategoryBreakdown:
    """Tests for product category sales breakdown."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_category_breakdown_linea_type(self, mock_repo_class):
        """Test category breakdown by Linea.

        Verifies that sales can be grouped by product line
        (Linea category type).

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Category data returned
            - Linea type used
            - Repository called correctly
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_category.return_value = [
            {'category': 'Electronics', 'sales': 120000},
            {'category': 'Furniture', 'sales': 95000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_category_breakdown(category_type='linea')

        # Assert
        assert len(result) == 2
        assert result[0]['category'] == 'Electronics'
        mock_repo.get_sales_by_category.assert_called_once_with(
            category_type='linea',
            start_date=None,
            end_date=None
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_category_breakdown_sub_linea_type(self, mock_repo_class):
        """Test category breakdown by Sub_Linea.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Sub_Linea breakdown works
            - Correct category type passed
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_category.return_value = [
            {'category': 'Smartphones', 'sales': 50000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_category_breakdown(category_type='sub_linea')

        # Assert
        assert len(result) == 1
        mock_repo.get_sales_by_category.assert_called_once()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_category_breakdown_invalid_type_raises_error(self, mock_repo_class):
        """Test that invalid category type raises ValidationError.

        Verifies only valid category types accepted (linea, sub_linea).

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError for invalid type
            - Valid types listed in error
            - Repository not called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service.get_category_breakdown(category_type='invalid_type')

        assert 'Invalid category type' in str(exc_info.value)
        assert 'linea, sub_linea' in str(exc_info.value)
        mock_repo.get_sales_by_category.assert_not_called()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_category_breakdown_with_date_range(self, mock_repo_class):
        """Test category breakdown with date filtering.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Date validation applied
            - Repository called with date parameters
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_category.return_value = [
            {'category': 'Electronics', 'sales': 80000}
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_category_breakdown(
            category_type='linea',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

        # Assert
        assert len(result) == 1
        mock_repo.get_sales_by_category.assert_called_once_with(
            category_type='linea',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )

    @patch('app.services.analytics_service.AnalyticsRepository')
    @patch('app.services.analytics_service.current_app')
    def test_get_category_breakdown_database_error(self, mock_app, mock_repo_class):
        """Test database error handling in category breakdown.

        Args:
            mock_app: Mocked Flask app
            mock_repo_class: Mocked repository

        Assertions:
            - DatabaseException raised on error
            - Error logged
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_sales_by_category.side_effect = Exception("Connection lost")
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_category_breakdown(category_type='linea')

        assert "Failed to retrieve category breakdown" in str(exc_info.value)
        mock_app.logger.error.assert_called_once()


class TestTableOperations:
    """Tests for table schema and metadata operations."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_available_tables_success(self, mock_repo_class):
        """Test retrieving list of available tables in analytical cube.

        Verifies that table listing works correctly.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Table list returned
            - Expected tables present
            - Repository method called
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.list_tables.return_value = [
            'Sucursal',
            'Productos',
            'Linea',
            'Sub_Linea'
        ]
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_available_tables()

        # Assert
        assert len(result) == 4
        assert 'Productos' in result
        assert 'Sucursal' in result
        mock_repo.list_tables.assert_called_once()

    @patch('app.services.analytics_service.AnalyticsRepository')
    @patch('app.services.analytics_service.current_app')
    def test_get_available_tables_database_error(self, mock_app, mock_repo_class):
        """Test database error handling in get_available_tables.

        Args:
            mock_app: Mocked Flask app
            mock_repo_class: Mocked repository

        Assertions:
            - DatabaseException raised on error
            - Error logged
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.list_tables.side_effect = Exception("Database unavailable")
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.get_available_tables()

        assert "Failed to list tables" in str(exc_info.value)
        mock_app.logger.error.assert_called_once()

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_table_schema_success(self, mock_repo_class):
        """Test retrieving schema information for a table.

        Verifies that column metadata can be retrieved.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Schema dictionary returned
            - Column names and types present
            - Repository called with table name
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_table_schema.return_value = {
            'product_id': 'INTEGER',
            'name': 'VARCHAR',
            'price': 'DECIMAL'
        }
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        result = service.get_table_schema('Productos')

        # Assert
        assert result['product_id'] == 'INTEGER'
        assert result['name'] == 'VARCHAR'
        mock_repo.get_table_schema.assert_called_once_with('Productos')

    @patch('app.services.analytics_service.current_app')
    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_get_table_schema_invalid_table_raises_error(self, mock_repo_class, mock_app):
        """Test error handling for nonexistent table.

        Args:
            mock_repo_class: Mocked repository
            mock_app: Mocked app

        Assertions:
            - DatabaseException raised
            - Error logged
        """
        # Arrange
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_repo = Mock()
        mock_repo.get_table_schema.side_effect = Exception('Table not found')
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(DatabaseException):
            service.get_table_schema('NonExistentTable')

        mock_logger.error.assert_called_once()


class TestCustomQueryExecution:
    """Tests for custom Ibis query execution."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_execute_custom_query_success(self, mock_repo_class):
        """Test executing custom Ibis query function.

        Verifies that custom queries can be executed with
        proper connection management.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Query function executed
            - Connection obtained
            - Result returned
        """
        # Arrange
        mock_connection = Mock()
        mock_repo = Mock()
        mock_repo.get_connection.return_value = mock_connection
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        def custom_query_func(con):
            return {'custom_result': 'data'}

        # Act
        result = service.execute_custom_query(custom_query_func)

        # Assert
        assert result == {'custom_result': 'data'}
        mock_repo.get_connection.assert_called_once()

    @patch('app.services.analytics_service.current_app')
    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_execute_custom_query_error_handling(self, mock_repo_class, mock_app):
        """Test error handling in custom query execution.

        Args:
            mock_repo_class: Mocked repository
            mock_app: Mocked app

        Assertions:
            - DatabaseException raised on error
            - Error logged
            - Graceful failure
        """
        # Arrange
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_repo = Mock()
        mock_repo.get_connection.side_effect = Exception('Connection failed')
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        def failing_query(con):
            return con.table('table').execute()

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            service.execute_custom_query(failing_query)

        assert 'Query execution failed' in str(exc_info.value)
        mock_logger.error.assert_called_once()


class TestDateValidation:
    """Tests for date format validation."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_validate_date_format_valid_date(self, mock_repo_class):
        """Test that valid ISO date format passes validation.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - No exception raised for valid date
            - Date string accepted
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert (should not raise)
        service._validate_date_format('2024-01-01')
        service._validate_date_format('2024-12-31')

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_validate_date_format_invalid_format(self, mock_repo_class):
        """Test that invalid date format raises ValidationError.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - ValidationError raised
            - Error message contains expected format
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            service._validate_date_format('01/01/2024')  # MM/DD/YYYY format

        assert 'Invalid date format' in str(exc_info.value)
        assert 'YYYY-MM-DD' in str(exc_info.value)


class TestConnectionManagement:
    """Tests for connection lifecycle management."""

    @patch('app.services.analytics_service.AnalyticsRepository')
    def test_close_connection_calls_repository_close(self, mock_repo_class):
        """Test that close_connection properly closes repository.

        Verifies resource cleanup is delegated to repository.

        Args:
            mock_repo_class: Mocked repository

        Assertions:
            - Repository close method called
            - Connection resources freed
        """
        # Arrange
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        service = AnalyticsService()

        # Act
        service.close_connection()

        # Assert
        mock_repo.close.assert_called_once()
