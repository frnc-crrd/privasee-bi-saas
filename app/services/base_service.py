"""
Base service class with common functionality.

All service classes should inherit from BaseService to ensure
consistent error handling, logging, and transaction management.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from app.extensions import db
from app.exceptions.base import DatabaseException


T = TypeVar('T')


class BaseService(Generic[T]):
    """
    Base service class with common CRUD operations and utilities.

    All service classes should inherit from this to maintain consistency
    across the service layer.
    """

    def __init__(self, repository) -> None:
        """
        Initialize service with a repository.

        Args:
            repository: Repository instance for data access
        """
        self.repository = repository

    def commit_or_rollback(self) -> None:
        """
        Commit database transaction or rollback on error.

        Raises:
            DatabaseException: If commit fails
        """
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database commit failed: {str(e)}")
            raise DatabaseException(f"Failed to save changes: {str(e)}") from e

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        try:
            return self.repository.get_by_id(entity_id)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to get entity by ID {entity_id}: {str(e)}")
            raise DatabaseException(f"Failed to retrieve entity: {str(e)}") from e

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Get all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        try:
            return self.repository.get_all(skip=skip, limit=limit)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to get all entities: {str(e)}")
            raise DatabaseException(f"Failed to retrieve entities: {str(e)}") from e

    def create(self, entity: T) -> T:
        """
        Create new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with ID assigned

        Raises:
            DatabaseException: If creation fails
        """
        try:
            created = self.repository.create(entity)
            self.commit_or_rollback()
            return created
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to create entity: {str(e)}")
            raise DatabaseException(f"Failed to create entity: {str(e)}") from e

    def update(self, entity: T) -> T:
        """
        Update existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity

        Raises:
            DatabaseException: If update fails
        """
        try:
            updated = self.repository.update(entity)
            self.commit_or_rollback()
            return updated
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to update entity: {str(e)}")
            raise DatabaseException(f"Failed to update entity: {str(e)}") from e

    def delete(self, entity_id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: ID of entity to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseException: If deletion fails
        """
        try:
            deleted = self.repository.delete(entity_id)
            if deleted:
                self.commit_or_rollback()
            return deleted
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to delete entity {entity_id}: {str(e)}")
            raise DatabaseException(f"Failed to delete entity: {str(e)}") from e

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching filters.

        Args:
            filters: Optional filters dictionary

        Returns:
            Count of matching entities
        """
        try:
            return self.repository.count(filters=filters)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to count entities: {str(e)}")
            raise DatabaseException(f"Failed to count entities: {str(e)}") from e

    def exists(self, entity_id: int) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity exists, False otherwise
        """
        try:
            return self.repository.exists(entity_id)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to check entity existence: {str(e)}")
            raise DatabaseException(f"Failed to check entity: {str(e)}") from e

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log service action for audit trail.

        Args:
            action: Action name (e.g., 'user_created', 'login_attempt')
            details: Optional details dictionary
        """
        log_message = f"Service action: {action}"
        if details:
            log_message += f" | Details: {details}"

        current_app.logger.info(log_message)
