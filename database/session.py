"""AsyncSession factory for request-scoped database sessions.

Purpose: Provide scoped async sessions for dependency injection in FastAPI routes.
Each HTTP request gets an isolated session instance that commits/rolls back independently.

Responsibility: Create AsyncSession instances bound to the global engine,
manage session lifecycle, and provide context manager patterns for transactions.

Consumers: FastAPI dependency injection (Depends), repositories, services.

Restrictions: No business logic; only session management infrastructure.

Reference: SQLAlchemy 2.0+ async documentation; AsyncSession patterns
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .engine import get_engine

logger = logging.getLogger("mif_copilot.database")

# Global session factory (lazy-initialized)
AsyncSessionLocal: Optional[async_sessionmaker] = None


def init_session_factory(engine_instance) -> async_sessionmaker:
    """Initialize the global async session factory.

    Purpose: Create async_sessionmaker bound to the global engine.
    Called once during application startup.

    Args:
        engine_instance: SQLAlchemy AsyncEngine instance.

    Returns:
        async_sessionmaker configured for the engine.

    Called by: backend/main.py during FastAPI startup.

    Example:
        >>> from database import init_session_factory, get_engine
        >>> engine = get_engine()
        >>> AsyncSessionLocal = init_session_factory(engine)
    """

    global AsyncSessionLocal

    AsyncSessionLocal = async_sessionmaker(
        engine_instance,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=False,  # Manual flush control
        autocommit=False,  # Explicit transaction control
    )

    logger.info("AsyncSession factory initialized")
    return AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting a request-scoped async session.

    Purpose: Provide an AsyncSession instance per HTTP request.
    Used as FastAPI Depends() for automatic injection into route handlers.

    Yields:
        AsyncSession: Scoped session for the request duration.

    Lifecycle:
        - Created at request start
        - Available to route handler
        - Committed or rolled back at request end
        - Context manager ensures cleanup

    Raises:
        RuntimeError: If session factory not initialized.

    Example (in FastAPI route):
        >>> from fastapi import Depends
        >>> from database import get_session
        >>>
        >>> @app.get("/drafts/{id}")
        >>> async def get_draft(
        ...     draft_id: str,
        ...     session: AsyncSession = Depends(get_session)
        ... ):
        ...     result = await session.execute(select(Draft).where(...))
        ...     return result.scalars().first()

    Note: The session is automatically committed if the route succeeds,
    rolled back if an exception is raised.
    """

    if AsyncSessionLocal is None:
        raise RuntimeError(
            "AsyncSession factory not initialized. "
            "Call init_session_factory() during startup first."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit on success
            logger.debug(f"Session {id(session)} committed")
        except Exception as e:
            await session.rollback()  # Rollback on error
            logger.error(f"Session {id(session)} rolled back due to {type(e).__name__}")
            raise
        finally:
            await session.close()  # Always close
            logger.debug(f"Session {id(session)} closed")


@asynccontextmanager
async def lifespan_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for manual session lifecycle control.

    Purpose: For scenarios where you want explicit transaction control
    outside of FastAPI's Depends() pattern (e.g., background tasks, scripts).

    Yields:
        AsyncSession: Scoped session for manual use.

    Lifecycle:
        - Created on context entry
        - Must be explicitly committed or rolled back
        - Closed on context exit

    Example (background task):
        >>> async def process_draft(draft_id: str):
        ...     async with lifespan_session() as session:
        ...         draft = await session.get(Draft, draft_id)
        ...         draft.status = "PROCESSING"
        ...         await session.commit()

    Example (CLI script):
        >>> async def backfill_data():
        ...     async with lifespan_session() as session:
        ...         # Manual queries/updates
        ...         result = await session.execute(...)
        ...         await session.commit()

    Raises:
        RuntimeError: If session factory not initialized.
    """

    if AsyncSessionLocal is None:
        raise RuntimeError(
            "AsyncSession factory not initialized. "
            "Call init_session_factory() during startup first."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            logger.debug(f"Lifespan session {id(session)} closed")


async def get_session_for_test() -> AsyncSession:
    """Create a standalone session for testing (no auto-commit/rollback).

    Purpose: For unit/integration tests that need explicit session control
    and don't want automatic commit on success.

    Returns:
        AsyncSession: Standalone session instance (caller must close).

    Raises:
        RuntimeError: If session factory not initialized.

    Note: Tests using this must explicitly await session.close() or use
    async context manager to prevent connection leaks.

    Example:
        >>> session = await get_session_for_test()
        >>> try:
        ...     user = User(github_username="test")
        ...     session.add(user)
        ...     await session.flush()
        ...     assert user.id is not None
        ... finally:
        ...     await session.close()
    """

    if AsyncSessionLocal is None:
        raise RuntimeError(
            "AsyncSession factory not initialized. "
            "Call init_session_factory() during startup first."
        )

    return AsyncSessionLocal()


async def reset_session_factory() -> None:
    """Reset the global session factory (mainly for testing).

    Purpose: Clear the session factory between test runs to ensure
    test isolation and prevent session pool leaks.

    Internal use only — tests and startup/shutdown hooks.

    Example:
        >>> # In test teardown
        >>> await reset_session_factory()
        >>> AsyncSessionLocal = None
    """

    global AsyncSessionLocal
    AsyncSessionLocal = None
    logger.info("AsyncSession factory reset")

