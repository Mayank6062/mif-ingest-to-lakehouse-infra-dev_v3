"""Session ORM model — user session state and draft workspace reference.

Purpose: Represent user sessions with active draft workspace tracking.

Responsibility: Store session identity (user, environment, lifetime) and audit metadata.
Track current active draft and GitHub token reference for session lifecycle.
No business logic; pure data definition aligned with migrations 002 + 008.

Ownership: models layer (leaf)
Consumers: SessionRepository, SessionService, DraftService, API middleware

Reference: migrations 002 + 008, Backend Module Architecture §2.8
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .user import User
    from .draft import Draft


class Session(Base):
    """User session entity — session state and draft workspace owner.

    Attributes:
        id: UUID primary key (String(36), immutable session identifier).
        user_id: Foreign key to users.id (session owner, NOT NULL).
        environment: Target environment (dev/staging/prod), NOT NULL.
        current_draft_id: Optional FK to drafts.id (active draft workspace).
        github_token_ref: Reference to GitHub token in secret store, NOT NULL.
        created_at: UTC timestamp when session was created (not null).
        updated_at: UTC timestamp of last activity (not null).
        expires_at: Optional UTC timestamp when session expires.
        version: Optimistic lock counter for concurrent updates (default 0).

    Relationships:
        user: Many-to-one reverse relationship to User (owned by User.sessions).
        current_draft: Optional one-to-one reverse reference to Draft.
        drafts: One-to-many reverse relationship to all drafts (owned by Draft.session).

    Constraints:
        - Primary key: id
        - Foreign key: user_id → users.id (ON DELETE CASCADE)
        - Foreign key: current_draft_id → drafts.id (ON DELETE SET NULL, deferred)
        - Unique: (user_id, environment) — one active session per env
        - Not null: user_id, environment, created_at, updated_at, version

    Optimistic Locking: version column tracks concurrent update conflicts.
    Increment version on each UPDATE; caller must verify version matches before commit.

    Current Draft Lifecycle:
        - current_draft_id is nullable (session may have no active draft)
        - If draft is deleted, current_draft_id becomes NULL (SET NULL semantics)
        - Session remains valid after draft deletion
        - User can create new draft or restore from snapshots

    Reference: migrations 002_add_session_tables.py, 008_add_sessions_current_draft_fk.py
    """

    __tablename__ = "sessions"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (immutable session identifier)",
    )

    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Session owner (foreign key to users.id)",
    )

    current_draft_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Current active draft (nullable; SET NULL if draft deleted)",
    )

    # Session Attributes
    environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Target environment (dev/staging/prod)",
    )

    github_token_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Reference to GitHub token in secret store (not the token itself)",
    )

    # Audit Columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Session creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Last activity timestamp (UTC)",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Session expiration timestamp (None = no expiry)",
    )

    # Optimistic Locking
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Optimistic lock counter; increment on each update",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        lazy="select",
        comment="Session owner (many-to-one reverse from User.sessions)",
    )

    drafts: Mapped[list["Draft"]] = relationship(
        "Draft",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
        comment="All drafts created in this session",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "environment", name="uq_sessions_user_environment"),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Session id={self.id!r} user_id={self.user_id!r} environment={self.environment!r} version={self.version}>"
