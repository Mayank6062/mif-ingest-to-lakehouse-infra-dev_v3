"""SQLAlchemy declarative base for ORM model definitions.

Purpose: Provide the declarative registry that all ORM models inherit from.

Responsibility: Define Base class that all models extend. Contains shared
metadata tracking and table registry for migrations and DDL generation.

Consumers: All backend/models/* files, Alembic migrations.

Restrictions: This module is infrastructure only; no business logic.

Reference: SQLAlchemy 2.0 documentation (declarative_base pattern)
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models.

    Purpose: Registry for all ORM entity definitions (User, Session, Draft, etc.).
    All model classes inherit from this base, which tracks them for:
      - Metadata (table definitions, columns, constraints)
      - Migration generation (Alembic uses metadata)
      - DDL creation (create_all/drop_all operations)

    Design pattern: SQLAlchemy 2.0 modern approach (replaces declarative_base() factory).

    Attributes:
        metadata: SQLAlchemy MetaData instance tracking all registered tables.

    Example (model definition):
        >>> from database import Base
        >>> from sqlalchemy import Column, String, DateTime
        >>> from datetime import datetime
        >>>
        >>> class User(Base):
        ...     __tablename__ = "users"
        ...
        ...     id = Column(String(36), primary_key=True)
        ...     github_username = Column(String(255), unique=True, nullable=False)
        ...     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    Alembic Integration:
        Alembic's env.py loads Base.metadata to generate migrations:

        >>> from database import Base
        >>> target_metadata = Base.metadata

    DDL Generation (for documentation/scripts):
        >>> from sqlalchemy import create_engine
        >>> from database import Base
        >>>
        >>> engine = create_engine("sqlite:///:memory:")
        >>> Base.metadata.create_all(engine)  # Sync example
        >>>
        >>> # Async example (migrations):
        >>> await engine.run_sync(Base.metadata.create_all)
    """

    pass

