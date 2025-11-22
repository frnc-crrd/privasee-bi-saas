"""
Database Connectivity Diagnostic Tool
-------------------------------------
Standalone script to validate connectivity to the SQL Server instance.
It bypasses the ETL pipeline to isolate driver, network, or credential issues.

Usage:
    python tests/diagnose_connection.py
"""

import logging
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, exc, text

# Configure Enterprise Logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def mask_connection_string(conn_str: Optional[str]) -> str:
    """
    Safely masks credentials in the connection string for logging purposes.
    """
    if not conn_str:
        return "None"
    try:
        # Simple logic to mask the password section for display
        # Assumes format: driver://user:password@host...
        prefix, rest = conn_str.split("://", 1)
        return f"{prefix}://***:***@{rest.split('@')[-1]}"
    except Exception:
        return "Invalid Connection String Format"


def run_diagnostic() -> None:
    """
    Executes a connectivity test against the configured SQL Server.
    """
    # 1. Load Environment Variables
    load_dotenv()
    conn_str = os.getenv("SOURCES__SQL_SERVER__CREDENTIALS")

    if not conn_str:
        logger.error("Environment variable 'SOURCES__SQL_SERVER__CREDENTIALS' is missing.")
        sys.exit(1)

    logger.info("--- STARTING CONNECTIVITY DIAGNOSTIC ---")
    logger.info(f"Target Connection: {mask_connection_string(conn_str)}")

    engine = None

    try:
        # 2. Initialize SQLAlchemy Engine
        logger.info("Initializing SQLAlchemy engine...")
        # We set a short timeout to fail fast if the firewall is blocking
        engine = create_engine(conn_str, connect_args={"timeout": 10})

        # 3. Attempt Connection
        logger.info("Attempting TCP handshake and authentication...")
        start_time = time.time()

        with engine.connect() as connection:
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Connection established successfully. Latency: {latency_ms:.2f}ms")

            # 4. Execute Test Query
            logger.info("Executing keep-alive query (SELECT 1)...")
            result = connection.execute(text("SELECT 1"))
            server_response = result.scalar()

            logger.info(f"Server responded: {server_response}")
            logger.info("Diagnostic completed successfully.")

    except exc.OperationalError as e:
        logger.error("OPERATIONAL ERROR: Connection failed.")
        logger.error("Root Cause Analysis suggestions:")
        logger.error("1. Firewall: Ensure outbound port 1433 is open and IP is whitelisted.")
        logger.error("2. Driver: Ensure 'msodbcsql18' is correctly installed via odbcinst.")
        logger.error(
            "3. SSL: If using self-signed certs, ensure TrustServerCertificate=yes "
            "is in the string."
        )
        logger.debug(f"Technical Details: {e}")
        sys.exit(1)

    except exc.ArgumentError as e:
        logger.error("CONFIGURATION ERROR: Invalid connection string format.")
        logger.debug(f"Details: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {type(e).__name__}")
        logger.debug(f"Details: {e}")
        sys.exit(1)

    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    run_diagnostic()
