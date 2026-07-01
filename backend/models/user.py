"""User ORM model — GitHub user identity store.

Purpose: Represent authenticated GitHub users and their session lifecycle.

Responsibility: Store user identity (GitHub ID, username, email) and audit metadata.
No business logic; pure data definition aligned with migration 001_initial_schema.

Ownership: models layer (leaf)
Consumers: SessionRepository, SessionService, AuthService, API middleware

Reference: migration 001_initial_schema.py, Backend Module Architecture §2.8
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .session import Session


class User(Base):
    """GitHub user entity — authentication identity and session owner.

    Attributes:
        id: UUID primary key (String(36), immutable identifier).
        github_id: GitHub numeric user ID (unique, for API lookups).
        github_username: GitHub username (unique, human-readable).
        email: Optional email address.
        created_at: UTC timestamp when record was created (not null).
        deleted_at: UTC timestamp for soft delete (null = active user).

    Relationships:
        sessions: One-to-many reverse relationship to Session (owned by Session.user).

    Constraints:
        - Primary key: id
        - Unique: github_id
        - Unique: github_username
        - Not null: github_username, created_at

    Soft Delete: deleted_at is None for active users; populated with UTC timestamp
    when soft-deleted. Queries should filter WHERE deleted_at IS NULL.

    Optimistic Locking: Not used for User (no version column).

    Reference: migration 001_initial_schema.py
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (immutable identifier)",
    )

    # GitHub Identity
    github_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        unique=True,
        nullable=True,
        comment="GitHub numeric ID for API lookups",
    )

    github_username: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="GitHub username (unique, human-readable)",
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional email address",
    )

    # Audit Columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Record creation timestamp (UTC)",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Soft-delete timestamp (None = active, populated = deleted)",
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        comment="Sessions owned by this user",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("github_id", name="uq_users_github_id"),
        UniqueConstraint("github_username", name="uq_users_github_username"),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<User id={self.id!r} github_username={self.github_username!r}>"
