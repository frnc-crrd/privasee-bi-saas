"""
Analytics service for BI queries on DuckDB analytical cube.

This service handles:
- Sales summary and metrics
- Product performance analysis
- Location-based analytics
- Time-series trends
- Custom analytical queries via Ibis
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from flask import current_app
import ibis
from ibis.expr import datatypes as dt
from app.repositories.analytics_repository import AnalyticsRepository
from app.exceptions.base import DatabaseException
from app.exceptions.validation import ValidationError
from app.core.cache import cache_analytics_data


class AnalyticsService:
    """
    Handles analytical queries and business intelligence operations.

    This service uses Ibis Framework to query DuckDB analytical cube
    and provides high-level analytics methods.
    """

    def __init__(self, duckdb_path: Optional[str] = None) -> None:
        """
        Initialize AnalyticsService with DuckDB connection.

        Args:
            duckdb_path: Path to DuckDB file (optional, uses default if None)
        """
        self.repository = AnalyticsRepository(duckdb_path=duckdb_path)

    @cache_analytics_data(timeout=3600)
    def get_sales_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get sales summary metrics for a date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD), optional
            end_date: End date in ISO format (YYYY-MM-DD), optional

        Returns:
            Dictionary with total sales, order count, avg order value

        Raises:
            ValidationError: If date format is invalid
            DatabaseException: If query fails

        Example:
            >>> analytics_service = AnalyticsService()
            >>> summary = analytics_service.get_sales_summary(
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )
        """
        # Validate dates
        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        try:
            return self.repository.get_sales_summary(
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            current_app.logger.error(f"Sales summary query failed: {str(e)}")
            raise DatabaseException(f"Failed to retrieve sales summary: {str(e)}") from e

    @cache_analytics_data(timeout=3600)
    def get_product_performance(
        self,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top performing products by sales.

        Args:
            limit: Number of top products to return (default: 20)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of dictionaries with product performance data

        Raises:
            ValidationError: If parameters are invalid
            DatabaseException: If query fails

        Example:
            >>> top_products = analytics_service.get_product_performance(
            ...     limit=10,
            ...     start_date="2024-01-01"
            ... )
        """
        if limit <= 0 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000")

        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        try:
            return self.repository.get_top_products(
                limit=limit,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            current_app.logger.error(f"Product performance query failed: {str(e)}")
            raise DatabaseException(f"Failed to retrieve product performance: {str(e)}") from e

    @cache_analytics_data(timeout=3600)
    def get_location_performance(
        self,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales performance by location (Sucursal).

        Args:
            limit: Number of top locations to return (default: 20)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of dictionaries with location performance data

        Raises:
            ValidationError: If parameters are invalid
            DatabaseException: If query fails

        Example:
            >>> locations = analytics_service.get_location_performance(
            ...     limit=10
            ... )
        """
        if limit <= 0 or limit > 1000:
            raise ValidationError("Limit must be between 1 and 1000")

        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        try:
            return self.repository.get_sales_by_location(
                limit=limit,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            current_app.logger.error(f"Location performance query failed: {str(e)}")
            raise DatabaseException(f"Failed to retrieve location performance: {str(e)}") from e

    @cache_analytics_data(timeout=3600)
    def get_sales_trends(
        self,
        period: str = 'monthly',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales trends over time.

        Args:
            period: Aggregation period ('daily', 'weekly', 'monthly', 'yearly')
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of dictionaries with time-series sales data

        Raises:
            ValidationError: If parameters are invalid
            DatabaseException: If query fails

        Example:
            >>> trends = analytics_service.get_sales_trends(
            ...     period='monthly',
            ...     start_date="2024-01-01"
            ... )
        """
        valid_periods = ['daily', 'weekly', 'monthly', 'yearly']
        if period not in valid_periods:
            raise ValidationError(
                f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )

        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        try:
            return self.repository.get_sales_trends(
                period=period,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            current_app.logger.error(f"Sales trends query failed: {str(e)}")
            raise DatabaseException(f"Failed to retrieve sales trends: {str(e)}") from e

    def get_category_breakdown(
        self,
        category_type: str = 'linea',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales breakdown by product category.

        Args:
            category_type: Category type ('linea' or 'sub_linea')
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of dictionaries with category sales data

        Raises:
            ValidationError: If parameters are invalid
            DatabaseException: If query fails

        Example:
            >>> breakdown = analytics_service.get_category_breakdown(
            ...     category_type='linea'
            ... )
        """
        valid_types = ['linea', 'sub_linea']
        if category_type not in valid_types:
            raise ValidationError(
                f"Invalid category type. Must be one of: {', '.join(valid_types)}"
            )

        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        try:
            return self.repository.get_sales_by_category(
                category_type=category_type,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            current_app.logger.error(f"Category breakdown query failed: {str(e)}")
            raise DatabaseException(f"Failed to retrieve category breakdown: {str(e)}") from e

    def get_available_tables(self) -> List[str]:
        """
        Get list of available tables in analytical cube.

        Returns:
            List of table names

        Example:
            >>> tables = analytics_service.get_available_tables()
            >>> print(tables)
            ['Sucursal', 'Productos', 'Linea', 'Sub_Linea']
        """
        try:
            return self.repository.list_tables()
        except Exception as e:
            current_app.logger.error(f"Failed to list tables: {str(e)}")
            raise DatabaseException(f"Failed to list tables: {str(e)}") from e

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of table

        Returns:
            Dictionary mapping column names to data types

        Raises:
            ValidationError: If table doesn't exist
            DatabaseException: If query fails

        Example:
            >>> schema = analytics_service.get_table_schema('Productos')
        """
        try:
            return self.repository.get_table_schema(table_name)
        except Exception as e:
            current_app.logger.error(f"Failed to get table schema: {str(e)}")
            raise DatabaseException(f"Failed to get schema for {table_name}: {str(e)}") from e

    def execute_custom_query(
        self,
        query_func: Any,
        cache_timeout: int = 600
    ) -> Any:
        """
        Execute a custom Ibis query.

        This method allows for advanced custom queries while maintaining
        caching and error handling.

        Args:
            query_func: Function that takes Ibis connection and returns query result
            cache_timeout: Cache timeout in seconds (default: 10 minutes)

        Returns:
            Query result

        Raises:
            DatabaseException: If query fails

        Example:
            >>> def my_query(con):
            ...     products = con.table('sales_mart.Productos')
            ...     return products.filter(products.precio > 100).execute()
            >>> result = analytics_service.execute_custom_query(my_query)
        """
        try:
            con = self.repository.get_connection()
            result = query_func(con)
            return result
        except Exception as e:
            current_app.logger.error(f"Custom query failed: {str(e)}")
            raise DatabaseException(f"Query execution failed: {str(e)}") from e

    def _validate_date_format(self, date_string: str) -> None:
        """
        Validate date string is in ISO format (YYYY-MM-DD).

        Args:
            date_string: Date string to validate

        Raises:
            ValidationError: If date format is invalid
        """
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
        except ValueError as e:
            raise ValidationError(
                f"Invalid date format: {date_string}. Expected format: YYYY-MM-DD"
            ) from e

    def close_connection(self) -> None:
        """
        Close DuckDB connection.

        Call this when service is no longer needed to free resources.

        Example:
            >>> analytics_service.close_connection()
        """
        self.repository.close()
