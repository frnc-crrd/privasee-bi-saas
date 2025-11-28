"""
Unit tests for analytics repository module.

This module contains comprehensive tests for DuckDB-based analytical
queries using the Ibis framework.

Test Coverage:
    - DuckDB connection initialization
    - Table reference retrieval
    - Sales summary queries
    - Top products queries
    - Location-based analytics
    - Time-series trend analysis
    - Product category queries
    - Customer metrics
    - Error handling and edge cases

Business Value:
    - Validates analytical query accuracy
    - Ensures data aggregation correctness
    - Confirms OLAP database integration
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

from app.repositories.analytics_repository import AnalyticsRepository
from app.exceptions.base import DatabaseException


@pytest.fixture
def mock_duckdb_path(tmp_path):
    """Create a temporary DuckDB file path."""
    db_path = tmp_path / "test_analytics.duckdb"
    db_path.touch()
    return str(db_path)


@pytest.fixture
def mock_ibis_connection():
    """Create a mock Ibis DuckDB connection."""
    connection = MagicMock()
    connection.table = MagicMock()
    connection.disconnect = MagicMock()
    return connection


@pytest.fixture
def analytics_repo(mock_duckdb_path, mock_ibis_connection):
    """Create analytics repository with mocked dependencies."""
    with patch("app.repositories.analytics_repository.ibis.duckdb.connect") as mock_connect:
        mock_connect.return_value = mock_ibis_connection
        repo = AnalyticsRepository(duckdb_path=mock_duckdb_path)
        yield repo


class TestConnectionInitialization:
    """Tests for DuckDB connection initialization."""

    def test_init_with_default_path(self, mock_ibis_connection):
        """Test initialization with default DuckDB path.

        Verifies that repository uses default path when none provided.

        Args:
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Default path used
            - Connection established
        """
        with patch("app.repositories.analytics_repository.Path.exists", return_value=True):
            with patch("app.repositories.analytics_repository.ibis.duckdb.connect") as mock_connect:
                mock_connect.return_value = mock_ibis_connection

                repo = AnalyticsRepository()

                assert repo.duckdb_path == "data/analytical_cube.duckdb"
                mock_connect.assert_called_once_with("data/analytical_cube.duckdb", read_only=True)

    def test_init_with_custom_path(self, mock_duckdb_path, mock_ibis_connection):
        """Test initialization with custom DuckDB path.

        Args:
            mock_duckdb_path: Temporary DuckDB file path
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Custom path used
            - Connection established
        """
        with patch("app.repositories.analytics_repository.ibis.duckdb.connect") as mock_connect:
            mock_connect.return_value = mock_ibis_connection

            repo = AnalyticsRepository(duckdb_path=mock_duckdb_path)

            assert repo.duckdb_path == mock_duckdb_path
            mock_connect.assert_called_once_with(mock_duckdb_path, read_only=True)

    def test_init_file_not_found(self):
        """Test initialization fails when DuckDB file does not exist.

        Assertions:
            - DatabaseException raised
            - Error message includes path
        """
        with pytest.raises(DatabaseException) as exc_info:
            AnalyticsRepository(duckdb_path="nonexistent.duckdb")

        assert "DuckDB file not found" in str(exc_info.value)
        assert "nonexistent.duckdb" in str(exc_info.value)

    def test_init_connection_failure(self, mock_duckdb_path):
        """Test initialization fails when connection cannot be established.

        Args:
            mock_duckdb_path: Temporary DuckDB file path

        Assertions:
            - DatabaseException raised
            - Original error preserved
        """
        with patch("app.repositories.analytics_repository.ibis.duckdb.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(DatabaseException) as exc_info:
                AnalyticsRepository(duckdb_path=mock_duckdb_path)

            assert "Failed to connect to DuckDB" in str(exc_info.value)


class TestTableRetrieval:
    """Tests for Ibis table reference retrieval."""

    def test_get_table_success(self, analytics_repo, mock_ibis_connection):
        """Test successful table retrieval.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Table reference returned
            - Correct schema and table name used
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        table = analytics_repo._get_table("Ordenes")

        assert table is mock_table
        mock_ibis_connection.table.assert_called_once_with("sales_mart.Ordenes")

    def test_get_table_custom_schema(self, analytics_repo, mock_ibis_connection):
        """Test table retrieval with custom schema.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Custom schema used
            - Table reference returned
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        table = analytics_repo._get_table("MyTable", schema="custom_schema")

        assert table is mock_table
        mock_ibis_connection.table.assert_called_once_with("custom_schema.MyTable")

    def test_get_table_not_found(self, analytics_repo, mock_ibis_connection):
        """Test table retrieval fails when table does not exist.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
            - Error includes table and schema names
        """
        mock_ibis_connection.table.side_effect = Exception("Table not found")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo._get_table("NonExistent")

        assert "Table not found: sales_mart.NonExistent" in str(exc_info.value)


class TestSalesSummary:
    """Tests for sales summary queries."""

    def test_get_sales_summary_success(self, analytics_repo, mock_ibis_connection):
        """Test successful sales summary retrieval.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Summary metrics calculated
            - Date filters applied
            - Results in expected format
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha)

        # Mock monto attribute
        mock_monto = MagicMock()
        type(mock_table).monto = PropertyMock(return_value=mock_monto)

        # Mock filter and aggregate operations
        mock_filtered = MagicMock()
        mock_filtered.count.return_value = MagicMock()
        type(mock_filtered).monto = PropertyMock(return_value=mock_monto)
        mock_table.filter.return_value = mock_filtered

        mock_aggregated = MagicMock()
        mock_filtered.aggregate.return_value = mock_aggregated

        # Mock execution result
        mock_result = MagicMock()
        mock_result.to_dict.return_value = [{
            "total_sales": 150000.50,
            "order_count": 250,
            "avg_order_value": 600.00
        }]
        mock_result.__len__ = Mock(return_value=1)
        mock_aggregated.execute.return_value = mock_result

        summary = analytics_repo.get_sales_summary("2025-01-01", "2025-01-31")

        assert summary["total_sales"] == 150000.50
        assert summary["order_count"] == 250
        assert summary["avg_order_value"] == 600.00
        mock_table.filter.assert_called_once()

    def test_get_sales_summary_empty_results(self, analytics_repo, mock_ibis_connection):
        """Test sales summary with no matching data.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Empty dictionary returned
            - No errors raised
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha)

        # Mock monto attribute
        mock_monto = MagicMock()
        type(mock_table).monto = PropertyMock(return_value=mock_monto)

        mock_filtered = MagicMock()
        mock_filtered.count.return_value = MagicMock()
        type(mock_filtered).monto = PropertyMock(return_value=mock_monto)
        mock_table.filter.return_value = mock_filtered

        mock_aggregated = MagicMock()
        mock_filtered.aggregate.return_value = mock_aggregated

        mock_result = MagicMock()
        mock_result.to_dict.return_value = []
        mock_result.__len__ = Mock(return_value=0)
        mock_aggregated.execute.return_value = mock_result

        summary = analytics_repo.get_sales_summary("2025-01-01", "2025-01-31")

        assert summary == {}

    def test_get_sales_summary_database_error(self, analytics_repo, mock_ibis_connection):
        """Test error handling in sales summary.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
            - Error details included
        """
        mock_ibis_connection.table.side_effect = Exception("Query failed")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_sales_summary("2025-01-01", "2025-01-31")

        assert "Failed to get sales summary" in str(exc_info.value)


class TestTopProducts:
    """Tests for top products queries."""

    def test_get_top_products_basic(self, analytics_repo, mock_ibis_connection):
        """Test retrieving top products without date filters.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Products ordered by revenue
            - Limit applied correctly
            - Join operations performed
        """
        mock_orders = MagicMock()
        mock_products = MagicMock()

        def table_side_effect(name):
            if "Detalle_Ordenes" in name:
                return mock_orders
            elif "Productos" in name:
                return mock_products
            raise Exception(f"Unknown table: {name}")

        mock_ibis_connection.table.side_effect = table_side_effect

        # Mock join and aggregate chain
        mock_joined = MagicMock()
        mock_orders.join.return_value = mock_joined

        mock_grouped = MagicMock()
        mock_joined.group_by.return_value = mock_grouped

        mock_aggregated = MagicMock()
        mock_grouped.aggregate.return_value = mock_aggregated

        mock_ordered = MagicMock()
        mock_aggregated.order_by.return_value = mock_ordered

        mock_limited = MagicMock()
        mock_ordered.limit.return_value = mock_limited

        mock_limited.execute.return_value.to_dict.return_value = [
            {"id": 1, "nombre": "Product A", "total_quantity": 100, "total_revenue": 5000},
            {"id": 2, "nombre": "Product B", "total_quantity": 80, "total_revenue": 4000}
        ]

        products = analytics_repo.get_top_products(limit=10)

        assert len(products) == 2
        assert products[0]["nombre"] == "Product A"
        mock_ordered.limit.assert_called_once_with(10)

    def test_get_top_products_with_date_filter(self, analytics_repo, mock_ibis_connection):
        """Test top products with date range filter.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Date filters applied
            - Results filtered correctly
        """
        mock_orders = MagicMock()
        mock_products = MagicMock()

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_orders).fecha = PropertyMock(return_value=mock_fecha)

        def table_side_effect(name):
            if "Detalle_Ordenes" in name:
                return mock_orders
            elif "Productos" in name:
                return mock_products
            raise Exception(f"Unknown table: {name}")

        mock_ibis_connection.table.side_effect = table_side_effect

        mock_joined = MagicMock()
        mock_orders.join.return_value = mock_joined
        mock_joined.filter.return_value = mock_joined
        mock_joined.group_by.return_value = mock_joined
        mock_joined.aggregate.return_value = mock_joined
        mock_joined.order_by.return_value = mock_joined
        mock_joined.limit.return_value = mock_joined
        mock_joined.execute.return_value.to_dict.return_value = []

        analytics_repo.get_top_products(
            limit=5,
            start_date="2025-01-01",
            end_date="2025-01-31"
        )

        mock_joined.filter.assert_called_once()

    def test_get_top_products_error(self, analytics_repo, mock_ibis_connection):
        """Test error handling in top products query.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
            - Error details preserved
        """
        mock_ibis_connection.table.side_effect = Exception("Join failed")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_top_products(limit=10)

        assert "Failed to get top products" in str(exc_info.value)


class TestSalesByLocation:
    """Tests for location-based sales queries."""

    def test_get_sales_by_location_success(self, analytics_repo, mock_ibis_connection):
        """Test sales aggregation by location.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Sales grouped by branch
            - Results ordered by revenue
        """
        mock_orders = MagicMock()
        mock_branches = MagicMock()

        def table_side_effect(name):
            if "Ordenes" in name:
                return mock_orders
            elif "Sucursal" in name:
                return mock_branches
            raise Exception(f"Unknown table: {name}")

        mock_ibis_connection.table.side_effect = table_side_effect

        mock_joined = MagicMock()
        mock_orders.join.return_value = mock_joined
        mock_joined.group_by.return_value = mock_joined
        mock_joined.aggregate.return_value = mock_joined
        mock_joined.order_by.return_value = mock_joined

        mock_joined.execute.return_value.to_dict.return_value = [
            {"id": 1, "nombre": "Branch A", "total_orders": 100, "total_revenue": 50000}
        ]

        results = analytics_repo.get_sales_by_location()

        assert len(results) == 1
        assert results[0]["nombre"] == "Branch A"

    def test_get_sales_by_location_with_dates(self, analytics_repo, mock_ibis_connection):
        """Test sales by location with date filters.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Date filters applied
        """
        mock_orders = MagicMock()
        mock_branches = MagicMock()

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_orders).fecha = PropertyMock(return_value=mock_fecha)

        def table_side_effect(name):
            if "Ordenes" in name:
                return mock_orders
            elif "Sucursal" in name:
                return mock_branches
            raise Exception(f"Unknown table: {name}")

        mock_ibis_connection.table.side_effect = table_side_effect

        mock_joined = MagicMock()
        mock_orders.join.return_value = mock_joined
        mock_joined.filter.return_value = mock_joined
        mock_joined.group_by.return_value = mock_joined
        mock_joined.aggregate.return_value = mock_joined
        mock_joined.order_by.return_value = mock_joined
        mock_joined.execute.return_value.to_dict.return_value = []

        analytics_repo.get_sales_by_location(
            start_date="2025-01-01",
            end_date="2025-01-31"
        )

        mock_joined.filter.assert_called_once()

    def test_get_sales_by_location_error(self, analytics_repo, mock_ibis_connection):
        """Test error handling in sales by location.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
        """
        mock_ibis_connection.table.side_effect = Exception("Aggregation failed")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_sales_by_location()

        assert "Failed to get sales by location" in str(exc_info.value)


class TestSalesTrends:
    """Tests for time-series sales trend queries."""

    def test_get_sales_trends_daily(self, analytics_repo, mock_ibis_connection):
        """Test daily sales trends.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Daily granularity used
            - Results ordered by period
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha)

        # Mock monto attribute
        mock_monto = MagicMock()
        type(mock_table).monto = PropertyMock(return_value=mock_monto)

        mock_filtered = MagicMock()
        type(mock_filtered).fecha = PropertyMock(return_value=mock_fecha)
        type(mock_filtered).monto = PropertyMock(return_value=mock_monto)
        mock_filtered.count.return_value = MagicMock()
        mock_table.filter.return_value = mock_filtered
        mock_filtered.group_by.return_value = mock_filtered
        mock_filtered.aggregate.return_value = mock_filtered
        mock_filtered.order_by.return_value = mock_filtered

        mock_filtered.execute.return_value.to_dict.return_value = [
            {"period": "2025-01-01", "total_sales": 10000, "order_count": 50}
        ]

        trends = analytics_repo.get_sales_trends(
            "2025-01-01",
            "2025-01-31",
            granularity="daily"
        )

        assert len(trends) == 1
        assert trends[0]["period"] == "2025-01-01"

    def test_get_sales_trends_weekly(self, analytics_repo, mock_ibis_connection):
        """Test weekly sales trends.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Weekly aggregation applied
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha_table = MagicMock()
        mock_fecha_table.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha_table.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha_table)

        # Mock monto attribute
        mock_monto = MagicMock()
        type(mock_table).monto = PropertyMock(return_value=mock_monto)

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered

        # Mock the fecha field with truncate method
        mock_fecha = MagicMock()
        mock_fecha.truncate.return_value = "truncated_weekly"
        type(mock_filtered).fecha = PropertyMock(return_value=mock_fecha)
        type(mock_filtered).monto = PropertyMock(return_value=mock_monto)
        mock_filtered.count.return_value = MagicMock()

        mock_filtered.group_by.return_value = mock_filtered
        mock_filtered.aggregate.return_value = mock_filtered
        mock_filtered.order_by.return_value = mock_filtered
        mock_filtered.execute.return_value.to_dict.return_value = []

        analytics_repo.get_sales_trends(
            "2025-01-01",
            "2025-01-31",
            granularity="weekly"
        )

        mock_fecha.truncate.assert_called_once_with("W")

    def test_get_sales_trends_monthly(self, analytics_repo, mock_ibis_connection):
        """Test monthly sales trends.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Monthly aggregation applied
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha_table = MagicMock()
        mock_fecha_table.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha_table.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha_table)

        # Mock monto attribute
        mock_monto = MagicMock()
        type(mock_table).monto = PropertyMock(return_value=mock_monto)

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered

        mock_fecha = MagicMock()
        mock_fecha.truncate.return_value = "truncated_monthly"
        type(mock_filtered).fecha = PropertyMock(return_value=mock_fecha)
        type(mock_filtered).monto = PropertyMock(return_value=mock_monto)
        mock_filtered.count.return_value = MagicMock()

        mock_filtered.group_by.return_value = mock_filtered
        mock_filtered.aggregate.return_value = mock_filtered
        mock_filtered.order_by.return_value = mock_filtered
        mock_filtered.execute.return_value.to_dict.return_value = []

        analytics_repo.get_sales_trends(
            "2025-01-01",
            "2025-01-31",
            granularity="monthly"
        )

        mock_fecha.truncate.assert_called_once_with("M")

    def test_get_sales_trends_invalid_granularity(self, analytics_repo, mock_ibis_connection):
        """Test error handling for invalid granularity.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
            - Error message mentions invalid granularity
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_sales_trends(
                "2025-01-01",
                "2025-01-31",
                granularity="invalid"
            )

        assert "Failed to get sales trends" in str(exc_info.value)


class TestProductCategories:
    """Tests for product category queries."""

    def test_get_product_categories_success(self, analytics_repo, mock_ibis_connection):
        """Test product categories retrieval.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Categories with product counts returned
            - Results ordered by count
        """
        mock_products = MagicMock()
        mock_categories = MagicMock()

        def table_side_effect(name):
            if "Productos" in name:
                return mock_products
            elif "Linea" in name:
                return mock_categories
            raise Exception(f"Unknown table: {name}")

        mock_ibis_connection.table.side_effect = table_side_effect

        mock_joined = MagicMock()
        mock_products.join.return_value = mock_joined
        mock_joined.group_by.return_value = mock_joined
        mock_joined.aggregate.return_value = mock_joined
        mock_joined.order_by.return_value = mock_joined

        mock_joined.execute.return_value.to_dict.return_value = [
            {"id": 1, "nombre": "Electronics", "product_count": 50}
        ]

        categories = analytics_repo.get_product_categories()

        assert len(categories) == 1
        assert categories[0]["nombre"] == "Electronics"

    def test_get_product_categories_error(self, analytics_repo, mock_ibis_connection):
        """Test error handling in product categories.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
        """
        mock_ibis_connection.table.side_effect = Exception("Join failed")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_product_categories()

        assert "Failed to get product categories" in str(exc_info.value)


class TestCustomerMetrics:
    """Tests for customer metrics queries."""

    def test_get_customer_metrics_success(self, analytics_repo, mock_ibis_connection):
        """Test customer metrics calculation.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Customer statistics calculated
            - Repeat customer rate computed
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock cliente_id attribute
        mock_cliente_id = MagicMock()
        mock_nunique = MagicMock()
        mock_nunique.execute.return_value = 100
        mock_nunique.__gt__ = MagicMock(return_value=True)
        mock_nunique.__truediv__ = MagicMock(return_value=100)
        mock_nunique.__rtruediv__ = MagicMock(return_value=0.03)
        mock_cliente_id.nunique.return_value = mock_nunique
        type(mock_table).cliente_id = PropertyMock(return_value=mock_cliente_id)

        # Mock count for total orders
        mock_count = MagicMock()
        mock_count.execute.return_value = 250
        mock_count.count.return_value = MagicMock()
        mock_table.count.return_value = mock_count

        # Mock group_by for orders per customer
        mock_grouped = MagicMock()
        mock_grouped.count.return_value = MagicMock()
        mock_table.group_by.return_value = mock_grouped
        mock_grouped.aggregate.return_value = mock_grouped

        # Mock execute result with order counts
        import pandas as pd
        mock_orders_df = pd.DataFrame({
            "cliente_id": [1, 2, 3, 4, 5],
            "order_count": [1, 2, 3, 1, 4]
        })
        mock_grouped.execute.return_value = mock_orders_df

        metrics = analytics_repo.get_customer_metrics()

        assert metrics["total_customers"] == 100
        assert metrics["total_orders"] == 250
        assert metrics["repeat_customer_count"] == 3
        assert metrics["repeat_customer_rate"] == 3.0

    def test_get_customer_metrics_with_date_filter(self, analytics_repo, mock_ibis_connection):
        """Test customer metrics with date range.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Date filters applied
        """
        mock_table = MagicMock()
        mock_ibis_connection.table.return_value = mock_table

        # Mock fecha attribute for comparisons
        mock_fecha = MagicMock()
        mock_fecha.__ge__ = MagicMock(return_value=MagicMock())
        mock_fecha.__le__ = MagicMock(return_value=MagicMock())
        type(mock_table).fecha = PropertyMock(return_value=mock_fecha)

        mock_filtered = MagicMock()
        mock_table.filter.return_value = mock_filtered

        # Mock cliente_id attribute
        mock_cliente_id = MagicMock()
        mock_nunique = MagicMock()
        mock_nunique.execute.return_value = 50
        mock_nunique.__gt__ = MagicMock(return_value=True)
        mock_nunique.__truediv__ = MagicMock(return_value=50)
        mock_nunique.__rtruediv__ = MagicMock(return_value=0.02)
        mock_cliente_id.nunique.return_value = mock_nunique
        type(mock_filtered).cliente_id = PropertyMock(return_value=mock_cliente_id)

        mock_count = MagicMock()
        mock_count.execute.return_value = 100
        mock_count.count.return_value = MagicMock()
        mock_filtered.count.return_value = mock_count

        mock_filtered.group_by.return_value = mock_filtered
        mock_filtered.aggregate.return_value = mock_filtered

        import pandas as pd
        mock_filtered.execute.return_value = pd.DataFrame({"order_count": [1, 2]})

        analytics_repo.get_customer_metrics(
            start_date="2025-01-01",
            end_date="2025-01-31"
        )

        mock_table.filter.assert_called_once()

    def test_get_customer_metrics_error(self, analytics_repo, mock_ibis_connection):
        """Test error handling in customer metrics.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - DatabaseException raised
        """
        mock_ibis_connection.table.side_effect = Exception("Query failed")

        with pytest.raises(DatabaseException) as exc_info:
            analytics_repo.get_customer_metrics()

        assert "Failed to get customer metrics" in str(exc_info.value)


class TestConnectionManagement:
    """Tests for connection lifecycle management."""

    def test_close_connection(self, analytics_repo, mock_ibis_connection):
        """Test closing DuckDB connection.

        Args:
            analytics_repo: Analytics repository instance
            mock_ibis_connection: Mocked Ibis connection

        Assertions:
            - Disconnect method called
        """
        analytics_repo.close()

        mock_ibis_connection.disconnect.assert_called_once()

    def test_close_connection_without_attribute(self):
        """Test close when connection attribute does not exist.

        Assertions:
            - No errors raised
        """
        repo = object.__new__(AnalyticsRepository)

        # Should not raise exception
        repo.close()
