"""Draft ORM model — user workspace for configuration changes.

Purpose: Represent draft workspace for incremental configuration changes (IaC files, Glue jobs).

Responsibility: Store draft state (OPEN/REVIEW/PR_CREATED/ABANDONED), file changes, job definitions,
and PR metadata. No business logic; pure data definition aligned with migration 003.

Ownership: models layer (leaf)
Consumers: DraftRepository, DraftService, LangGraph workflow, API middleware

Reference: migration 003_add_draft_tables.py, Backend Module Architecture §2.8
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .session import Session
    from .draft_file import DraftFile
    from .draft_glue_job import DraftGlueJob
    from .snapshot import Snapshot
    from .validation_report import ValidationReport
    from .pr_metadata import PRMetadata


class Draft(Base):
    """Draft workspace entity — configuration change workspace.

    Attributes:
        id: UUID primary key (String(36), immutable draft identifier).
        session_id: Foreign key to sessions.id (workspace owner, NOT NULL).
        environment: Target environment (dev/staging/prod), NOT NULL.
        status: Draft state (OPEN/REVIEW/PR_CREATED/ABANDONED), NOT NULL.
        pr_number: Optional GitHub PR number if PR created.
        pr_url: Optional full GitHub PR URL.
        pr_branch: Optional Git branch name (typically draft/<draft_id> pattern).
        is_frozen: Boolean flag; frozen drafts cannot be edited (default False).
        change_count: Counter for file changes + job additions (default 0).
        job_count: Counter for Glue jobs in draft (default 0).
        created_by: GitHub username of draft creator, NOT NULL.
        created_at: UTC timestamp when draft was created (not null).
        updated_at: UTC timestamp of last modification (not null).
        commit_sha: Optional Git commit SHA if PR created.
        version: Optimistic lock counter for concurrent updates (default 0).

    Relationships:
        session: Many-to-one reverse relationship to Session (owned by Session.drafts).
        draft_files: One-to-many relationship to DraftFile entries (files to be changed).
        draft_glue_jobs: One-to-many relationship to DraftGlueJob entries (job definitions).
        snapshots: One-to-many relationship to Snapshot (point-in-time captures).
        validation_reports: One-to-many relationship to ValidationReport (validation results).
        pr_metadata: One-to-one relationship to PRMetadata (PR lifecycle info).

    Constraints:
        - Primary key: id
        - Foreign key: session_id → sessions.id (ON DELETE CASCADE)
        - Not null: session_id, environment, status, created_by, created_at, updated_at, version

    Status Lifecycle:
        OPEN → REVIEW → PR_CREATED (or ABANDONED at any point)
        - OPEN: Initial state; user adding files/jobs
        - REVIEW: User completed changes; pending PR creation
        - PR_CREATED: GitHub PR created; awaiting merge
        - ABANDONED: Draft discarded; no further changes allowed

    Frozen Drafts:
        - is_frozen=True after PR creation or explicit freeze
        - Frozen drafts are immutable at application layer
        - Database does not enforce (application responsibility)

    Counters:
        - change_count: Incremented when files/jobs added; decremented on removal
        - job_count: Incremented when Glue job added; decremented on removal
        - Used by UI/services for progress tracking

    Optimistic Locking:
        - version column tracks concurrent update conflicts
        - Increment version on each UPDATE; caller must verify version matches before commit

    Reference: migration 003_add_draft_tables.py
    """

    __tablename__ = "drafts"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (draft identifier)",
    )

    # Foreign Key
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning session (foreign key to sessions.id)",
    )

    # Draft Identity
    environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Target environment (dev/staging/prod)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Draft status (OPEN/REVIEW/PR_CREATED/ABANDONED)",
    )

    # PR Fields
    pr_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="GitHub PR number if PR created",
    )

    pr_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Full GitHub PR URL if created",
    )

    pr_branch: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Git branch name for PR (typically draft/<draft_id>)",
    )

    # Draft State
    is_frozen: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Frozen draft cannot be edited (application-enforced)",
    )

    # Counters
    change_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="File changes + job additions count",
    )

    job_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Glue jobs in draft count",
    )

    # Metadata
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="GitHub username of draft creator",
    )

    # Audit Columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Draft creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Last modification timestamp (UTC)",
    )

    commit_sha: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        comment="Git commit SHA if PR created",
    )

    # Optimistic Locking
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Optimistic lock counter; increment on each update",
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="drafts",
        lazy="select",
        comment="Owning session (many-to-one reverse from Session.drafts)",
    )

    draft_files: Mapped[list["DraftFile"]] = relationship(
        "DraftFile",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="select",
        comment="Files to be modified in this draft",
    )

    draft_glue_jobs: Mapped[list["DraftGlueJob"]] = relationship(
        "DraftGlueJob",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="select",
        comment="Glue job definitions in this draft",
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(
        "Snapshot",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="select",
        comment="Point-in-time snapshots of draft state",
    )

    validation_reports: Mapped[list["ValidationReport"]] = relationship(
        "ValidationReport",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="select",
        comment="Validation results for this draft",
    )

    pr_metadata: Mapped[Optional["PRMetadata"]] = relationship(
        "PRMetadata",
        back_populates="draft",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
        comment="PR lifecycle information (1:1 with draft)",
    )

    # Constraints
    __table_args__ = ()

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Draft id={self.id!r} session_id={self.session_id!r} status={self.status!r} version={self.version}>"
