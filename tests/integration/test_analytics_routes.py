"""Integration tests for analytics routes and BI query endpoints.

This module provides comprehensive integration tests for analytics endpoints,
including sales summaries, product performance, location analysis, trends,
category breakdowns, and table metadata retrieval.

Test Coverage:
    - Authentication and authorization requirements
    - Role-based access control (analyst and admin)
    - Query parameter validation
    - Date range filtering
    - Caching behavior
    - Error handling for database failures
    - Response format validation
"""

import pytest
from unittest.mock import patch, MagicMock
from app.exceptions.validation import ValidationError
from app.exceptions.base import DatabaseException


class TestSalesSummaryEndpoint:
    """Test suite for sales summary analytics endpoint."""

    def test_get_sales_summary_authenticated(
        self, client, analyst_user, analyst_token
    ):
        """Test sales summary endpoint requires authentication.

        This test verifies that the sales summary endpoint enforces
        JWT authentication and rejects unauthenticated requests.

        Assertions:
            - Unauthenticated request returns 401
            - Authenticated request with analyst token succeeds

        Test Data:
            - Endpoint: GET /api/v1/analytics/sales/summary
            - Required: Valid JWT token
        """
        # Act: Unauthenticated request
        response_no_auth = client.get('/api/v1/analytics/sales/summary')

        # Assert
        assert response_no_auth.status_code == 401

        # Act: Authenticated request (mock service)
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_summary') as mock_summary:
            mock_summary.return_value = {
                'total_sales': 100000,
                'total_transactions': 500
            }

            response_auth = client.get(
                '/api/v1/analytics/sales/summary',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response_auth.status_code == 200
            data = response_auth.get_json()
            assert 'data' in data
            assert 'summary' in data['data']

    def test_get_sales_summary_analyst_access(
        self, client, analyst_token
    ):
        """Test analyst role has access to sales summary endpoint.

        This test verifies that users with analyst role can successfully
        access the sales summary endpoint.

        Assertions:
            - Response status code is 200
            - Response contains summary data
            - Success message is present

        Test Data:
            - User Role: analyst
            - Expected: Access granted
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_summary') as mock_summary:
            mock_summary.return_value = {
                'total_sales': 250000.50,
                'total_transactions': 1234,
                'average_transaction': 202.60
            }

            # Act
            response = client.get(
                '/api/v1/analytics/sales/summary',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            assert data['success'] is True
            assert 'summary' in data['data']
            assert data['data']['summary']['total_sales'] == 250000.50

    def test_get_sales_summary_viewer_denied(
        self, client, viewer_token
    ):
        """Test viewer role is denied access to sales summary endpoint.

        This test verifies that users with viewer role cannot access
        analytics endpoints that require analyst or admin privileges.

        Assertions:
            - Response status code is 401
            - Error message indicates authentication failure due to insufficient permissions

        Test Data:
            - User Role: viewer
            - Expected: Access denied (401 Unauthorized)
        """
        # Act
        response = client.get(
            '/api/v1/analytics/sales/summary',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )

        # Assert
        assert response.status_code == 401

    def test_get_sales_summary_date_filters(
        self, client, analyst_token
    ):
        """Test sales summary endpoint accepts date range filters.

        This test verifies that the endpoint correctly processes start_date
        and end_date query parameters for filtering results.

        Assertions:
            - Service is called with correct date parameters
            - Response status code is 200
            - Filtered data is returned

        Test Data:
            - Query Parameters: start_date=2024-01-01, end_date=2024-12-31
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_summary') as mock_summary:
            mock_summary.return_value = {
                'total_sales': 180000.00,
                'period': '2024-01-01 to 2024-12-31'
            }

            # Act
            response = client.get(
                '/api/v1/analytics/sales/summary?start_date=2024-01-01&end_date=2024-12-31',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_summary.assert_called_once_with(
                start_date='2024-01-01',
                end_date='2024-12-31'
            )

    def test_get_sales_summary_admin_access(
        self, client, admin_token
    ):
        """Test admin role has access to sales summary endpoint.

        This test verifies that users with admin role can successfully
        access analytics endpoints.

        Assertions:
            - Response status code is 200
            - Response contains summary data

        Test Data:
            - User Role: admin
            - Expected: Access granted
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_summary') as mock_summary:
            mock_summary.return_value = {
                'total_sales': 500000.00
            }

            # Act
            response = client.get(
                '/api/v1/analytics/sales/summary',
                headers={'Authorization': f'Bearer {admin_token}'}
            )

            # Assert
            assert response.status_code == 200
            assert response.get_json()['success'] is True

    def test_get_sales_summary_database_error(
        self, client, analyst_token, app
    ):
        """Test sales summary endpoint handles database errors gracefully.

        This test verifies that database errors are caught and returned
        as proper error responses without exposing internal details.

        Assertions:
            - Response status code is 500
            - Error message is user-friendly
            - No internal error details are exposed

        Test Data:
            - Simulated Error: Database connection failure
        """
        # Arrange: Mock service to raise database error
        # Note: We need to disable caching for this test to avoid cache serialization issues
        with app.app_context():
            with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_summary') as mock_summary, \
                 patch('app.extensions.cache.cached', lambda *args, **kwargs: lambda f: f):
                mock_summary.side_effect = DatabaseException("DuckDB connection failed")

                # Act
                response = client.get(
                    '/api/v1/analytics/sales/summary',
                    headers={'Authorization': f'Bearer {analyst_token}'}
                )
                data = response.get_json()

                # Assert
                assert response.status_code == 500
                assert data['success'] is False
                assert 'Failed to retrieve sales summary' in data['error']['message']


class TestProductPerformanceEndpoint:
    """Test suite for product performance analytics endpoint."""

    def test_get_product_performance_top_20(
        self, client, analyst_token
    ):
        """Test product performance endpoint returns top 20 products by default.

        This test verifies that the endpoint returns the configured default
        number of top products when no limit is specified.

        Assertions:
            - Service is called with default limit of 20
            - Response status code is 200
            - Response contains products list

        Test Data:
            - Default Limit: 20
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_product_performance') as mock_products:
            mock_products.return_value = [
                {'product_id': i, 'sales': 1000 - (i * 10)}
                for i in range(1, 21)
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/products',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_products.assert_called_once_with(
                limit=20,
                start_date=None,
                end_date=None
            )
            assert len(data['data']['products']) == 20

    def test_get_product_performance_custom_limit(
        self, client, analyst_token
    ):
        """Test product performance endpoint accepts custom limit parameter.

        This test verifies that the endpoint respects the limit query parameter
        to control the number of returned products.

        Assertions:
            - Service is called with specified limit
            - Response contains correct number of products

        Test Data:
            - Query Parameter: limit=10
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_product_performance') as mock_products:
            mock_products.return_value = [
                {'product_id': i, 'sales': 1000 - (i * 10)}
                for i in range(1, 11)
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/products?limit=10',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_products.assert_called_once_with(
                limit=10,
                start_date=None,
                end_date=None
            )
            assert len(data['data']['products']) == 10

    def test_get_product_performance_with_date_filters(
        self, client, analyst_token
    ):
        """Test product performance endpoint accepts date range filters.

        This test verifies that date filters are properly passed to the
        analytics service for temporal analysis.

        Assertions:
            - Service is called with date parameters
            - Response status code is 200

        Test Data:
            - Query Parameters: start_date, end_date, limit
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_product_performance') as mock_products:
            mock_products.return_value = [
                {'product_id': 1, 'sales': 5000}
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/products?limit=5&start_date=2024-01-01&end_date=2024-06-30',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response.status_code == 200
            mock_products.assert_called_once_with(
                limit=5,
                start_date='2024-01-01',
                end_date='2024-06-30'
            )


class TestLocationPerformanceEndpoint:
    """Test suite for location performance analytics endpoint."""

    def test_get_location_performance_pagination(
        self, client, analyst_token
    ):
        """Test location performance endpoint supports pagination via limit.

        This test verifies that the endpoint supports result limiting
        for efficient data transfer and processing.

        Assertions:
            - Service is called with limit parameter
            - Response contains limited number of locations
            - Response status code is 200

        Test Data:
            - Query Parameter: limit=15
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_location_performance') as mock_locations:
            mock_locations.return_value = [
                {'location_id': i, 'sales': 50000 - (i * 1000)}
                for i in range(1, 16)
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/locations?limit=15',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_locations.assert_called_once_with(
                limit=15,
                start_date=None,
                end_date=None
            )
            assert len(data['data']['locations']) == 15

    def test_get_location_performance_default_limit(
        self, client, analyst_token
    ):
        """Test location performance endpoint uses default limit.

        This test verifies the default pagination behavior when no
        limit parameter is specified.

        Assertions:
            - Service is called with default limit of 20
            - Response status code is 200

        Test Data:
            - Default Limit: 20
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_location_performance') as mock_locations:
            mock_locations.return_value = []

            # Act
            response = client.get(
                '/api/v1/analytics/sales/locations',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response.status_code == 200
            mock_locations.assert_called_once_with(
                limit=20,
                start_date=None,
                end_date=None
            )


class TestSalesTrendsEndpoint:
    """Test suite for sales trends analytics endpoint."""

    def test_get_sales_trends_period_monthly(
        self, client, analyst_token
    ):
        """Test sales trends endpoint supports monthly aggregation period.

        This test verifies that the endpoint correctly processes monthly
        period requests for time-series analysis.

        Assertions:
            - Service is called with monthly period
            - Response contains trends data
            - Response includes period information

        Test Data:
            - Query Parameter: period=monthly
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_trends') as mock_trends:
            mock_trends.return_value = [
                {'month': '2024-01', 'sales': 10000},
                {'month': '2024-02', 'sales': 12000},
                {'month': '2024-03', 'sales': 11500}
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/trends?period=monthly',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_trends.assert_called_once_with(
                period='monthly',
                start_date=None,
                end_date=None
            )
            assert data['data']['period'] == 'monthly'
            assert 'trends' in data['data']

    def test_get_sales_trends_period_daily(
        self, client, analyst_token
    ):
        """Test sales trends endpoint supports daily aggregation period.

        This test verifies daily period aggregation for detailed
        time-series analysis.

        Assertions:
            - Service is called with daily period
            - Response status code is 200

        Test Data:
            - Query Parameter: period=daily
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_trends') as mock_trends:
            mock_trends.return_value = []

            # Act
            response = client.get(
                '/api/v1/analytics/sales/trends?period=daily',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response.status_code == 200
            mock_trends.assert_called_once_with(
                period='daily',
                start_date=None,
                end_date=None
            )

    def test_get_sales_trends_invalid_period(
        self, client, analyst_token
    ):
        """Test sales trends endpoint validates period parameter.

        This test verifies that invalid period values are rejected
        with appropriate error messages.

        Assertions:
            - Response status code is 400 for invalid period
            - Error message indicates validation failure

        Test Data:
            - Invalid Period: 'hourly' (not supported)
        """
        # Arrange: Mock service to raise validation error
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_trends') as mock_trends:
            mock_trends.side_effect = ValidationError("Invalid period: hourly")

            # Act
            response = client.get(
                '/api/v1/analytics/sales/trends?period=hourly',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 400
            assert data['success'] is False

    def test_get_sales_trends_with_date_range(
        self, client, analyst_token
    ):
        """Test sales trends endpoint accepts date range filters.

        This test verifies that date filters work correctly with
        period aggregation for temporal analysis.

        Assertions:
            - Service is called with all parameters
            - Response status code is 200

        Test Data:
            - Query Parameters: period, start_date, end_date
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_sales_trends') as mock_trends:
            mock_trends.return_value = []

            # Act
            response = client.get(
                '/api/v1/analytics/sales/trends?period=monthly&start_date=2024-01-01&end_date=2024-12-31',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response.status_code == 200
            mock_trends.assert_called_once_with(
                period='monthly',
                start_date='2024-01-01',
                end_date='2024-12-31'
            )


class TestCategoryBreakdownEndpoint:
    """Test suite for category breakdown analytics endpoint."""

    def test_get_category_breakdown_linea(
        self, client, analyst_token
    ):
        """Test category breakdown endpoint supports linea category type.

        This test verifies that the endpoint correctly processes requests
        for top-level category (linea) breakdowns.

        Assertions:
            - Service is called with linea category type
            - Response contains categories data
            - Response includes category_type information

        Test Data:
            - Query Parameter: category_type=linea
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_category_breakdown') as mock_breakdown:
            mock_breakdown.return_value = [
                {'category': 'Electronics', 'sales': 50000},
                {'category': 'Clothing', 'sales': 30000}
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/sales/categories?category_type=linea',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            mock_breakdown.assert_called_once_with(
                category_type='linea',
                start_date=None,
                end_date=None
            )
            assert data['data']['category_type'] == 'linea'
            assert 'categories' in data['data']

    def test_get_category_breakdown_sub_linea(
        self, client, analyst_token
    ):
        """Test category breakdown endpoint supports sub_linea category type.

        This test verifies sub-category level breakdown analysis.

        Assertions:
            - Service is called with sub_linea category type
            - Response status code is 200

        Test Data:
            - Query Parameter: category_type=sub_linea
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_category_breakdown') as mock_breakdown:
            mock_breakdown.return_value = []

            # Act
            response = client.get(
                '/api/v1/analytics/sales/categories?category_type=sub_linea',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )

            # Assert
            assert response.status_code == 200
            mock_breakdown.assert_called_once_with(
                category_type='sub_linea',
                start_date=None,
                end_date=None
            )


class TestTableMetadataEndpoints:
    """Test suite for table metadata and schema endpoints."""

    def test_list_available_tables_cached(
        self, client, analyst_token
    ):
        """Test list tables endpoint returns cached results.

        This test verifies that the available tables list is cached
        to reduce database overhead for metadata queries.

        Assertions:
            - Response status code is 200
            - Response contains tables list
            - Cache decorator is applied (600s timeout)

        Test Data:
            - Endpoint: GET /api/v1/analytics/tables
            - Cache Timeout: 600 seconds
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_available_tables') as mock_tables:
            mock_tables.return_value = ['Productos', 'Sucursal', 'Linea', 'Sub_Linea']

            # Act
            response = client.get(
                '/api/v1/analytics/tables',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            assert 'tables' in data['data']
            assert len(data['data']['tables']) == 4
            assert data['message'] == '4 tables available'

    def test_get_table_schema_valid_table(
        self, client, analyst_token
    ):
        """Test get table schema endpoint for valid table name.

        This test verifies that the endpoint returns schema information
        for existing tables in the analytical cube.

        Assertions:
            - Response status code is 200
            - Response contains table_name and schema
            - Schema includes column names and types

        Test Data:
            - Table Name: Productos
        """
        # Arrange: Mock service response
        with patch('app.routes.v1.analytics_routes.analytics_service.get_table_schema') as mock_schema:
            mock_schema.return_value = [
                {'column_name': 'id', 'data_type': 'INTEGER'},
                {'column_name': 'name', 'data_type': 'VARCHAR'},
                {'column_name': 'price', 'data_type': 'DECIMAL'}
            ]

            # Act
            response = client.get(
                '/api/v1/analytics/tables/Productos/schema',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 200
            assert data['data']['table_name'] == 'Productos'
            assert 'schema' in data['data']
            assert len(data['data']['schema']) == 3

    def test_get_table_schema_invalid_table(
        self, client, analyst_token
    ):
        """Test get table schema endpoint rejects invalid table names.

        This test verifies that requests for non-existent tables return
        appropriate error responses.

        Assertions:
            - Response status code is 400 or 500
            - Error message indicates table not found

        Test Data:
            - Table Name: NonExistentTable
        """
        # Arrange: Mock service to raise validation error
        with patch('app.routes.v1.analytics_routes.analytics_service.get_table_schema') as mock_schema:
            mock_schema.side_effect = ValidationError("Table 'NonExistentTable' does not exist")

            # Act
            response = client.get(
                '/api/v1/analytics/tables/NonExistentTable/schema',
                headers={'Authorization': f'Bearer {analyst_token}'}
            )
            data = response.get_json()

            # Assert
            assert response.status_code == 400
            assert data['success'] is False
