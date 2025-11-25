"""Base repository with generic CRUD operations.

This module provides the foundation for the Repository Pattern:
- Generic CRUD operations (Create, Read, Update, Delete)
- Type-safe operations with Generic[ModelType]
- Pagination and filtering support
- Soft delete support
- Batch operations
- Transaction handling

All repositories should inherit from BaseRepository to ensure
consistent data access patterns.

Usage:
    from app.repositories.base_repository import BaseRepository
    from app.models import User

    class UserRepository(BaseRepository[User]):
        def __init__(self):
            super().__init__(User)

    repo = UserRepository()
    user = repo.get_by_id(123)
    users = repo.get_all(limit=10)
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, asc, desc, select
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import DatabaseException, ResourceNotFoundException
from app.extensions import db

# Type variable for the model class
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic repository for database operations.

    Provides type-safe CRUD operations for any SQLAlchemy model.
    All methods handle database sessions and exceptions automatically.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages

    Attributes:
        model: The SQLAlchemy model class

    Example:
        >>> from app.models import User
        >>> repo = BaseRepository(User)
        >>> user = repo.get_by_id(123)
        >>> users = repo.get_all(limit=10, offset=0)
    """

    def __init__(self, model: Type[ModelType]):
        """Initialize repository with model class.

        Args:
            model: SQLAlchemy model class to manage

        Example:
            >>> repo = BaseRepository(User)
        """
        self.model = model

    def create(self, instance: Optional[ModelType] = None, **kwargs: Any) -> ModelType:
        """Create a new record.

        Args:
            instance: Optional pre-created model instance to save
            **kwargs: Field values for the new record (if instance not provided)

        Returns:
            Created model instance with ID assigned

        Raises:
            DatabaseException: If creation fails

        Example:
            >>> # Method 1: Pass instance
            >>> user = User(username="john", email="john@example.com")
            >>> repo.create(user)
            >>>
            >>> # Method 2: Pass kwargs
            >>> user = repo.create(username="john", email="john@example.com")
        """
        try:
            if instance is None:
                instance = self.model(**kwargs)
            db.session.add(instance)
            db.session.commit()
            db.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseException(
                message=f"Failed to create {self.model.__name__}",
                details={"error": str(e)},
            ) from e

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance if found, None otherwise

        Example:
            >>> user = repo.get_by_id(123)
            >>> if user:
            ...     print(user.username)
        """
        try:
            return db.session.get(self.model, id)
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to fetch {self.model.__name__}",
                details={"error": str(e), "id": id},
            ) from e

    def get_by_id_or_404(self, id: int) -> ModelType:
        """Get a record by ID or raise 404 error.

        Args:
            id: Primary key value

        Returns:
            Model instance

        Raises:
            ResourceNotFoundException: If record not found

        Example:
            >>> user = repo.get_by_id_or_404(123)
            >>> print(user.username)  # Guaranteed to exist
        """
        instance = self.get_by_id(id)
        if instance is None:
            raise ResourceNotFoundException(
                message=f"{self.model.__name__} not found",
                resource_type=self.model.__name__,
                resource_id=id,
            )
        return instance

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> List[ModelType]:
        """Get all records with optional pagination and ordering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by
            order_desc: Sort in descending order (default: False)

        Returns:
            List of model instances

        Raises:
            DatabaseException: If query fails

        Example:
            >>> users = repo.get_all(limit=10, offset=0, order_by="created_at")
            >>> recent_users = repo.get_all(limit=5, order_by="created_at", order_desc=True)
        """
        try:
            query = select(self.model)

            # Apply ordering
            if order_by:
                column = getattr(self.model, order_by, None)
                if column is not None:
                    query = query.order_by(desc(column) if order_desc else asc(column))

            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = db.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to fetch {self.model.__name__} records",
                details={"error": str(e)},
            ) from e

    def get_paginated(
        self,
        page: int = 1,
        per_page: int = 10,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Pagination:
        """Get paginated records with Flask-SQLAlchemy pagination.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            order_by: Field name to order by
            order_desc: Sort in descending order
            filters: Dictionary of field:value filters

        Returns:
            Pagination object with items and metadata

        Raises:
            DatabaseException: If query fails

        Example:
            >>> pagination = repo.get_paginated(page=1, per_page=10)
            >>> print(f"Total: {pagination.total}")
            >>> for user in pagination.items:
            ...     print(user.username)
        """
        try:
            query = select(self.model)

            # Apply filters
            if filters:
                for field, value in filters.items():
                    column = getattr(self.model, field, None)
                    if column is not None:
                        query = query.where(column == value)

            # Apply ordering
            if order_by:
                column = getattr(self.model, order_by, None)
                if column is not None:
                    query = query.order_by(desc(column) if order_desc else asc(column))

            return db.paginate(query, page=page, per_page=per_page, error_out=False)
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to paginate {self.model.__name__} records",
                details={"error": str(e)},
            ) from e

    def filter_by(self, **filters: Any) -> List[ModelType]:
        """Filter records by field values.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            List of matching model instances

        Raises:
            DatabaseException: If query fails

        Example:
            >>> active_users = repo.filter_by(is_active=True)
            >>> admin_users = repo.filter_by(role="admin", is_active=True)
        """
        try:
            query = select(self.model)
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)

            result = db.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to filter {self.model.__name__} records",
                details={"error": str(e), "filters": filters},
            ) from e

    def find_one_by(self, **filters: Any) -> Optional[ModelType]:
        """Find a single record by field values.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            First matching model instance or None

        Example:
            >>> user = repo.find_one_by(email="john@example.com")
            >>> if user:
            ...     print(user.username)
        """
        try:
            query = select(self.model)
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)

            result = db.session.execute(query.limit(1))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to find {self.model.__name__}",
                details={"error": str(e), "filters": filters},
            ) from e

    def update(self, id_or_instance, **kwargs: Any) -> ModelType:
        """Update a record by ID or instance.

        Args:
            id_or_instance: Primary key value (int) or model instance
            **kwargs: Fields to update with new values (ignored if instance passed)

        Returns:
            Updated model instance

        Raises:
            ResourceNotFoundException: If record not found
            DatabaseException: If update fails

        Example:
            >>> # Update by ID
            >>> user = repo.update(123, email="newemail@example.com")
            >>> # Update by instance
            >>> user.email = "newemail@example.com"
            >>> user = repo.update(user)
        """
        # Handle both ID and instance
        if isinstance(id_or_instance, int):
            instance = self.get_by_id_or_404(id_or_instance)
            # Apply kwargs updates
            for field, value in kwargs.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
        else:
            # id_or_instance is already an instance
            instance = id_or_instance

        try:
            db.session.commit()
            db.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            db.session.rollback()
            instance_id = getattr(instance, 'id', 'unknown')
            raise DatabaseException(
                message=f"Failed to update {self.model.__name__}",
                details={"error": str(e), "id": instance_id, "data": kwargs},
            ) from e

    def delete(self, id: int) -> None:
        """Delete a record by ID (hard delete).

        Args:
            id: Primary key value

        Raises:
            ResourceNotFoundException: If record not found
            DatabaseException: If deletion fails

        Example:
            >>> repo.delete(123)
        """
        instance = self.get_by_id_or_404(id)

        try:
            db.session.delete(instance)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseException(
                message=f"Failed to delete {self.model.__name__}",
                details={"error": str(e), "id": id},
            ) from e

    def soft_delete(self, id: int, deleted_field: str = "is_deleted") -> ModelType:
        """Soft delete a record by setting a flag.

        Args:
            id: Primary key value
            deleted_field: Name of the boolean field to set (default: "is_deleted")

        Returns:
            Updated model instance

        Raises:
            ResourceNotFoundException: If record not found
            DatabaseException: If update fails

        Example:
            >>> user = repo.soft_delete(123)
            >>> # Or with custom field name
            >>> user = repo.soft_delete(123, deleted_field="is_active")
        """
        return self.update(id, **{deleted_field: True})

    def count(self, **filters: Any) -> int:
        """Count records matching filters.

        Args:
            **filters: Field:value pairs to filter by

        Returns:
            Number of matching records

        Raises:
            DatabaseException: If query fails

        Example:
            >>> total_users = repo.count()
            >>> active_users = repo.count(is_active=True)
        """
        try:
            query = select(self.model)
            for field, value in filters.items():
                column = getattr(self.model, field, None)
                if column is not None:
                    query = query.where(column == value)

            result = db.session.execute(query)
            return len(list(result.scalars().all()))
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to count {self.model.__name__} records",
                details={"error": str(e), "filters": filters},
            ) from e

    def exists(self, id: int) -> bool:
        """Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if record exists, False otherwise

        Example:
            >>> if repo.exists(123):
            ...     print("User exists")
        """
        return self.get_by_id(id) is not None

    def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records in a single transaction.

        Args:
            items: List of dictionaries with field values

        Returns:
            List of created model instances

        Raises:
            DatabaseException: If bulk creation fails

        Example:
            >>> users = repo.bulk_create([
            ...     {"username": "user1", "email": "user1@example.com"},
            ...     {"username": "user2", "email": "user2@example.com"}
            ... ])
        """
        try:
            instances = [self.model(**item) for item in items]
            db.session.add_all(instances)
            db.session.commit()

            # Refresh all instances to get IDs
            for instance in instances:
                db.session.refresh(instance)

            return instances
        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseException(
                message=f"Failed to bulk create {self.model.__name__} records",
                details={"error": str(e), "count": len(items)},
            ) from e

    def execute_query(self, query: Select) -> List[ModelType]:
        """Execute a custom SQLAlchemy query.

        Args:
            query: SQLAlchemy Select statement

        Returns:
            List of model instances

        Raises:
            DatabaseException: If query execution fails

        Example:
            >>> from sqlalchemy import select
            >>> query = select(User).where(User.age > 18)
            >>> adults = repo.execute_query(query)
        """
        try:
            result = db.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseException(
                message=f"Failed to execute query on {self.model.__name__}",
                details={"error": str(e)},
            ) from e
