"""Database query performance monitoring with SQLAlchemy event listeners."""

import time
from typing import Any, Optional

from flask import current_app, has_app_context
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.core.metrics import record_db_query, update_db_connections


# Query performance tracking
class QueryPerformanceMonitor:
    """Monitor and log slow database queries."""

    # Threshold for slow query logging (in seconds)
    SLOW_QUERY_THRESHOLD = 0.5

    @staticmethod
    def setup_listeners(engine: Engine) -> None:
        """
        Set up SQLAlchemy event listeners for query monitoring.

        Args:
            engine: SQLAlchemy engine instance
        """
        event.listen(engine, "before_cursor_execute", QueryPerformanceMonitor._before_cursor_execute)
        event.listen(engine, "after_cursor_execute", QueryPerformanceMonitor._after_cursor_execute)

    @staticmethod
    def setup_pool_listeners(engine: Engine) -> None:
        """
        Set up connection pool monitoring.

        Args:
            engine: SQLAlchemy engine instance
        """
        pool = engine.pool
        event.listen(pool, "connect", QueryPerformanceMonitor._on_connect)
        event.listen(pool, "checkout", QueryPerformanceMonitor._on_checkout)
        event.listen(pool, "checkin", QueryPerformanceMonitor._on_checkin)

    @staticmethod
    def _before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool
    ) -> None:
        """
        Record query start time before execution.

        Args:
            conn: Database connection
            cursor: Database cursor
            statement: SQL statement
            parameters: Query parameters
            context: Execution context
            executemany: Whether executing multiple statements
        """
        conn.info.setdefault('query_start_time', []).append(time.time())

    @staticmethod
    def _after_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool
    ) -> None:
        """
        Calculate and log query duration after execution.

        Args:
            conn: Database connection
            cursor: Database cursor
            statement: SQL statement
            parameters: Query parameters
            context: Execution context
            executemany: Whether executing multiple statements
        """
        try:
            # Calculate duration
            query_start_times = conn.info.get('query_start_time', [])
            if not query_start_times:
                return

            start_time = query_start_times.pop()
            duration = time.time() - start_time

            # Determine query type
            query_type = QueryPerformanceMonitor._get_query_type(statement)

            # Record metric
            record_db_query(query_type, duration)

            # Log slow queries
            if duration >= QueryPerformanceMonitor.SLOW_QUERY_THRESHOLD:
                if has_app_context():
                    current_app.logger.warning(
                        f"Slow query detected ({duration:.3f}s): {statement[:200]}..."
                    )

        except Exception as e:
            # Don't let monitoring errors break the application
            if has_app_context():
                current_app.logger.error(f"Query monitoring error: {str(e)}")

    @staticmethod
    def _get_query_type(statement: str) -> str:
        """
        Determine query type from SQL statement.

        Args:
            statement: SQL statement

        Returns:
            Query type (select, insert, update, delete, other)
        """
        statement_upper = statement.strip().upper()

        if statement_upper.startswith('SELECT'):
            return 'select'
        elif statement_upper.startswith('INSERT'):
            return 'insert'
        elif statement_upper.startswith('UPDATE'):
            return 'update'
        elif statement_upper.startswith('DELETE'):
            return 'delete'
        else:
            return 'other'

    @staticmethod
    def _on_connect(dbapi_conn: Any, connection_record: Any) -> None:
        """
        Handle new database connection.

        Args:
            dbapi_conn: DBAPI connection
            connection_record: Connection record
        """
        if has_app_context():
            current_app.logger.debug("New database connection established")

    @staticmethod
    def _on_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
        """
        Handle connection checkout from pool.

        Args:
            dbapi_conn: DBAPI connection
            connection_record: Connection record
            connection_proxy: Connection proxy
        """
        try:
            # Get pool size from the connection proxy's pool
            pool = connection_proxy._pool
            if pool:
                # Update connection pool metrics
                checked_out = pool.checkedout()
                update_db_connections(checked_out)
        except Exception:
            # Silently ignore pool monitoring errors
            pass

    @staticmethod
    def _on_checkin(dbapi_conn: Any, connection_record: Any) -> None:
        """
        Handle connection checkin to pool.

        Args:
            dbapi_conn: DBAPI connection
            connection_record: Connection record
        """
        # Connection returned to pool - metrics updated on next checkout
        pass


def init_query_monitoring(app: Any) -> None:
    """
    Initialize query performance monitoring for the application.

    Args:
        app: Flask application instance
    """
    from app.extensions import db

    # Set up query monitoring
    engine = db.engine
    QueryPerformanceMonitor.setup_listeners(engine)
    QueryPerformanceMonitor.setup_pool_listeners(engine)

    app.logger.info("Database query performance monitoring initialized")
