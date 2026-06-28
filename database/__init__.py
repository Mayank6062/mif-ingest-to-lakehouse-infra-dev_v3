"""Database connectivity package (leaf within backend).

Purpose: Provide SQLAlchemy ORM engine, session factory, and declarative base
for persistent storage of users, sessions, drafts, and validation history.

Responsibility: Manage database lifecycle, connection pooling, transactions,
and DDL reference. No business logic; repositories orchestrate data operations.

Consumers: Repositories, migrations, application startup.

Restrictions: This layer is a leaf — it must not import from services,
repositories, api, langgraph, or knowledge layers. Only backend/core imports allowed.

Reference documents: Architecture_Freeze.md, doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.7,
doc/02_BACKEND_MODULE_ARCHITECTURE.md §2.8 (Models)
"""

from .engine import create_engine, get_engine
from .session import AsyncSessionLocal, get_session, lifespan_session
from .base import Base

__all__ = [
    "create_engine",
    "get_engine",
    "AsyncSessionLocal",
    "get_session",
    "lifespan_session",
    "Base",
]

