"""SQLAlchemy async engine factory.

Purpose: Initialize and manage SQLAlchemy async engine for PostgreSQL connection pooling.

Responsibility: Create engine with proper connection pool settings, echo configuration,
and lifecycle hooks. Singleton pattern with lazy initialization.

Consumers: Session factory, application startup, health checks.

Restrictions: No business logic; only infrastructure setup. No data access operations here.

Reference: SQLAlchemy 2.0+ async documentation; SQLALCHEMY_DATABASE_URL from config.Settings
"""

import logging
from typing import Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger("mif_copilot.database")

# Global engine instance (singleton)
_engine: Optional[AsyncEngine] = None


def create_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """Create and configure SQLAlchemy async engine for PostgreSQL.

    Purpose: Initialize async engine with proper connection pooling for scalable
    concurrent request handling. Pool settings tuned for web application workloads.

    Args:
        database_url: PostgreSQL async URL (postgresql+asyncpg://...).
        echo: Whether to log all SQL statements (use for debugging only).
        pool_size: Max number of connections to maintain in the pool (default 20).
        max_overflow: Max connections beyond pool_size (default 10).
        pool_recycle: Recycle connections after N seconds (default 3600 = 1 hour).
        pool_pre_ping: Test connections before using (prevents "connection lost" errors).

    Returns:
        AsyncEngine configured for async operations and connection pooling.

    Raises:
        ValueError: If database_url is missing or invalid.

    Example:
        >>> engine = create_engine(
        ...     "postgresql+asyncpg://user:pass@localhost/dbname",
        ...     echo=False,
        ...     pool_size=20
        ... )

    Reference: Backend Module Architecture §2.8 (Models & Database lifecycle)
    """

    if not database_url:
        raise ValueError("database_url is required and cannot be empty")

    # Use QueuePool for web applications (standard pooling behavior)
    # Use NullPool for serverless/edge (no persistent connections)
    poolclass = QueuePool

    engine = create_async_engine(
        database_url,
        echo=echo,
        poolclass=poolclass,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
        connect_args={
            "timeout": 10,  # Connection timeout (seconds)
            "command_timeout": 30,  # Query timeout (seconds)
            "server_settings": {
                # PostgreSQL session-level settings
                "application_name": "mif-copilot-backend",
                "timezone": "UTC",
            },
        },
    )

    # Optional: Add event listeners for debugging/monitoring
    @event.listens_for(engine.sync_engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Execute DDL on new connection to ensure timezone is UTC."""
        cursor = dbapi_conn.cursor()
        cursor.execute("SET timezone = 'UTC'")
        cursor.close()
        logger.debug("New DB connection established; timezone set to UTC")

    @event.listens_for(engine.sync_engine, "pool_connect")
    def receive_pool_connect(dbapi_conn, connection_record):
        """Log pool connection events for monitoring."""
        pass  # Logging can be verbose; enable only for debugging

    @event.listens_for(engine.sync_engine, "pool_checkout")
    def receive_pool_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log pool checkout for monitoring."""
        pass

    logger.info(f"SQLAlchemy async engine created (pool_size={pool_size}, echo={echo})")

    return engine


def get_engine() -> AsyncEngine:
    """Get or create the global engine instance (singleton).

    Purpose: Lazy-initialize the engine on first call. Ensures single engine
    instance shared across all requests/connections.

    Returns:
        Global AsyncEngine instance.

    Raises:
        RuntimeError: If called before engine is initialized.

    Example:
        >>> engine = get_engine()
        >>> async with engine.begin() as conn:
        ...     await conn.run_sync(metadata.create_all)

    Note: The engine must be initialized during application startup via
    backend/main.py or a dedicated initialization function before this is called.
    """

    global _engine

    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. "
            "Call create_engine() during application startup first."
        )

    return _engine


def set_engine(engine: AsyncEngine) -> None:
    """Set the global engine instance (internal use only).

    Purpose: Store the initialized engine for singleton access.
    Should only be called during application startup.

    Args:
        engine: AsyncEngine instance to store globally.

    Internal note: This is called by backend/main.py during FastAPI startup.
    """

    global _engine
    _engine = engine
    logger.info("Global database engine initialized")


async def dispose_engine() -> None:
    """Dispose of the global engine (cleanup on shutdown).

    Purpose: Release all connections in the pool and close the engine
    during application shutdown.

    Called by: FastAPI shutdown hook (backend/main.py).

    Example:
        >>> await dispose_engine()

    Note: After disposal, a new engine must be created before any new
    database operations can be performed.
    """

    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed and connections closed")

