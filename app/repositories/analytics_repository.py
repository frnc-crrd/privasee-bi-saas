"""Analytics repository for DuckDB queries using Ibis.

This module provides analytical queries for the OLAP database (DuckDB):
- Sales analytics and summaries
- Product performance metrics
- Location-based analytics
- Time-series trend analysis

Uses Ibis framework for type-safe, database-agnostic queries.

Usage:
    from app.repositories.analytics_repository import AnalyticsRepository

    repo = AnalyticsRepository()
    summary = repo.get_sales_summary("2025-01-01", "2025-01-31")
    top_products = repo.get_top_products(limit=10)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import ibis
from ibis.expr.types import Table

from app.exceptions import DatabaseException


class AnalyticsRepository:
    """Repository for analytical queries on DuckDB.

    Provides read-only access to the analytical cube (OLAP database)
    using Ibis for type-safe queries.

    Attributes:
        connection: Ibis DuckDB connection
        duckdb_path: Path to DuckDB database file

    Example:
        >>> repo = AnalyticsRepository()
        >>> summary = repo.get_sales_summary("2025-01-01", "2025-01-31")
        >>> print(f"Total sales: ${summary['total_sales']}")
    """

    def __init__(self, duckdb_path: Optional[str] = None):
        """Initialize AnalyticsRepository with DuckDB connection.

        Args:
            duckdb_path: Path to DuckDB file (default: data/analytical_cube.duckdb)

        Example:
            >>> repo = AnalyticsRepository()
            >>> # Or with custom path
            >>> repo = AnalyticsRepository("path/to/custom.duckdb")
        """
        if duckdb_path is None:
            duckdb_path = "data/analytical_cube.duckdb"

        self.duckdb_path = duckdb_path

        # Check if database file exists
        db_file = Path(duckdb_path)
        if not db_file.exists():
            raise DatabaseException(
                message=f"DuckDB file not found: {duckdb_path}",
                details={"path": duckdb_path},
            )

        try:
            self.connection = ibis.duckdb.connect(duckdb_path, read_only=True)
        except Exception as e:
            raise DatabaseException(
                message="Failed to connect to DuckDB",
                details={"error": str(e), "path": duckdb_path},
            ) from e

    def _get_table(self, table_name: str, schema: str = "sales_mart") -> Table:
        """Get Ibis table reference.

        Args:
            table_name: Name of the table
            schema: Schema name (default: sales_mart)

        Returns:
            Ibis table reference

        Raises:
            DatabaseException: If table not found
        """
        try:
            full_name = f"{schema}.{table_name}"
            return self.connection.table(full_name)
        except Exception as e:
            raise DatabaseException(
                message=f"Table not found: {schema}.{table_name}",
                details={"error": str(e), "table": table_name, "schema": schema},
            ) from e

    def get_sales_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get sales summary for date range.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)

        Returns:
            Dictionary with summary metrics:
            - total_sales: Total sales amount
            - order_count: Number of orders
            - avg_order_value: Average order value

        Example:
            >>> summary = repo.get_sales_summary("2025-01-01", "2025-01-31")
            >>> print(f"Total: ${summary['total_sales']:,.2f}")
        """
        try:
            orders = self._get_table("Ordenes")

            # Filter by date range
            filtered = orders.filter((orders.fecha >= start_date) & (orders.fecha <= end_date))

            # Aggregate metrics
            result = filtered.aggregate(
                total_sales=filtered.monto.sum(),
                order_count=filtered.count(),
                avg_order_value=filtered.monto.mean(),
            ).execute()

            # Convert to dictionary
            return result.to_dict("records")[0] if len(result) > 0 else {}
        except Exception as e:
            raise DatabaseException(
                message="Failed to get sales summary",
                details={
                    "error": str(e),
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ) from e

    def get_top_products(
        self, limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get top-selling products.

        Args:
            limit: Number of products to return (default: 10)
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            List of dictionaries with product metrics:
            - product_id: Product identifier
            - product_name: Product name
            - total_quantity: Total quantity sold
            - total_revenue: Total revenue generated

        Example:
            >>> top_products = repo.get_top_products(limit=5)
            >>> for product in top_products:
            ...     print(f"{product['product_name']}: ${product['total_revenue']}")
        """
        try:
            orders = self._get_table("Detalle_Ordenes")
            products = self._get_table("Productos")

            # Join orders with products
            joined = orders.join(products, orders.producto_id == products.id)

            # Apply date filters if provided
            if start_date and end_date:
                joined = joined.filter((orders.fecha >= start_date) & (orders.fecha <= end_date))

            # Aggregate by product
            result = (
                joined.group_by([products.id, products.nombre])
                .aggregate(
                    total_quantity=orders.cantidad.sum(),
                    total_revenue=(orders.cantidad * orders.precio_unitario).sum(),
                )
                .order_by(ibis.desc("total_revenue"))
                .limit(limit)
                .execute()
            )

            return result.to_dict("records")
        except Exception as e:
            raise DatabaseException(
                message="Failed to get top products",
                details={"error": str(e), "limit": limit},
            ) from e

    def get_sales_by_location(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get sales aggregated by location.

        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            List of dictionaries with location metrics:
            - sucursal_id: Branch identifier
            - sucursal_name: Branch name
            - total_orders: Number of orders
            - total_revenue: Total revenue

        Example:
            >>> by_location = repo.get_sales_by_location()
            >>> for loc in by_location:
            ...     print(f"{loc['sucursal_name']}: ${loc['total_revenue']}")
        """
        try:
            orders = self._get_table("Ordenes")
            branches = self._get_table("Sucursal")

            # Join orders with branches
            joined = orders.join(branches, orders.sucursal_id == branches.id)

            # Apply date filters if provided
            if start_date and end_date:
                joined = joined.filter((orders.fecha >= start_date) & (orders.fecha <= end_date))

            # Aggregate by location
            result = (
                joined.group_by([branches.id, branches.nombre])
                .aggregate(
                    total_orders=orders.count(),
                    total_revenue=orders.monto.sum(),
                )
                .order_by(ibis.desc("total_revenue"))
                .execute()
            )

            return result.to_dict("records")
        except Exception as e:
            raise DatabaseException(
                message="Failed to get sales by location",
                details={"error": str(e)},
            ) from e

    def get_sales_trends(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "daily",
    ) -> List[Dict[str, Any]]:
        """Get sales trends over time.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            granularity: Time granularity (daily, weekly, monthly)

        Returns:
            List of dictionaries with time-series data:
            - period: Time period
            - total_sales: Total sales for period
            - order_count: Number of orders

        Example:
            >>> trends = repo.get_sales_trends("2025-01-01", "2025-01-31", "daily")
            >>> for day in trends:
            ...     print(f"{day['period']}: ${day['total_sales']}")
        """
        try:
            orders = self._get_table("Ordenes")

            # Filter by date range
            filtered = orders.filter((orders.fecha >= start_date) & (orders.fecha <= end_date))

            # Group by time period based on granularity
            if granularity == "daily":
                period_expr = filtered.fecha
            elif granularity == "weekly":
                period_expr = filtered.fecha.truncate("W")
            elif granularity == "monthly":
                period_expr = filtered.fecha.truncate("M")
            else:
                raise ValueError(f"Invalid granularity: {granularity}")

            # Aggregate by period
            result = (
                filtered.group_by(period=period_expr)
                .aggregate(
                    total_sales=filtered.monto.sum(),
                    order_count=filtered.count(),
                )
                .order_by("period")
                .execute()
            )

            return result.to_dict("records")
        except Exception as e:
            raise DatabaseException(
                message="Failed to get sales trends",
                details={
                    "error": str(e),
                    "start_date": start_date,
                    "end_date": end_date,
                    "granularity": granularity,
                },
            ) from e

    def get_product_categories(self) -> List[Dict[str, Any]]:
        """Get list of product categories with counts.

        Returns:
            List of dictionaries with category info:
            - linea_id: Category identifier
            - linea_name: Category name
            - product_count: Number of products in category

        Example:
            >>> categories = repo.get_product_categories()
            >>> for cat in categories:
            ...     print(f"{cat['linea_name']}: {cat['product_count']} products")
        """
        try:
            products = self._get_table("Productos")
            categories = self._get_table("Linea")

            # Join and aggregate
            result = (
                products.join(categories, products.linea_id == categories.id)
                .group_by([categories.id, categories.nombre])
                .aggregate(product_count=products.count())
                .order_by(ibis.desc("product_count"))
                .execute()
            )

            return result.to_dict("records")
        except Exception as e:
            raise DatabaseException(
                message="Failed to get product categories",
                details={"error": str(e)},
            ) from e

    def get_customer_metrics(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get customer-related metrics.

        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dictionary with customer metrics:
            - total_customers: Total unique customers
            - avg_orders_per_customer: Average orders per customer
            - repeat_customer_rate: Percentage of repeat customers

        Example:
            >>> metrics = repo.get_customer_metrics()
            >>> print(f"Total customers: {metrics['total_customers']}")
        """
        try:
            orders = self._get_table("Ordenes")

            # Apply date filters if provided
            if start_date and end_date:
                orders = orders.filter((orders.fecha >= start_date) & (orders.fecha <= end_date))

            # Calculate metrics
            total_customers = orders.cliente_id.nunique()
            total_orders = orders.count()

            # Orders per customer
            orders_per_customer = (
                orders.group_by("cliente_id").aggregate(order_count=orders.count()).execute()
            )

            avg_orders = (
                orders_per_customer["order_count"].mean() if len(orders_per_customer) > 0 else 0
            )

            # Repeat customers (more than 1 order)
            repeat_customers = len(orders_per_customer[orders_per_customer["order_count"] > 1])
            repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0

            return {
                "total_customers": int(total_customers.execute()),
                "total_orders": int(total_orders.execute()),
                "avg_orders_per_customer": float(avg_orders),
                "repeat_customer_count": repeat_customers,
                "repeat_customer_rate": round(repeat_rate, 2),
            }
        except Exception as e:
            raise DatabaseException(
                message="Failed to get customer metrics",
                details={"error": str(e)},
            ) from e

    def close(self):
        """Close the DuckDB connection.

        Should be called when done with the repository to free resources.

        Example:
            >>> repo = AnalyticsRepository()
            >>> # ... use repo ...
            >>> repo.close()
        """
        if hasattr(self, "connection"):
            self.connection.disconnect()
