"""
Database Schema Inspection Utility
----------------------------------
Diagnostic tool designed to retrieve and list all available tables within
a specific schema of the connected SQL Server instance.

This script is essential for validating:
1. Connectivity permissions.
2. Schema visibility (e.g., ensuring the user can see 'dbo').
3. Exact table naming conventions (case sensitivity checks).

Usage:
    python tests/inspect_schema.py
"""

import logging
import os
import sys
from typing import List

from sqlalchemy import create_engine, inspect, exc
from dotenv import load_dotenv

# Configure Enterprise Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def get_db_connection_string() -> str:
    """
    Retrieves the connection string from the environment.
    Raises an error if the variable is missing to ensure fail-fast behavior.
    """
    load_dotenv()
    conn_str = os.getenv("SOURCES__SQL_SERVER__CREDENTIALS")
    
    if not conn_str:
        logger.error("Environment variable 'SOURCES__SQL_SERVER__CREDENTIALS' is not defined.")
        sys.exit(1)
        
    return conn_str

def inspect_schema(target_schema: str = "dbo") -> None:
    """
    Connects to the database and lists all tables found in the specified schema.
    
    Args:
        target_schema (str): The database schema to inspect (default: 'dbo').
    """
    connection_string = get_db_connection_string()
    
    # Mask password for security logging
    masked_uri = connection_string.split("@")[-1] if "@" in connection_string else "******"
    logger.info(f"Connecting to database host: {masked_uri}")

    try:
        # Initialize SQLAlchemy Engine
        # echo=False disables verbose SQL logging to keep output clean
        engine = create_engine(connection_string, echo=False)
        
        # Initialize Inspector
        inspector = inspect(engine)
        
        # Retrieve table names
        logger.info(f"Inspecting schema: '{target_schema}'...")
        tables: List[str] = inspector.get_table_names(schema=target_schema)
        
        if not tables:
            logger.warning(f"No tables found in schema '{target_schema}'. Check permissions or schema name.")
            return

        logger.info(f"Successfully retrieved {len(tables)} tables:")
        print("-" * 50)
        for table in tables:
            # Print directly to stdout for clear visibility
            print(f" - {table}")
        print("-" * 50)

    except exc.OperationalError as e:
        logger.error("Operational Error: Connection failed.")
        logger.debug(f"Technical Details: {e}")
    except exc.NoSuchModuleError as e:
        logger.error("Driver Error: Missing database driver (e.g., pyodbc, msodbcsql18).")
        logger.debug(f"Technical Details: {e}")
    except Exception as e:
        logger.error(f"Unexpected Error: {type(e).__name__}")
        logger.error(e)
    finally:
        # Ensure resources are released
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    inspect_schema()
