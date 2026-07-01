"""Snapshot ORM model — point-in-time draft state capture.

Purpose: Represent a point-in-time snapshot of draft state for versioning and rollback.

Responsibility: Store complete draft state (files, jobs, PR metadata) at a given timestamp.
No business logic; pure data definition aligned with migration 004.

Ownership: models layer (leaf)
Consumers: SnapshotRepository, DraftService, LangGraph workflow, rollback operations

Reference: migration 004_add_snapshots.py, Backend Module Architecture §2.8
"""

from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .draft import Draft


class Snapshot(Base):
    """Snapshot entity — point-in-time draft state capture.

    Attributes:
        id: UUID primary key (String(36), immutable snapshot identifier).
        draft_id: Foreign key to drafts.id (parent draft, NOT NULL).
        created_at: UTC timestamp when snapshot was created (NOT NULL).
        snapshot_content: Complete draft state as JSON (NOT NULL).
            Contains serialized representation of:
            - All DraftFile entries with content and operation
            - All DraftGlueJob entries with configuration
            - PR metadata if present
            - Draft status and metadata at capture time
        description: Optional human-readable label for snapshot (String(500), nullable).
            Example: "before adding job X", "pre-validation checkpoint"

    Relationships:
        draft: Many-to-one reverse relationship to Draft (owned by Draft.snapshots).

    Constraints:
        - Primary key: id
        - Foreign key: draft_id → drafts.id (ON DELETE CASCADE)
        - Not null: id, draft_id, created_at, snapshot_content

    Purpose:
        - User can revert draft to previous state (rollback)
        - Audit trail of draft evolution
        - Conflict detection uses snapshots for state comparison
        - Draft workspace history and change tracking

    Immutability:
        - Snapshot entries immutable once created
        - No updates permitted; only creation and deletion
        - Deletion only via cascade when draft is deleted

    JSON Schema (snapshot_content):
        {
            "draft_id": "...",
            "environment": "dev/staging/prod",
            "status": "OPEN/REVIEW/PR_CREATED/ABANDONED",
            "files": [{"id": "...", "file_path": "...", "operation": "ADD/MODIFY/DELETE", ...}],
            "jobs": [{"id": "...", "job_key": "...", "glue_job_name": "...", ...}],
            "pr_metadata": {"pr_number": 123, "pr_url": "...", ...} or null,
            "created_at": "2026-07-01T12:00:00Z",
            "created_by": "user@github"
        }

    Reference: migration 004_add_snapshots.py
    """

    __tablename__ = "snapshots"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (snapshot identifier)",
    )

    # Foreign Key
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning draft (foreign key to drafts.id)",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When this snapshot was created (UTC)",
    )

    # State Capture
    snapshot_content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Complete draft state (files, jobs, PR metadata, status)",
    )

    # Optional Label
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional user-provided label (e.g., 'before adding job X')",
    )

    # Relationship
    draft: Mapped["Draft"] = relationship(
        "Draft",
        back_populates="snapshots",
        lazy="select",
        comment="Owning draft (many-to-one reverse from Draft.snapshots)",
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<Snapshot id={self.id!r} draft_id={self.draft_id!r} created_at={self.created_at!r}>"
