"""Migration 004: add snapshots table.

Revision ID: 004_add_snapshots
Revises: 003_add_draft_tables
Create Date: Database phase 2.3 implementation

Purpose: Create snapshots table for draft state versioning/rollback.

Table: snapshots
  - id (UUID, primary key)
  - draft_id (UUID, foreign key to drafts.id)
  - created_at (timestamp)
  - snapshot_content (JSON, complete draft state at this point)
  - description (str, optional human-readable label)

Constraints:
  - Foreign key: draft_id → drafts.id
  - Index: (draft_id, created_at) for time-series queries

Purpose of snapshots:
  - User can revert draft to previous state
  - Audit trail of draft evolution
  - Conflict detection uses snapshots
  - Draft workspace history

Reference: Backend Module Architecture §2.8 (Models table spec)
          MIF_Implementation_Bible.md (snapshot operations)
"""

from alembic import op
import sqlalchemy as sa

revision = "004_add_snapshots"
down_revision = "003_add_draft_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create snapshots table."""

    op.create_table(
        "snapshots",
        sa.Column(
            "id",
            sa.String(36),
            nullable=False,
            comment="UUID primary key",
        ),
        sa.Column(
            "draft_id",
            sa.String(36),
            nullable=False,
            comment="Foreign key to drafts.id (snapshot belongs to draft)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="Timestamp when snapshot was created",
        ),
        sa.Column(
            "snapshot_content",
            sa.JSON,
            nullable=False,
            comment="Complete draft state at this point (files, jobs, PR metadata)",
        ),
        sa.Column(
            "description",
            sa.String(500),
            nullable=True,
            comment="Optional user-provided label (e.g., 'before adding job X')",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_snapshots"),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name="fk_snapshots_draft_id",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop snapshots table."""

    op.drop_table("snapshots")

