"""
Sales Data Ingestion Pipeline
-----------------------------
Orchestrator script responsible for extracting heavy load sales data from
the remote SQL Server (PITS_VENTAS_CENTRAL) and loading it into the
local Analytical Engine (DuckDB).

Architecture:
    - Extraction: Microsoft SQL Server (via ODBC Driver 18)
    - Transport:  dlt (Data Load Tool) stream processing
    - Load:       DuckDB (Local Data Warehouse / OLAP Cube)
    - Strategy:   Full Refresh (Replace) for initial setup.

Author: Data Engineering Team
"""

import os

import dlt
from dlt.sources.sql_database import sql_database
from dotenv import load_dotenv

# Load environment variables explicitly to ensure credentials are available
load_dotenv()


def load_sales_data() -> None:
    """
    Executes the ELT pipeline.

    This function initializes the dlt pipeline, configures the SQL source
    connector with specific table patterns, and executes the load job.

    The 'write_disposition="replace"' setting ensures idempotency by
    recreating the target tables on every run.
    """

    # 1. Retrieve Credentials Explicitly
    # ----------------------------------
    # We retrieve the connection string directly from the environment.
    # This avoids ambiguity with dlt's implicit configuration naming conventions.
    conn_string = os.getenv("SOURCES__SQL_SERVER__CREDENTIALS")

    if not conn_string:
        raise ValueError("CRITICAL: Variable 'SOURCES__SQL_SERVER__CREDENTIALS' not found in .env")

    # 2. Pipeline Configuration
    # -------------------------
    # 'pipeline_name': Defines the persistence scope (schema tracking).
    # 'destination':   Target system (DuckDB file).
    # 'dataset_name':  Logical grouping for tables in DuckDB (e.g., sales_mart.orders).
    # 'progress':      Enables TQDM progress bars in the console.
    pipeline = dlt.pipeline(
        pipeline_name="pits_central_loader",
        destination="duckdb",
        dataset_name="sales_mart",
        progress="tqdm",
    )

    # 3. Source Configuration
    # -----------------------
    # We map the generic 'sql_database' source to our specific infrastructure.
    # backend="pyodbc": Forces usage of the MS ODBC Driver 18 installed on Fedora.
    source = sql_database(
        credentials=conn_string,
        schema="dbo",
        table_names=[
            # "Ordenes",
            "Sucursal",
            "Productos",
            "Linea",
            "Sub_Linea",
            # "Detalle_Ordenes",  # Reserved for future heavy load implementation
        ],
        backend="pandas",
    )

    # 4. Execution
    # ------------
    print(">> [INFO] Initializing Data Ingestion from PITS_VENTAS_CENTRAL...")
    print(">> [INFO] Target: Local DuckDB (sales_mart)")

    # Run the pipeline with 'replace' strategy (Full Load)
    load_info = pipeline.run(source, write_disposition="replace")

    # 5. Reporting
    # ------------
    print(load_info)
    print(">> [SUCCESS] Pipeline execution completed.")


if __name__ == "__main__":
    load_sales_data()
