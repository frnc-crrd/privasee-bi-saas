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
    Get sales summary metrics and KPIs.
    ---
    tags:
      - Analytics
    summary: Get sales summary
    description: |
      Retrieves aggregate sales metrics including total sales, order count, average order value, and growth rates.
      Requires analyst or admin role. Results are cached for 5 minutes.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: start_date
        type: string
        format: date
        required: false
        description: Start date filter (YYYY-MM-DD format)
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        required: false
        description: End date filter (YYYY-MM-DD format)
        example: "2024-12-31"
    responses:
      200:
        description: Sales summary retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Sales summary retrieved successfully
            data:
              type: object
              properties:
                summary:
                  type: object
                  properties:
                    total_sales:
                      type: number
                      format: float
                      example: 1250000.50
                      description: Total sales revenue
                    total_orders:
                      type: integer
                      example: 3420
                      description: Number of orders
                    avg_order_value:
                      type: number
                      format: float
                      example: 365.50
                      description: Average order value
                    growth_rate:
                      type: number
                      format: float
                      example: 12.5
                      description: Growth percentage compared to previous period
      400:
        description: Validation error (invalid date format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Invalid date format
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Missing or invalid token
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Insufficient permissions
      500:
        description: Server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: Failed to retrieve sales summary
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
    Get top performing products ranked by sales revenue.
    ---
    tags:
      - Analytics
    summary: Get top products by sales
    description: |
      Retrieves a ranked list of products by total sales revenue. Returns product name, total sales,
      order count, and average order value. Useful for identifying bestsellers and inventory optimization.

      **Features:**
      - Configurable limit (top N products)
      - Date range filtering
      - Cached for 5 minutes (performance optimization)
      - Returns aggregated metrics per product

      **Use Cases:**
      - Identify bestselling products
      - Inventory planning and restocking decisions
      - Product performance comparison
      - Marketing campaign targeting

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: limit
        type: integer
        required: false
        default: 20
        description: Number of top products to return (maximum 1000)
        example: 10
      - in: query
        name: start_date
        type: string
        format: date
        required: false
        description: Filter sales from this date onwards (YYYY-MM-DD format)
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        required: false
        description: Filter sales until this date (YYYY-MM-DD format)
        example: "2024-12-31"
    responses:
      200:
        description: Product performance data retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Top 10 products retrieved successfully"
            data:
              type: object
              properties:
                products:
                  type: array
                  items:
                    type: object
                    properties:
                      product_id:
                        type: integer
                        example: 42
                        description: Product identifier
                      product_name:
                        type: string
                        example: "Laptop Dell XPS 15"
                        description: Product name
                      total_sales:
                        type: number
                        format: float
                        example: 125000.50
                        description: Total sales revenue for this product
                      order_count:
                        type: integer
                        example: 342
                        description: Number of orders containing this product
                      avg_order_value:
                        type: number
                        format: float
                        example: 365.50
                        description: Average value per order
                      rank:
                        type: integer
                        example: 1
                        description: Ranking by total sales (1 = highest)
      400:
        description: Validation error (invalid date format or limit exceeds maximum)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid date format. Use YYYY-MM-DD"
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      500:
        description: Server error (database connection or query execution failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve product performance"
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
    Get sales performance metrics by physical location (branch/store).
    ---
    tags:
      - Analytics
    summary: Get sales by location
    description: |
      Retrieves sales performance metrics aggregated by physical location (Sucursal). Returns location name,
      total sales revenue, order count, average order value, and geographic information (city, region).

      **Features:**
      - Configurable limit (top N locations)
      - Date range filtering
      - Geographic aggregation (city-level insights)
      - Cached for 5 minutes (performance optimization)

      **Use Cases:**
      - Identify highest-performing stores
      - Regional sales analysis
      - Resource allocation decisions
      - Expansion planning (identify successful locations)
      - Compare urban vs. suburban performance

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: limit
        type: integer
        required: false
        default: 20
        description: Number of top locations to return (maximum 1000)
        example: 10
      - in: query
        name: start_date
        type: string
        format: date
        required: false
        description: Filter sales from this date onwards (YYYY-MM-DD format)
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        required: false
        description: Filter sales until this date (YYYY-MM-DD format)
        example: "2024-12-31"
    responses:
      200:
        description: Location performance data retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Top 10 locations retrieved successfully"
            data:
              type: object
              properties:
                locations:
                  type: array
                  items:
                    type: object
                    properties:
                      location_id:
                        type: integer
                        example: 5
                        description: Location identifier (Sucursal ID)
                      location_name:
                        type: string
                        example: "Centro CDMX"
                        description: Store/branch name
                      city:
                        type: string
                        example: "Ciudad de México"
                        description: City where location is based
                      total_sales:
                        type: number
                        format: float
                        example: 450000.75
                        description: Total sales revenue for this location
                      order_count:
                        type: integer
                        example: 1250
                        description: Number of orders processed at this location
                      avg_order_value:
                        type: number
                        format: float
                        example: 360.00
                        description: Average order value
                      rank:
                        type: integer
                        example: 1
                        description: Ranking by total sales (1 = highest)
      400:
        description: Validation error (invalid date format or limit exceeds maximum)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid date format. Use YYYY-MM-DD"
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      500:
        description: Server error (database connection or query execution failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve location performance"
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
    Get time-series sales trends with configurable aggregation periods.
    ---
    tags:
      - Analytics
    summary: Get sales trends over time
    description: |
      Retrieves sales metrics aggregated over time with configurable granularity (daily, weekly, monthly, yearly).
      Returns time-series data showing sales evolution, enabling trend analysis and seasonality detection.

      **Features:**
      - Multiple aggregation periods (daily, weekly, monthly, yearly)
      - Date range filtering
      - Time-series data optimized for charting
      - Cached for 5 minutes (performance optimization)
      - Includes period-over-period growth calculations

      **Use Cases:**
      - Identify seasonal patterns and trends
      - Forecast future sales based on historical data
      - Detect anomalies or unusual sales spikes/drops
      - Compare year-over-year performance
      - Visualize sales evolution in dashboards

      **Aggregation Periods:**
      - daily: Day-by-day granularity (best for recent data)
      - weekly: Week-by-week aggregation (balance between detail and overview)
      - monthly: Month-by-month summary (standard for quarterly reviews)
      - yearly: Annual totals (long-term strategic planning)

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: period
        type: string
        required: false
        default: "monthly"
        enum: [daily, weekly, monthly, yearly]
        description: Time aggregation granularity
        example: "monthly"
      - in: query
        name: start_date
        type: string
        format: date
        required: false
        description: Filter sales from this date onwards (YYYY-MM-DD format)
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        required: false
        description: Filter sales until this date (YYYY-MM-DD format)
        example: "2024-12-31"
    responses:
      200:
        description: Sales trends data retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Sales trends retrieved successfully"
            data:
              type: object
              properties:
                trends:
                  type: array
                  items:
                    type: object
                    properties:
                      period_label:
                        type: string
                        example: "2024-03"
                        description: Period identifier (format varies by aggregation - YYYY-MM for monthly)
                      period_start:
                        type: string
                        format: date
                        example: "2024-03-01"
                        description: Start date of the period
                      period_end:
                        type: string
                        format: date
                        example: "2024-03-31"
                        description: End date of the period
                      total_sales:
                        type: number
                        format: float
                        example: 185000.50
                        description: Total sales revenue for this period
                      order_count:
                        type: integer
                        example: 520
                        description: Number of orders in this period
                      avg_order_value:
                        type: number
                        format: float
                        example: 355.77
                        description: Average order value for this period
                      growth_rate:
                        type: number
                        format: float
                        example: 8.5
                        description: Percentage growth compared to previous period
                period:
                  type: string
                  example: "monthly"
                  description: Aggregation period used
      400:
        description: Validation error (invalid period value or date format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid period. Must be one of: daily, weekly, monthly, yearly"
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      500:
        description: Server error (database connection or query execution failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve sales trends"
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
    Get sales breakdown by product category hierarchy (Linea/Sub-Linea).
    ---
    tags:
      - Analytics
    summary: Get sales by category
    description: |
      Retrieves sales metrics aggregated by product category with support for hierarchical categorization.
      Supports both top-level categories (Linea) and subcategories (Sub-Linea) for granular analysis.

      **Features:**
      - Hierarchical category support (Linea and Sub-Linea)
      - Date range filtering
      - Percentage contribution calculations
      - Cached for 5 minutes (performance optimization)
      - Sorted by total sales (highest first)

      **Use Cases:**
      - Identify best-performing product categories
      - Category mix analysis (revenue distribution)
      - Inventory planning by category
      - Category-level promotions and discounting strategies
      - Portfolio optimization decisions

      **Category Types:**
      - linea: Top-level product categories (e.g., Electronics, Clothing, Home Goods)
      - sub_linea: Subcategories within main categories (e.g., Laptops, Smartphones under Electronics)

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: query
        name: category_type
        type: string
        required: false
        default: "linea"
        enum: [linea, sub_linea]
        description: Category hierarchy level to analyze
        example: "linea"
      - in: query
        name: start_date
        type: string
        format: date
        required: false
        description: Filter sales from this date onwards (YYYY-MM-DD format)
        example: "2024-01-01"
      - in: query
        name: end_date
        type: string
        format: date
        required: false
        description: Filter sales until this date (YYYY-MM-DD format)
        example: "2024-12-31"
    responses:
      200:
        description: Category breakdown data retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Category breakdown retrieved successfully"
            data:
              type: object
              properties:
                categories:
                  type: array
                  items:
                    type: object
                    properties:
                      category_id:
                        type: integer
                        example: 3
                        description: Category identifier
                      category_name:
                        type: string
                        example: "Electronics"
                        description: Category name
                      total_sales:
                        type: number
                        format: float
                        example: 320000.75
                        description: Total sales revenue for this category
                      order_count:
                        type: integer
                        example: 890
                        description: Number of orders containing products from this category
                      avg_order_value:
                        type: number
                        format: float
                        example: 359.55
                        description: Average order value for this category
                      sales_percentage:
                        type: number
                        format: float
                        example: 25.6
                        description: Percentage of total sales contributed by this category
                      product_count:
                        type: integer
                        example: 45
                        description: Number of distinct products in this category
                category_type:
                  type: string
                  example: "linea"
                  description: Category hierarchy level analyzed
      400:
        description: Validation error (invalid category_type or date format)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid category_type. Must be 'linea' or 'sub_linea'"
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      500:
        description: Server error (database connection or query execution failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve category breakdown"
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
    List all available tables in the analytical data warehouse (DuckDB).
    ---
    tags:
      - Analytics
    summary: List available data tables
    description: |
      Retrieves a list of all accessible tables in the analytical cube (DuckDB warehouse).
      Useful for data exploration, schema discovery, and building dynamic queries.

      **Features:**
      - Returns table names from DuckDB analytical database
      - Cached for 10 minutes (tables change infrequently)
      - Includes metadata about table availability
      - No query parameters required

      **Use Cases:**
      - Data exploration and discovery
      - Building dynamic query builders
      - Schema documentation generation
      - Validating table existence before queries
      - Administrative data catalog

      **Common Tables:**
      - Sucursal: Physical store/branch locations
      - Productos: Product catalog with categories
      - Linea: Top-level product categories
      - Sub_Linea: Product subcategories
      - Ventas: Sales transactions (fact table)

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    responses:
      200:
        description: Table list retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "5 tables available"
            data:
              type: object
              properties:
                tables:
                  type: array
                  items:
                    type: string
                  example: ["Sucursal", "Productos", "Linea", "Sub_Linea", "Ventas"]
                  description: List of available table names
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      500:
        description: Server error (DuckDB connection failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve tables"
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
    Get detailed schema information for a specific table in the analytical warehouse.
    ---
    tags:
      - Analytics
    summary: Get table schema
    description: |
      Retrieves comprehensive schema metadata for a specified table, including column names,
      data types, and constraints. Essential for building dynamic queries and understanding data structure.

      **Features:**
      - Returns all columns with data types
      - Includes nullable/not-null constraints
      - Primary key identification
      - Data type information (INTEGER, VARCHAR, DATE, etc.)
      - Cached for 10 minutes (schemas change infrequently)

      **Use Cases:**
      - Schema discovery for query building
      - Data validation and type checking
      - Documentation generation
      - Database migration planning
      - Dynamic form generation based on schema

      **Common Tables to Query:**
      - Sucursal: Store location schema
      - Productos: Product catalog structure
      - Linea: Category schema
      - Sub_Linea: Subcategory schema
      - Ventas: Sales transaction schema (fact table)

      **Authorization:**
      Requires analyst or admin role.
    security:
      - Bearer: []
    parameters:
      - in: path
        name: table_name
        type: string
        required: true
        description: Name of the table (case-sensitive, e.g., 'Productos', 'Sucursal')
        example: "Productos"
    responses:
      200:
        description: Table schema retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Table schema retrieved successfully"
            data:
              type: object
              properties:
                table_name:
                  type: string
                  example: "Productos"
                  description: Name of the table
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      column_name:
                        type: string
                        example: "id_producto"
                        description: Column name
                      data_type:
                        type: string
                        example: "INTEGER"
                        description: SQL data type
                      is_nullable:
                        type: boolean
                        example: false
                        description: Whether column accepts NULL values
                      is_primary_key:
                        type: boolean
                        example: true
                        description: Whether column is part of primary key
                      default_value:
                        type: string
                        example: null
                        description: Default value if any
                  description: Array of column definitions
      400:
        description: Validation error (table name is empty or invalid)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Table name is required"
      401:
        description: Unauthorized (missing or invalid JWT token)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Missing or invalid token"
      403:
        description: Forbidden (insufficient permissions - requires analyst or admin role)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Insufficient permissions. Analyst or admin role required"
      404:
        description: Table not found in the database
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Table 'InvalidTableName' not found"
      500:
        description: Server error (DuckDB connection failure)
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Failed to retrieve schema for table 'Productos'"
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
