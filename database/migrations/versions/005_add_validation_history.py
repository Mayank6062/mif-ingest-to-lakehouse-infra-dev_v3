"""Migration 005: add validation_reports table.

Revision ID: 005_add_validation_history
Revises: 004_add_snapshots
Create Date: Database phase 2.3 implementation

Purpose: Create validation_reports table for tracking validation results.

Table: validation_reports
  - id (UUID, primary key)
  - draft_id (UUID, foreign key to drafts.id)
  - validation_type (str: structural/semantic/compliance/etc.)
  - status (str: PASS/FAIL/WARNING)
  - rule_id (str, optional rule identifier for traceability)
  - message (str, user-safe message)
  - internal_context (JSON, optional technical details not sent to user)
  - created_at (timestamp)

Constraints:
  - Foreign key: draft_id → drafts.id
  - Not null: draft_id, validation_type, status, message

Purpose of validation_reports:
  - Audit trail of validation attempts
  - User feedback on validation results
  - Rules engine traceability
  - PR creation blockers
  - Compliance history

Reference: Backend Module Architecture §2.8 (Models table spec)
          §2.4.8 (ValidationService)
"""

from alembic import op
import sqlalchemy as sa

revision = "005_add_validation_history"
down_revision = "004_add_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create validation_reports table."""

    op.create_table(
        "validation_reports",
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
            comment="Foreign key to drafts.id (validation belongs to draft)",
        ),
        sa.Column(
            "validation_type",
            sa.String(100),
            nullable=False,
            comment="Type of validation (structural/semantic/compliance/etc.)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="Result status: PASS/FAIL/WARNING",
        ),
        sa.Column(
            "rule_id",
            sa.String(255),
            nullable=True,
            comment="Internal rule identifier for traceability (not user-facing)",
        ),
        sa.Column(
            "message",
            sa.Text,
            nullable=False,
            comment="User-safe message describing result (never exposes internals)",
        ),
        sa.Column(
            "internal_context",
            sa.JSON,
            nullable=True,
            comment="Technical context for logging/debugging (not sent to user)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="When this validation was recorded",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_validation_reports"),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name="fk_validation_reports_draft_id",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop validation_reports table."""

    op.drop_table("validation_reports")

