"""Unit of Work pattern for transaction boundary management.

Purpose: Provide a clean abstraction for managing database transactions
across multiple repository operations within a single business operation.

Responsibility: Coordinate session lifecycle, transaction control, and
repository instance management for ACID compliance.

Consumers: Services orchestrating multi-step operations (draft mutation,
PR creation, conflict resolution).

Restrictions: No business logic; only infrastructure coordination.

Reference: Backend Module Architecture §2.9 (Repository Layer - Transactions)
          Domain-Driven Design (Unit of Work pattern)
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("mif_copilot.repositories")


class UnitOfWork:
    """Unit of Work coordinator for multi-repository transactions.

    Purpose: Bundle multiple repository operations into a single transaction
    boundary. Ensures ACID properties across related data modifications.

    Design pattern: Dependency injection of session; repositories stored
    as instance attributes; single commit/rollback point.

    Example (service layer):
        >>> class DraftService:
        ...     async def add_glue_job_to_draft(self, draft_id, config):
        ...         async with UnitOfWork(session) as uow:
        ...             # All operations in this block share one transaction
        ...             draft = await uow.draft_repo.get(draft_id)
        ...             await uow.draft_repo.update(draft, ...)
        ...             await uow.glue_job_repo.add(config)
        ...             await uow.snapshot_repo.create(snapshot)
        ...             # Commit happens automatically on exit if no exception
        ...         # If exception raised, rollback occurs

    Transaction semantics:
        - All repository operations share the same session/transaction
        - Commit succeeds only if ALL operations succeed
        - Rollback on ANY exception
        - Atomicity: either all changes persist or none do

    Lifecycle:
        1. Create with session
        2. Access repositories via self.{repo_name}
        3. Perform operations
        4. Exit context manager (auto-commit/rollback)
    """

    def __init__(self, session: AsyncSession):
        """Initialize Unit of Work with a session.

        Args:
            session: AsyncSession instance for this transaction boundary.

        Note: Repositories are lazily instantiated on first access
        to avoid circular imports and unnecessary object creation.
        """
        self.session = session
        self._draft_repo = None
        self._file_repo = None
        self._job_repo = None
        self._snapshot_repo = None
        self._session_repo = None
        self._user_repo = None
        self._validation_repo = None
        self._pr_repo = None

    async def __aenter__(self):
        """Enter async context manager.

        Returns:
            self (this UnitOfWork instance)
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager.

        Behavior:
            - If no exception: await self.commit()
            - If exception raised: await self.rollback() (suppresses exception)

        Args:
            exc_type: Exception type if raised, None otherwise.
            exc_val: Exception instance if raised, None otherwise.
            exc_tb: Exception traceback if raised, None otherwise.

        Returns:
            None (don't suppress exceptions; let them propagate)
        """
        if exc_type is not None:
            await self.rollback()
            logger.error(
                f"UnitOfWork rollback due to {exc_type.__name__}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            await self.commit()
            logger.debug("UnitOfWork commit succeeded")

    async def commit(self) -> None:
        """Commit the transaction.

        Purpose: Persist all changes made through repositories in this UoW.

        Behavior:
            - Flushes all pending changes to database
            - Commits the transaction
            - Expires ORM objects (forces fresh load on next access)

        Raises:
            SQLAlchemyError: If commit fails (constraint violation, etc.)
                            — must be caught by caller

        Example:
            >>> async with UnitOfWork(session) as uow:
            ...     await uow.draft_repo.update(...)
            ...     await uow.commit()  # Explicitly commit
        """
        try:
            await self.session.flush()  # Write to DB (not committed yet)
            await self.session.commit()  # Commit transaction
            logger.debug("Transaction committed successfully")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Commit failed, rolling back: {e}")
            raise

    async def rollback(self) -> None:
        """Rollback the transaction.

        Purpose: Undo all changes made through repositories in this UoW.

        Behavior:
            - Rolls back all pending changes
            - ORM objects are expunged from session

        Example:
            >>> async with UnitOfWork(session) as uow:
            ...     await uow.draft_repo.update(...)
            ...     await uow.rollback()  # Undo changes
            ...     # Objects reverted to DB state
        """
        await self.session.rollback()
        logger.debug("Transaction rolled back")

    async def refresh(self, obj) -> None:
        """Refresh an ORM object from the database.

        Purpose: Reload an object's state from the current transaction.
        Useful after another operation modified the object.

        Args:
            obj: SQLAlchemy ORM instance to refresh.

        Example:
            >>> draft = await uow.draft_repo.get(draft_id)
            >>> # (another operation modifies draft)
            >>> await uow.refresh(draft)  # Reload from DB
        """
        await self.session.refresh(obj)

    @property
    def draft_repo(self):
        """Lazy property for DraftRepository instance.

        Returns:
            DraftRepository using this UoW's session.
        """
        if self._draft_repo is None:
            from .draft_repository import DraftRepository
            self._draft_repo = DraftRepository(self.session)
        return self._draft_repo

    @property
    def file_repo(self):
        """Lazy property for DraftFileRepository instance."""
        if self._file_repo is None:
            from .draft_file_repository import DraftFileRepository
            self._file_repo = DraftFileRepository(self.session)
        return self._file_repo

    @property
    def job_repo(self):
        """Lazy property for DraftGlueJobRepository instance."""
        if self._job_repo is None:
            from .draft_glue_job_repository import DraftGlueJobRepository
            self._job_repo = DraftGlueJobRepository(self.session)
        return self._job_repo

    @property
    def snapshot_repo(self):
        """Lazy property for SnapshotRepository instance."""
        if self._snapshot_repo is None:
            from .snapshot_repository import SnapshotRepository
            self._snapshot_repo = SnapshotRepository(self.session)
        return self._snapshot_repo

    @property
    def session_repo(self):
        """Lazy property for SessionRepository instance."""
        if self._session_repo is None:
            from .session_repository import SessionRepository
            self._session_repo = SessionRepository(self.session)
        return self._session_repo

    @property
    def user_repo(self):
        """Lazy property for UserRepository instance."""
        if self._user_repo is None:
            from .user_repository import UserRepository
            self._user_repo = UserRepository(self.session)
        return self._user_repo

    @property
    def validation_repo(self):
        """Lazy property for ValidationReportRepository instance."""
        if self._validation_repo is None:
            from .validation_report_repository import ValidationReportRepository
            self._validation_repo = ValidationReportRepository(self.session)
        return self._validation_repo

    @property
    def pr_repo(self):
        """Lazy property for PRMetadataRepository instance."""
        if self._pr_repo is None:
            from .pr_metadata_repository import PRMetadataRepository
            self._pr_repo = PRMetadataRepository(self.session)
        return self._pr_repo
