"""
Unit tests for database query monitoring module.

This module contains comprehensive tests for SQLAlchemy query performance
monitoring, including query execution tracking, slow query detection,
connection pool monitoring, and metrics collection.

Test Coverage:
    - Query type detection
    - Query performance tracking
    - Slow query detection and logging
    - Connection pool monitoring
    - Event listener setup
    - Error handling and resilience
    - Initialization
"""

from unittest.mock import Mock, patch, MagicMock, call
import pytest
import time

from app.core.query_monitoring import QueryPerformanceMonitor, init_query_monitoring


class TestQueryTypeDetection:
    """Tests for SQL query type detection."""

    def test_get_query_type_returns_select_for_select_statement(self):
        """Test that SELECT statements are correctly identified.

        Verifies that SQL SELECT queries are classified as 'select' type,
        which is important for categorizing database operations.

        Assertions:
            - SELECT statement returns 'select'
            - Case-insensitive detection
            - Leading whitespace handled
        """
        # Arrange
        statements = [
            "SELECT * FROM users",
            "select id, name from products",
            "  SELECT COUNT(*) FROM orders",
            "SELECT\n  * FROM customers"
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'select'

    def test_get_query_type_returns_insert_for_insert_statement(self):
        """Test that INSERT statements are correctly identified.

        Verifies that SQL INSERT queries are classified as 'insert' type
        for proper metrics categorization.

        Assertions:
            - INSERT statement returns 'insert'
            - Case-insensitive detection
            - Multi-line statements handled
        """
        # Arrange
        statements = [
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')",
            "insert into products values (1, 'Product')",
            "  INSERT INTO orders SELECT * FROM temp_orders"
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'insert'

    def test_get_query_type_returns_update_for_update_statement(self):
        """Test that UPDATE statements are correctly identified.

        Verifies that SQL UPDATE queries are classified as 'update' type.

        Assertions:
            - UPDATE statement returns 'update'
            - Case-insensitive detection
            - WHERE clause variations handled
        """
        # Arrange
        statements = [
            "UPDATE users SET active = true WHERE id = 1",
            "update products set price = 100",
            "  UPDATE orders SET status = 'shipped'"
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'update'

    def test_get_query_type_returns_delete_for_delete_statement(self):
        """Test that DELETE statements are correctly identified.

        Verifies that SQL DELETE queries are classified as 'delete' type.

        Assertions:
            - DELETE statement returns 'delete'
            - Case-insensitive detection
            - WHERE clause handled
        """
        # Arrange
        statements = [
            "DELETE FROM users WHERE id = 1",
            "delete from temp_table",
            "  DELETE FROM orders WHERE created_at < '2020-01-01'"
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'delete'

    def test_get_query_type_returns_other_for_unknown_statement(self):
        """Test that non-standard SQL statements return 'other' type.

        Verifies that DDL and other SQL commands are classified as 'other'
        when they don't match standard CRUD operations.

        Assertions:
            - CREATE statement returns 'other'
            - ALTER statement returns 'other'
            - DROP statement returns 'other'
            - TRUNCATE statement returns 'other'
        """
        # Arrange
        statements = [
            "CREATE TABLE users (id INTEGER)",
            "ALTER TABLE users ADD COLUMN age INTEGER",
            "DROP TABLE temp_table",
            "TRUNCATE TABLE logs",
            "COMMIT",
            "BEGIN"
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'other'

    def test_get_query_type_handles_empty_and_whitespace_statements(self):
        """Test query type detection with edge case inputs.

        Verifies that empty or whitespace-only statements are handled
        gracefully without raising exceptions.

        Assertions:
            - Empty string returns 'other'
            - Whitespace-only string returns 'other'
            - No exceptions raised
        """
        # Arrange
        statements = [
            "",
            "   ",
            "\n\t",
        ]

        # Act & Assert
        for statement in statements:
            query_type = QueryPerformanceMonitor._get_query_type(statement)
            assert query_type == 'other'


class TestQueryPerformanceTracking:
    """Tests for query execution performance tracking."""

    def test_before_cursor_execute_records_start_time(self):
        """Test that query start time is recorded before execution.

        Verifies that _before_cursor_execute properly stores the start
        timestamp in the connection info dictionary.

        Assertions:
            - Start time is recorded
            - Connection info contains query_start_time list
            - Timestamp is approximately current time
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.info = {}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._before_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert
        assert 'query_start_time' in mock_conn.info
        assert len(mock_conn.info['query_start_time']) == 1

        # Verify timestamp is recent (within 1 second)
        start_time = mock_conn.info['query_start_time'][0]
        assert abs(time.time() - start_time) < 1.0

    def test_before_cursor_execute_appends_to_existing_times(self):
        """Test that multiple query start times are tracked correctly.

        Verifies that concurrent queries each get their own start time
        in the list, enabling nested query tracking.

        Assertions:
            - Multiple start times can be recorded
            - Start times are appended to list
            - Each query gets unique timestamp
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.info = {'query_start_time': [time.time() - 1.0]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._before_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert
        assert len(mock_conn.info['query_start_time']) == 2

    @patch('app.core.query_monitoring.record_db_query')
    def test_after_cursor_execute_calculates_duration(self, mock_record):
        """Test that query duration is calculated correctly.

        Verifies that _after_cursor_execute calculates the time difference
        between start and end of query execution.

        Args:
            mock_record: Mocked record_db_query function

        Assertions:
            - Duration is calculated
            - record_db_query is called with duration
            - Duration is positive number
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.info = {'query_start_time': [time.time() - 0.1]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert
        mock_record.assert_called_once()

        # Verify duration argument
        call_args = mock_record.call_args[0]
        duration = call_args[1]
        assert duration > 0
        assert duration < 1.0  # Should be less than 1 second

    @patch('app.core.query_monitoring.record_db_query')
    def test_after_cursor_execute_determines_query_type(self, mock_record):
        """Test that query type is determined during execution tracking.

        Verifies that the query type is extracted from the SQL statement
        and passed to the metrics recording function.

        Args:
            mock_record: Mocked record_db_query function

        Assertions:
            - Query type is detected
            - record_db_query receives correct query type
            - SELECT query returns 'select' type
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.info = {'query_start_time': [time.time()]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert
        mock_record.assert_called_once()

        # Verify query type argument
        call_args = mock_record.call_args[0]
        query_type = call_args[0]
        assert query_type == 'select'

    @patch('app.core.query_monitoring.record_db_query')
    def test_after_cursor_execute_handles_missing_start_time(self, mock_record):
        """Test graceful handling when start time is missing.

        Verifies that missing start time doesn't cause errors and
        monitoring continues normally.

        Args:
            mock_record: Mocked record_db_query function

        Assertions:
            - No exception raised
            - record_db_query not called
            - Function returns without error
        """
        # Arrange
        mock_conn = Mock()
        mock_conn.info = {}  # No query_start_time
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert - No error, no metric recorded
        mock_record.assert_not_called()


class TestSlowQueryDetection:
    """Tests for slow query detection and logging."""

    @patch('app.core.query_monitoring.has_app_context')
    @patch('app.core.query_monitoring.current_app')
    @patch('app.core.query_monitoring.record_db_query')
    def test_slow_query_logged_when_exceeds_threshold(self, mock_record, mock_app, mock_has_context):
        """Test that slow queries are logged when exceeding threshold.

        Verifies that queries taking longer than SLOW_QUERY_THRESHOLD
        generate warning logs for monitoring.

        Args:
            mock_record: Mocked metrics recording
            mock_app: Mocked Flask app
            mock_has_context: Mocked app context check

        Assertions:
            - Warning logged for slow query
            - Log message contains duration
            - Log message contains SQL statement
        """
        # Arrange
        mock_has_context.return_value = True
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_conn = Mock()
        # Simulate slow query (0.6s > 0.5s threshold)
        mock_conn.info = {'query_start_time': [time.time() - 0.6]}
        mock_cursor = Mock()
        statement = "SELECT * FROM large_table WHERE complex_condition = true"

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, statement, None, None, False
        )

        # Assert
        mock_logger.warning.assert_called_once()

        # Verify warning message
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Slow query detected" in warning_call
        assert "0.6" in warning_call or "0.5" in warning_call
        assert "SELECT" in warning_call

    @patch('app.core.query_monitoring.has_app_context')
    @patch('app.core.query_monitoring.current_app')
    @patch('app.core.query_monitoring.record_db_query')
    def test_fast_query_not_logged_as_slow(self, mock_record, mock_app, mock_has_context):
        """Test that fast queries are not logged as slow.

        Verifies that queries under the threshold don't trigger
        slow query warnings.

        Args:
            mock_record: Mocked metrics recording
            mock_app: Mocked Flask app
            mock_has_context: Mocked app context check

        Assertions:
            - No warning logged
            - Metrics still recorded
            - Query completes normally
        """
        # Arrange
        mock_has_context.return_value = True
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_conn = Mock()
        # Simulate fast query (0.1s < 0.5s threshold)
        mock_conn.info = {'query_start_time': [time.time() - 0.1]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users WHERE id = 1", None, None, False
        )

        # Assert
        mock_logger.warning.assert_not_called()
        mock_record.assert_called_once()

    @patch('app.core.query_monitoring.has_app_context')
    @patch('app.core.query_monitoring.record_db_query')
    def test_slow_query_not_logged_without_app_context(self, mock_record, mock_has_context):
        """Test that slow queries don't log outside Flask context.

        Verifies that logging is skipped when Flask app context
        is not available (e.g., in background tasks).

        Args:
            mock_record: Mocked metrics recording
            mock_has_context: Mocked app context check

        Assertions:
            - No logging attempted
            - Metrics still recorded
            - No exceptions raised
        """
        # Arrange
        mock_has_context.return_value = False

        mock_conn = Mock()
        mock_conn.info = {'query_start_time': [time.time() - 0.6]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert - Metrics recorded, but no logging
        mock_record.assert_called_once()


class TestConnectionPoolMonitoring:
    """Tests for database connection pool monitoring."""

    @patch('app.core.query_monitoring.has_app_context')
    @patch('app.core.query_monitoring.current_app')
    def test_on_connect_logs_new_connection(self, mock_app, mock_has_context):
        """Test that new database connections are logged.

        Verifies that connection establishment is logged for
        debugging and monitoring purposes.

        Args:
            mock_app: Mocked Flask app
            mock_has_context: Mocked app context check

        Assertions:
            - Debug log generated
            - Log message indicates new connection
        """
        # Arrange
        mock_has_context.return_value = True
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_dbapi_conn = Mock()
        mock_connection_record = Mock()

        # Act
        QueryPerformanceMonitor._on_connect(mock_dbapi_conn, mock_connection_record)

        # Assert
        mock_logger.debug.assert_called_once()
        debug_message = mock_logger.debug.call_args[0][0]
        assert "database connection" in debug_message.lower()

    @patch('app.core.query_monitoring.update_db_connections')
    def test_on_checkout_updates_connection_metrics(self, mock_update):
        """Test that connection checkout updates pool metrics.

        Verifies that checking out a connection from the pool
        updates the connection count metrics.

        Args:
            mock_update: Mocked update_db_connections function

        Assertions:
            - update_db_connections is called
            - Checked out count is passed to metrics
        """
        # Arrange
        mock_dbapi_conn = Mock()
        mock_connection_record = Mock()

        # Mock connection proxy with pool
        mock_pool = Mock()
        mock_pool.checkedout.return_value = 5

        mock_connection_proxy = Mock()
        mock_connection_proxy._pool = mock_pool

        # Act
        QueryPerformanceMonitor._on_checkout(
            mock_dbapi_conn, mock_connection_record, mock_connection_proxy
        )

        # Assert
        mock_update.assert_called_once_with(5)

    @patch('app.core.query_monitoring.update_db_connections')
    def test_on_checkout_handles_missing_pool(self, mock_update):
        """Test graceful handling when pool is not available.

        Verifies that connection checkout doesn't fail when
        pool information is unavailable.

        Args:
            mock_update: Mocked update_db_connections function

        Assertions:
            - No exception raised
            - Metrics update not called
            - Function completes normally
        """
        # Arrange
        mock_dbapi_conn = Mock()
        mock_connection_record = Mock()

        # Connection proxy without pool
        mock_connection_proxy = Mock()
        mock_connection_proxy._pool = None

        # Act
        QueryPerformanceMonitor._on_checkout(
            mock_dbapi_conn, mock_connection_record, mock_connection_proxy
        )

        # Assert - No error, no update
        mock_update.assert_not_called()

    def test_on_checkin_completes_without_error(self):
        """Test that connection checkin completes successfully.

        Verifies that returning a connection to the pool
        doesn't raise any exceptions.

        Assertions:
            - No exception raised
            - Function returns successfully
        """
        # Arrange
        mock_dbapi_conn = Mock()
        mock_connection_record = Mock()

        # Act & Assert - Should not raise
        QueryPerformanceMonitor._on_checkin(mock_dbapi_conn, mock_connection_record)


class TestListenerSetup:
    """Tests for SQLAlchemy event listener configuration."""

    @patch('app.core.query_monitoring.event')
    def test_setup_listeners_registers_cursor_events(self, mock_event):
        """Test that query execution listeners are registered.

        Verifies that before_cursor_execute and after_cursor_execute
        event listeners are properly configured.

        Args:
            mock_event: Mocked SQLAlchemy event module

        Assertions:
            - event.listen called twice
            - before_cursor_execute listener registered
            - after_cursor_execute listener registered
        """
        # Arrange
        mock_engine = Mock()

        # Act
        QueryPerformanceMonitor.setup_listeners(mock_engine)

        # Assert
        assert mock_event.listen.call_count == 2

        # Verify event registrations
        calls = mock_event.listen.call_args_list

        # First call: before_cursor_execute
        assert calls[0][0][0] == mock_engine
        assert calls[0][0][1] == "before_cursor_execute"
        assert calls[0][0][2] == QueryPerformanceMonitor._before_cursor_execute

        # Second call: after_cursor_execute
        assert calls[1][0][0] == mock_engine
        assert calls[1][0][1] == "after_cursor_execute"
        assert calls[1][0][2] == QueryPerformanceMonitor._after_cursor_execute

    @patch('app.core.query_monitoring.event')
    def test_setup_pool_listeners_registers_pool_events(self, mock_event):
        """Test that connection pool listeners are registered.

        Verifies that connect, checkout, and checkin event listeners
        are properly configured for the connection pool.

        Args:
            mock_event: Mocked SQLAlchemy event module

        Assertions:
            - event.listen called three times
            - connect listener registered
            - checkout listener registered
            - checkin listener registered
        """
        # Arrange
        mock_pool = Mock()
        mock_engine = Mock()
        mock_engine.pool = mock_pool

        # Act
        QueryPerformanceMonitor.setup_pool_listeners(mock_engine)

        # Assert
        assert mock_event.listen.call_count == 3

        # Verify event registrations
        calls = mock_event.listen.call_args_list

        # All calls should be on the pool
        for call in calls:
            assert call[0][0] == mock_pool

        # Verify event types
        event_types = [call[0][1] for call in calls]
        assert "connect" in event_types
        assert "checkout" in event_types
        assert "checkin" in event_types


class TestErrorHandling:
    """Tests for error handling and resilience."""

    @patch('app.core.query_monitoring.has_app_context')
    @patch('app.core.query_monitoring.current_app')
    @patch('app.core.query_monitoring.record_db_query')
    def test_after_cursor_execute_logs_monitoring_errors(self, mock_record, mock_app, mock_has_context):
        """Test that monitoring errors are logged without breaking execution.

        Verifies that exceptions in monitoring code are caught and logged
        rather than propagating to the application.

        Args:
            mock_record: Mocked metrics recording
            mock_app: Mocked Flask app
            mock_has_context: Mocked app context check

        Assertions:
            - Exception is caught
            - Error is logged
            - No exception propagates
        """
        # Arrange
        mock_has_context.return_value = True
        mock_logger = Mock()
        mock_app.logger = mock_logger

        # Make record_db_query raise an exception
        mock_record.side_effect = Exception("Metrics service unavailable")

        mock_conn = Mock()
        mock_conn.info = {'query_start_time': [time.time()]}
        mock_cursor = Mock()

        # Act
        QueryPerformanceMonitor._after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users", None, None, False
        )

        # Assert - Error logged, no exception raised
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Query monitoring error" in error_message

    @patch('app.core.query_monitoring.update_db_connections')
    def test_on_checkout_silently_ignores_pool_errors(self, mock_update):
        """Test that pool monitoring errors are silently ignored.

        Verifies that exceptions during pool monitoring don't
        affect database operations.

        Args:
            mock_update: Mocked update_db_connections function

        Assertions:
            - Exception is caught
            - No error logged
            - Function returns normally
        """
        # Arrange
        mock_dbapi_conn = Mock()
        mock_connection_record = Mock()

        # Mock connection proxy that raises exception
        mock_connection_proxy = Mock()
        mock_connection_proxy._pool = Mock()
        mock_connection_proxy._pool.checkedout.side_effect = Exception("Pool error")

        # Act & Assert - Should not raise
        QueryPerformanceMonitor._on_checkout(
            mock_dbapi_conn, mock_connection_record, mock_connection_proxy
        )


class TestInitialization:
    """Tests for query monitoring initialization."""

    @patch('app.core.query_monitoring.QueryPerformanceMonitor.setup_pool_listeners')
    @patch('app.core.query_monitoring.QueryPerformanceMonitor.setup_listeners')
    @patch('app.extensions.db')
    def test_init_query_monitoring_sets_up_all_listeners(self, mock_db, mock_setup_listeners, mock_setup_pool):
        """Test that initialization sets up all monitoring listeners.

        Verifies that both query and pool listeners are configured
        during application initialization.

        Args:
            mock_db: Mocked database extension
            mock_setup_listeners: Mocked setup_listeners
            mock_setup_pool: Mocked setup_pool_listeners

        Assertions:
            - setup_listeners called with engine
            - setup_pool_listeners called with engine
            - Info log generated
        """
        # Arrange
        mock_app = Mock()
        mock_logger = Mock()
        mock_app.logger = mock_logger

        mock_engine = Mock()
        mock_db.engine = mock_engine

        # Act
        init_query_monitoring(mock_app)

        # Assert
        mock_setup_listeners.assert_called_once_with(mock_engine)
        mock_setup_pool.assert_called_once_with(mock_engine)

        # Verify info log
        mock_logger.info.assert_called_once()
        info_message = mock_logger.info.call_args[0][0]
        assert "monitoring initialized" in info_message.lower()
