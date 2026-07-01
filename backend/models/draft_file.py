"""DraftFile ORM model — file changes within a draft workspace.

Purpose: Represent a single file change (HCL/JSON/YAML) within a draft.

Responsibility: Store file path, content, and operation type (ADD/MODIFY/DELETE).
No business logic; pure data definition aligned with migration 003.

Ownership: models layer (leaf)
Consumers: DraftRepository, DraftService, LangGraph workflow, API middleware

Reference: migration 003_add_draft_tables.py, Backend Module Architecture §2.8
"""

from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .draft import Draft


class DraftFile(Base):
    """Draft file entity — file change entry within a draft workspace.

    Attributes:
        id: UUID primary key (String(36), immutable file change identifier).
        draft_id: Foreign key to drafts.id (parent draft, NOT NULL).
        file_path: Relative repository path (e.g., saptcc/glue.tf), NOT NULL.
        content: File content as text (HCL/JSON/YAML), NOT NULL.
        operation: Change operation type (ADD/MODIFY/DELETE), NOT NULL.
        created_at: UTC timestamp when file was added to draft (not null).

    Relationships:
        draft: Many-to-one reverse relationship to Draft (owned by Draft.draft_files).

    Constraints:
        - Primary key: id
        - Foreign key: draft_id → drafts.id (ON DELETE CASCADE)
        - Unique: (draft_id, file_path) — one change per file per draft
        - Not null: draft_id, file_path, content, operation, created_at

    Operation Types:
        ADD: New file to be created in repository.
        MODIFY: Existing file to be modified.
        DELETE: Existing file to be removed.

    Unique Constraint Semantics:
        The (draft_id, file_path) unique constraint ensures one entry per file path
        per draft. Re-uploading the same file path replaces the previous entry
        (handled by application layer, not database).

    Immutability:
        DraftFile entries are immutable once created. Updates are done via replacement
        (update operation, not column modification). This aligns with event-sourcing
        principles where changes are recorded, not overwritten.

    Reference: migration 003_add_draft_tables.py
    """

    __tablename__ = "draft_files"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (file change identifier)",
    )

    # Foreign Key
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent draft (foreign key to drafts.id)",
    )

    # File Identity
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Relative repository path (e.g., saptcc/glue.tf)",
    )

    # File Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="File content (HCL/JSON/YAML)",
    )

    # Change Metadata
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Change operation: ADD/MODIFY/DELETE",
    )

    # Audit Columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Timestamp when file was added to draft (UTC)",
    )

    # Relationships
    draft: Mapped["Draft"] = relationship(
        "Draft",
        back_populates="draft_files",
        lazy="select",
        comment="Parent draft (many-to-one reverse from Draft.draft_files)",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("draft_id", "file_path", name="uq_draft_files_draft_path"),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<DraftFile id={self.id!r} draft_id={self.draft_id!r} file_path={self.file_path!r} operation={self.operation!r}>"
