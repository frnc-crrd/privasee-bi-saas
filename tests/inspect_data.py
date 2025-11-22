"""
Database Schema & Data Inspection Tool
--------------------------------------
Provides a visual overview of the existing tables in the Data Warehouse
and samples records from key tables to verify data structure and content.

Usage:
    python tests/inspect_data.py
"""

import duckdb
import sys

DB_PATH = 'data/analytical_cube.duckdb'

def inspect_schema() -> None:
    """
    Prints the list of all tables and a sample of the 'sucursal' table.
    """
    try:
        # Context manager ensures the connection is closed automatically
        with duckdb.connect(DB_PATH) as conn:
            
            print("\n=== 1. EXISTING TABLES (SCHEMA) ===")
            conn.sql("SHOW ALL TABLES").show()

            print("\n=== 2. DATA SAMPLE: SUCURSAL (Top 3) ===")
            # Using a try-block specifically for the query in case the table is missing
            try:
                conn.sql("SELECT * FROM sales_mart.sucursal LIMIT 3").show()
            except duckdb.CatalogException:
                print("[WARN] Table 'sales_mart.sucursal' does not exist yet.")
                
    except Exception as e:
        print(f"[CRITICAL] Error inspecting database: {e}")

if __name__ == "__main__":
    inspect_schema()
