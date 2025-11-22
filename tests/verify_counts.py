"""
Data Quality Verification Script
--------------------------------
Performs quantitative validation of the Sales Mart tables in DuckDB.
Checks record counts against expected thresholds to ensure data integrity.

Usage:
    python tests/verify_counts.py
"""

import sys

import duckdb

# Configuration Constants
DB_PATH = "data/analytical_cube.duckdb"


def get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Establishes a connection to the DuckDB database."""
    try:
        return duckdb.connect(db_path)
    except Exception as e:
        print(f"[CRITICAL] Failed to connect to database at {db_path}: {e}")
        sys.exit(1)


def verify_counts() -> None:
    """
    Executes count queries on key dimensions and prints the results.
    """
    conn = get_db_connection(DB_PATH)

    print(f">> [INFO] verifying data quality in: {DB_PATH}")
    print("-" * 50)

    try:
        # 1. Verify Sucursales (Branches)
        # We use fetchone()[0] to get the scalar value directly
        count_sucursales: int = conn.sql("SELECT COUNT(*) FROM sales_mart.sucursal").fetchone()[0]
        print(f"Sucursales (Branches) Count: {count_sucursales}")

        # 2. Verify Productos (Products)
        count_productos: int = conn.sql("SELECT COUNT(*) FROM sales_mart.productos").fetchone()[0]
        print(f"Productos (Products) Count:  {count_productos}")

        # Business Logic Validation (Example)
        if count_sucursales == 0 or count_productos == 0:
            print("\n[WARNING] Tables appear to be empty. Check ETL pipeline.")
        else:
            print("\n[SUCCESS] Data counts look healthy.")

    except duckdb.CatalogException as e:
        print(f"\n[ERROR] Table not found or schema mismatch: {e}")
        print("Ensure the 'ingest_sales_data.py' pipeline has been executed successfully.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during verification: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    verify_counts()
