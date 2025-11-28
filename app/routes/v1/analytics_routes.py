"""
Analytics routes for BI queries and data visualization.

Endpoints:
- GET /api/v1/analytics/sales/summary - Sales summary metrics
- GET /api/v1/analytics/sales/products - Product performance
- GET /api/v1/analytics/sales/locations - Location performance
- GET /api/v1/analytics/sales/trends - Sales trends over time
- GET /api/v1/analytics/sales/categories - Category breakdown
- GET /api/v1/analytics/tables - List available tables
- GET /api/v1/analytics/tables/{table_name}/schema - Get table schema
"""

from flask import Blueprint, request, current_app
from app.services.analytics_service import AnalyticsService
from app.middleware.auth_middleware import jwt_required_custom
from app.middleware.rbac_middleware import require_analyst_or_admin
from app.core.responses import success_response, error_response
from app.exceptions.validation import ValidationError
from app.exceptions.base import DatabaseException
from app.extensions import cache


# Create blueprint
analytics_bp = Blueprint('analytics', __name__)

# Initialize service (will use default DuckDB path from config)
analytics_service = AnalyticsService()


@analytics_bp.route('/sales/summary', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=300, query_string=True)
def get_sales_summary():
    """
    Get sales summary metrics for a date range.

    Query Parameters:
        - start_date: Start date in ISO format (YYYY-MM-DD), optional
        - end_date: End date in ISO format (YYYY-MM-DD), optional

    Returns:
        200: Sales summary data
        400: Validation error

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/analytics/sales/summary?start_date=2024-01-01&end_date=2024-12-31" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        # Get sales summary
        summary = analytics_service.get_sales_summary(
            start_date=start_date,
            end_date=end_date
        )

        return success_response(
            data={'summary': summary},
            message="Sales summary retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Sales summary error: {str(e)}")
        return error_response(
            message="Failed to retrieve sales summary",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/sales/products', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=300, query_string=True)
def get_product_performance():
    """
    Get top performing products by sales.

    Query Parameters:
        - limit: Number of top products (default: 20, max: 1000)
        - start_date: Start date filter (optional)
        - end_date: End date filter (optional)

    Returns:
        200: Product performance data
        400: Validation error

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/analytics/sales/products?limit=10" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        # Get product performance
        products = analytics_service.get_product_performance(
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

        return success_response(
            data={'products': products},
            message=f"Top {len(products)} products retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Product performance error: {str(e)}")
        return error_response(
            message="Failed to retrieve product performance",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/sales/locations', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=300, query_string=True)
def get_location_performance():
    """
    Get sales performance by location (Sucursal).

    Query Parameters:
        - limit: Number of top locations (default: 20, max: 1000)
        - start_date: Start date filter (optional)
        - end_date: End date filter (optional)

    Returns:
        200: Location performance data
        400: Validation error

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/analytics/sales/locations?limit=10" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        # Get location performance
        locations = analytics_service.get_location_performance(
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

        return success_response(
            data={'locations': locations},
            message=f"Top {len(locations)} locations retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Location performance error: {str(e)}")
        return error_response(
            message="Failed to retrieve location performance",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/sales/trends', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=300, query_string=True)
def get_sales_trends():
    """
    Get sales trends over time.

    Query Parameters:
        - period: Aggregation period (daily, weekly, monthly, yearly) - default: monthly
        - start_date: Start date filter (optional)
        - end_date: End date filter (optional)

    Returns:
        200: Sales trends data
        400: Validation error

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/analytics/sales/trends?period=monthly" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        period = request.args.get('period', 'monthly')
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        # Get sales trends
        trends = analytics_service.get_sales_trends(
            period=period,
            start_date=start_date,
            end_date=end_date
        )

        return success_response(
            data={'trends': trends, 'period': period},
            message="Sales trends retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Sales trends error: {str(e)}")
        return error_response(
            message="Failed to retrieve sales trends",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/sales/categories', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=300, query_string=True)
def get_category_breakdown():
    """
    Get sales breakdown by product category.

    Query Parameters:
        - category_type: Category type (linea or sub_linea) - default: linea
        - start_date: Start date filter (optional)
        - end_date: End date filter (optional)

    Returns:
        200: Category breakdown data
        400: Validation error

    Example:
        $ curl -X GET "http://localhost:5000/api/v1/analytics/sales/categories?category_type=linea" \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        # Get query parameters
        category_type = request.args.get('category_type', 'linea')
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        # Get category breakdown
        breakdown = analytics_service.get_category_breakdown(
            category_type=category_type,
            start_date=start_date,
            end_date=end_date
        )

        return success_response(
            data={'categories': breakdown, 'category_type': category_type},
            message="Category breakdown retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Category breakdown error: {str(e)}")
        return error_response(
            message="Failed to retrieve category breakdown",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/tables', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=600)
def list_available_tables():
    """
    Get list of available tables in analytical cube.

    Returns:
        200: List of table names

    Example:
        $ curl -X GET http://localhost:5000/api/v1/analytics/tables \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        tables = analytics_service.get_available_tables()

        return success_response(
            data={'tables': tables},
            message=f"{len(tables)} tables available"
        )

    except DatabaseException as e:
        current_app.logger.error(f"List tables error: {str(e)}")
        return error_response(
            message="Failed to retrieve tables",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )


@analytics_bp.route('/tables/<table_name>/schema', methods=['GET'])
@jwt_required_custom()
@require_analyst_or_admin()
@cache.cached(timeout=600, key_prefix='table_schema')
def get_table_schema(table_name: str):
    """
    Get schema information for a table.

    Path Parameters:
        table_name: Name of the table

    Returns:
        200: Table schema with column names and types
        400: Validation error
        500: Database error

    Example:
        $ curl -X GET http://localhost:5000/api/v1/analytics/tables/Productos/schema \\
          -H "Authorization: Bearer <access_token>"
    """
    try:
        schema = analytics_service.get_table_schema(table_name)

        return success_response(
            data={'table_name': table_name, 'schema': schema},
            message="Table schema retrieved successfully"
        )

    except ValidationError as e:
        return error_response(
            message=str(e),
            status_code=400
        )
    except DatabaseException as e:
        current_app.logger.error(f"Get table schema error: {str(e)}")
        return error_response(
            message=f"Failed to retrieve schema for table '{table_name}'",
            status_code=500
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return error_response(
            message="An unexpected error occurred",
            status_code=500
        )
