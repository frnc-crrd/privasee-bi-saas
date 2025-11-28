"""Integration tests for health check and monitoring endpoints.

This module provides comprehensive integration tests for health check endpoints,
including overall system health, readiness probes, and liveness probes.
These endpoints are critical for Kubernetes deployments and load balancer health monitoring.

Test Coverage:
    - Overall health check with all components
    - Liveness probe for process health
    - Readiness probe for traffic acceptance
    - Database health verification
    - Component status aggregation
    - Error handling for unhealthy components
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError


class TestHealthCheckEndpoint:
    """Test suite for the overall health check endpoint."""

    def test_health_check_all_healthy(self, client):
        """Test health check returns 200 when all components are healthy.

        This test verifies that when all system components (database, application)
        are functioning correctly, the health endpoint returns a successful status.

        Assertions:
            - Response status code is 200
            - Overall status is 'healthy'
            - Response contains timestamp
            - Response contains checks for all components
            - Database check status is 'healthy'
            - Application check status is 'healthy'

        Test Data:
            - Endpoint: GET /health
            - Expected Components: database, application
        """
        # Act
        response = client.get('/health')
        data = response.get_json()

        # Assert
        assert response.status_code == 200
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'checks' in data
        assert 'database' in data['checks']
        assert 'application' in data['checks']
        assert data['checks']['database']['status'] == 'healthy'
        assert data['checks']['application']['status'] == 'healthy'

    def test_health_check_database_unhealthy(self, client, app):
        """Test health check returns 503 when database is unhealthy.

        This test simulates a database connection failure and verifies that
        the health endpoint correctly reports an unhealthy status.

        Assertions:
            - Response status code is 503
            - Overall status is 'unhealthy'
            - Database check status is 'unhealthy'
            - Database check contains error message
            - Application check status is still 'healthy'

        Test Data:
            - Simulated Error: Database connection failure
            - Expected Status Code: 503 (Service Unavailable)
        """
        # Arrange: Mock database failure
        with app.app_context():
            with patch('app.extensions.db.session.execute') as mock_execute:
                mock_execute.side_effect = OperationalError(
                    "Connection refused",
                    params=None,
                    orig=Exception("Database unavailable")
                )

                # Act
                response = client.get('/health')
                data = response.get_json()

                # Assert
                assert response.status_code == 503
                assert data['status'] == 'unhealthy'
                assert data['checks']['database']['status'] == 'unhealthy'
                assert 'Database connection failed' in data['checks']['database']['message']
                assert data['checks']['application']['status'] == 'healthy'

    def test_health_check_contains_timestamp(self, client):
        """Test health check response includes ISO-formatted timestamp.

        This test verifies that the health check response includes a valid
        timestamp in ISO 8601 format for audit and monitoring purposes.

        Assertions:
            - Response contains 'timestamp' field
            - Timestamp is in ISO 8601 format
            - Timestamp contains timezone information

        Test Data:
            - Expected Format: YYYY-MM-DDTHH:MM:SS.mmmmmm+00:00
        """
        # Act
        response = client.get('/health')
        data = response.get_json()

        # Assert
        assert 'timestamp' in data
        assert 'T' in data['timestamp']  # ISO 8601 format
        assert data['timestamp'].endswith('+00:00') or data['timestamp'].endswith('Z')

    def test_health_check_component_details(self, client):
        """Test health check provides detailed component information.

        This test verifies that the health check endpoint returns comprehensive
        status information for each monitored component.

        Assertions:
            - Database check contains status and message
            - Application check contains status, message, and uptime
            - Component messages are descriptive

        Test Data:
            - Expected Database Message: 'Database connection successful'
            - Expected Application Message: 'Application running normally'
        """
        # Act
        response = client.get('/health')
        data = response.get_json()

        # Assert
        database_check = data['checks']['database']
        application_check = data['checks']['application']

        assert 'status' in database_check
        assert 'message' in database_check
        assert database_check['message'] == 'Database connection successful'

        assert 'status' in application_check
        assert 'message' in application_check
        assert 'uptime' in application_check
        assert application_check['message'] == 'Application running normally'


class TestLivenessProbe:
    """Test suite for Kubernetes liveness probe endpoint."""

    def test_liveness_probe_always_succeeds(self, client):
        """Test liveness probe returns 200 when process is running.

        The liveness probe is a lightweight check that indicates the application
        process is alive. It should always return 200 OK if the server is responding.

        Assertions:
            - Response status code is 200
            - Status is 'alive'
            - Response contains timestamp

        Test Data:
            - Endpoint: GET /health/liveness
            - Expected Status: 'alive'
        """
        # Act
        response = client.get('/health/liveness')
        data = response.get_json()

        # Assert
        assert response.status_code == 200
        assert data['status'] == 'alive'
        assert 'timestamp' in data

    def test_liveness_probe_no_dependency_checks(self, client, app):
        """Test liveness probe succeeds even when dependencies are down.

        The liveness probe should not check external dependencies, as it only
        indicates whether the application process is responsive.

        Assertions:
            - Response status code is 200
            - Status is 'alive'
            - Response does not contain dependency checks

        Test Data:
            - Simulated Condition: Database unavailable
            - Expected Behavior: Liveness probe still succeeds
        """
        # Arrange: Mock database failure
        with app.app_context():
            with patch('app.extensions.db.session.execute') as mock_execute:
                mock_execute.side_effect = OperationalError(
                    "Connection refused",
                    params=None,
                    orig=Exception("Database unavailable")
                )

                # Act
                response = client.get('/health/liveness')
                data = response.get_json()

                # Assert
                assert response.status_code == 200
                assert data['status'] == 'alive'
                assert 'checks' not in data

    def test_liveness_probe_response_structure(self, client):
        """Test liveness probe returns minimal response structure.

        The liveness probe should return a lightweight response with only
        essential information to minimize overhead.

        Assertions:
            - Response contains exactly 'status' and 'timestamp'
            - No additional fields are present

        Test Data:
            - Expected Fields: status, timestamp
        """
        # Act
        response = client.get('/health/liveness')
        data = response.get_json()

        # Assert
        assert 'status' in data
        assert 'timestamp' in data
        assert len(data) == 2  # Only status and timestamp


class TestReadinessProbe:
    """Test suite for Kubernetes readiness probe endpoint."""

    def test_readiness_probe_ready_when_database_healthy(self, client):
        """Test readiness probe returns 200 when all dependencies are healthy.

        The readiness probe indicates whether the application is ready to accept
        traffic. It checks critical dependencies like the database.

        Assertions:
            - Response status code is 200
            - Status is 'ready'
            - Response contains timestamp
            - Response contains database check
            - Database status is 'healthy'

        Test Data:
            - Endpoint: GET /health/readiness
            - Expected Status: 'ready'
        """
        # Act
        response = client.get('/health/readiness')
        data = response.get_json()

        # Assert
        assert response.status_code == 200
        assert data['status'] == 'ready'
        assert 'timestamp' in data
        assert 'checks' in data
        assert 'database' in data['checks']
        assert data['checks']['database']['status'] == 'healthy'

    def test_readiness_probe_not_ready_when_database_down(self, client, app):
        """Test readiness probe returns 503 when database is unavailable.

        When critical dependencies are unavailable, the application should
        report itself as not ready to prevent traffic routing.

        Assertions:
            - Response status code is 503
            - Status is 'not_ready'
            - Database check status is 'unhealthy'
            - Database check contains error message

        Test Data:
            - Simulated Error: Database connection failure
            - Expected Status Code: 503 (Service Unavailable)
        """
        # Arrange: Mock database failure
        with app.app_context():
            with patch('app.extensions.db.session.execute') as mock_execute:
                mock_execute.side_effect = OperationalError(
                    "Connection refused",
                    params=None,
                    orig=Exception("Database unavailable")
                )

                # Act
                response = client.get('/health/readiness')
                data = response.get_json()

                # Assert
                assert response.status_code == 503
                assert data['status'] == 'not_ready'
                assert data['checks']['database']['status'] == 'unhealthy'
                assert 'Database connection failed' in data['checks']['database']['message']

    def test_readiness_probe_includes_dependency_details(self, client):
        """Test readiness probe provides detailed dependency status.

        The readiness probe should include comprehensive information about
        each checked dependency for troubleshooting purposes.

        Assertions:
            - Response contains checks object
            - Database check contains status and message
            - Message indicates successful connection

        Test Data:
            - Expected Message: 'Database connection successful'
        """
        # Act
        response = client.get('/health/readiness')
        data = response.get_json()

        # Assert
        assert 'checks' in data
        database_check = data['checks']['database']
        assert 'status' in database_check
        assert 'message' in database_check
        assert database_check['message'] == 'Database connection successful'

    def test_readiness_probe_response_format(self, client):
        """Test readiness probe response follows standardized format.

        This test verifies that the readiness probe response adheres to
        the expected format for monitoring tools and orchestrators.

        Assertions:
            - Response is valid JSON
            - Contains status, timestamp, and checks
            - Timestamp is in ISO format

        Test Data:
            - Expected Structure: {status, timestamp, checks}
        """
        # Act
        response = client.get('/health/readiness')
        data = response.get_json()

        # Assert
        assert isinstance(data, dict)
        assert 'status' in data
        assert 'timestamp' in data
        assert 'checks' in data
        assert 'T' in data['timestamp']  # ISO format


class TestDatabaseHealthCheck:
    """Test suite for database health check functionality."""

    def test_database_health_check_rollback_on_error(self, client, app):
        """Test database health check performs rollback on connection error.

        This test verifies that the health check properly rolls back the database
        session on error to prevent connection pool exhaustion.

        Assertions:
            - Database session rollback is called on error
            - Error message is included in response
            - Status is 'unhealthy'

        Test Data:
            - Simulated Error: Connection pool exhaustion
        """
        # Arrange: Mock database failure and rollback
        with app.app_context():
            with patch('app.extensions.db.session.execute') as mock_execute, \
                 patch('app.extensions.db.session.rollback') as mock_rollback, \
                 patch('app.extensions.db.session.commit') as mock_commit:

                mock_execute.side_effect = OperationalError(
                    "Connection pool exhausted",
                    params=None,
                    orig=Exception("Too many connections")
                )

                # Act
                response = client.get('/health')
                data = response.get_json()

                # Assert
                mock_rollback.assert_called()
                assert data['checks']['database']['status'] == 'unhealthy'
                assert 'Connection pool exhausted' in data['checks']['database']['message']

    def test_database_health_check_commit_on_success(self, client, app):
        """Test database health check commits transaction on success.

        This test verifies that successful database checks properly commit
        the transaction to release the connection.

        Assertions:
            - Database session commit is called
            - Status is 'healthy'
            - Success message is included

        Test Data:
            - Expected Message: 'Database connection successful'
        """
        # Arrange
        with app.app_context():
            with patch('app.extensions.db.session.commit') as mock_commit:
                # Act
                response = client.get('/health')
                data = response.get_json()

                # Assert
                mock_commit.assert_called()
                assert data['checks']['database']['status'] == 'healthy'
                assert data['checks']['database']['message'] == 'Database connection successful'
