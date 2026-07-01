"""PRMetadata ORM model — GitHub PR lifecycle tracking.

Purpose: Represent GitHub PR metadata linked to a draft (one-to-one relationship).

Responsibility: Store PR details, conflict detection/resolution state.
No business logic; pure data definition aligned with migration 006.

Ownership: models layer (leaf)
Consumers: PRRepository, DraftService, ConflictService, LangGraph workflow

Reference: migration 006_add_pr_metadata.py, Backend Module Architecture §2.8
"""

from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .draft import Draft


class PRMetadata(Base):
    """PR metadata entity — GitHub PR lifecycle information.

    Attributes:
        id: UUID primary key (String(36), immutable metadata identifier).
        draft_id: Foreign key to drafts.id (String(36), NOT NULL, UNIQUE).
            UNIQUE constraint enforces one-to-one relationship per FR-D-2.
            Each draft has at most one PR; each PR has exactly one draft.
        pr_number: GitHub PR number (Integer, NOT NULL).
            Unique identifier for PR within repository.
        pr_url: Full GitHub PR URL (String(500), NOT NULL).
            Example: https://github.com/org/repo/pull/123
        commit_sha: Git commit SHA of the PR (String(40), NOT NULL).
            Used for linking to commit history and CI results.
        branch_name: Git branch name (String(255), NOT NULL).
            Format: "draft/<draft_id>" (standard pattern).
        pr_created_by: GitHub username who created the PR (String(255), NOT NULL).
            For audit trail and notification.
        pr_created_at: Timestamp when PR was created (DateTime, NOT NULL, UTC).
            Separate from created_at (record creation timestamp).
        conflict_detected: Whether merge conflict detected during PR creation (Boolean, NOT NULL, default False).
            Per FR-C-1 (conflict detection requirement).
        conflict_resolved: Whether conflict was resolved (Boolean, NOT NULL, default False).
            Per FR-C-2 (conflict resolution requirement).
        created_at: Timestamp when this record was created (DateTime, NOT NULL, UTC).
            For audit trail of metadata record creation.

    Relationships:
        draft: One-to-one reverse relationship to Draft (owned by Draft.pr_metadata).

    Constraints:
        - Primary key: id
        - Foreign key: draft_id → drafts.id (ON DELETE CASCADE)
        - Unique constraint: draft_id (enforces one-to-one relationship)
        - Not null: all columns

    One-to-One Semantics:
        - UNIQUE constraint on draft_id ensures one-to-one relationship
        - Draft.pr_metadata uses uselist=False (optional, single instance)
        - PRMetadata.draft accesses parent with regular many-to-one semantics
        - When draft deleted, PRMetadata deleted via CASCADE

    Conflict Detection State Machine (FR-C-1 to FR-C-2):
        - OPEN PR (conflict_detected=False, conflict_resolved=False): No conflict
        - CONFLICT DETECTED (conflict_detected=True, conflict_resolved=False): Conflict found
        - CONFLICT RESOLVED (conflict_detected=True, conflict_resolved=True): Conflict resolved
        - States: F,F → T,F → T,T (unidirectional; never revert)

    Immutability:
        - PRMetadata entries immutable once created (conflict detection only updates state)
        - No field updates after creation per FR-C-2 (new record for each state change)
        - Deletion only via cascade when draft is deleted

    Audit Trail:
        - pr_created_at: When PR created in GitHub
        - created_at: When this record inserted in DB
        - Allows tracking of PR lifecycle from creation to resolution

    Reference: migration 006_add_pr_metadata.py, Backend Module Architecture §2.8
    Functional Requirement: FR-D-2 (one-to-one), FR-C-1 (conflict detection), FR-C-2 (conflict resolution)
    """

    __tablename__ = "pr_metadata"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (metadata identifier)",
    )

    # Foreign Key (Unique for One-to-One)
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="Owning draft (UNIQUE: one-to-one relationship per FR-D-2)",
    )

    # GitHub PR Details
    pr_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="GitHub PR number",
    )

    pr_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full GitHub PR URL",
    )

    commit_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="Git commit SHA of the PR",
    )

    branch_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Branch name (draft/<draft_id> format)",
    )

    pr_created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="GitHub username who created the PR",
    )

    pr_created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Timestamp when PR was created (UTC)",
    )

    # Conflict Detection/Resolution State (FR-C-1, FR-C-2)
    conflict_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether merge conflict detected during PR creation (FR-C-1)",
    )

    conflict_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether conflict was resolved if detected (FR-C-2)",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When this record was created (UTC)",
    )

    # Relationship
    draft: Mapped["Draft"] = relationship(
        "Draft",
        back_populates="pr_metadata",
        lazy="select",
        comment="Owning draft (one-to-one via UNIQUE draft_id)",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            name="uq_pr_metadata_draft_id",
        ),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<PRMetadata id={self.id!r} draft_id={self.draft_id!r} pr_number={self.pr_number!r}>"
