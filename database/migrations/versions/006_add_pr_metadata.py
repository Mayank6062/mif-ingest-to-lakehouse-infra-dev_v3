"""Migration 006: add pr_metadata table.

Revision ID: 006_add_pr_metadata
Revises: 005_add_validation_history
Create Date: Database phase 2.3 implementation

Purpose: Create pr_metadata table for tracking PR lifecycle and conflict detection.

Table: pr_metadata
  - id (UUID, primary key)
  - draft_id (UUID, unique foreign key to drafts.id) — 1:1 relationship
  - pr_number (int, GitHub PR number)
  - pr_url (str, full GitHub PR URL)
  - commit_sha (str, Git commit SHA)
  - branch_name (str, Git branch name)
  - pr_created_by (str, GitHub username)
  - pr_created_at (timestamp)
  - conflict_detected (bool, whether merge conflict found per FR-C-1)
  - conflict_resolved (bool, whether conflict was resolved)
  - created_at (timestamp, record creation)

Constraints:
  - Primary key: id
  - Unique: draft_id (1:1 relationship per FR-D-2)
  - Foreign key: draft_id → drafts.id (UNIQUE)
  - Not null: draft_id, pr_number, pr_url, commit_sha, branch_name, pr_created_by, pr_created_at

Purpose of pr_metadata:
  - Track PR creation for each draft
  - Conflict detection/resolution state (FR-C-1/FR-C-2)
  - Audit trail of PR activity
  - Linking back to PR for status updates

Reference: Backend Module Architecture §2.8 (Models table spec)
          §2.4.6 (ConflictService, PR lifecycle)
          doc/01_REPOSITORY_MASTER_STRUCTURE.md §1.7 (UNIQUE constraint on draft_id)
"""

from alembic import op
import sqlalchemy as sa

revision = "006_add_pr_metadata"
down_revision = "005_add_validation_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create pr_metadata table."""

    op.create_table(
        "pr_metadata",
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
            unique=True,
            comment="Foreign key to drafts.id (UNIQUE: 1:1 relationship per FR-D-2)",
        ),
        sa.Column(
            "pr_number",
            sa.Integer,
            nullable=False,
            comment="GitHub PR number",
        ),
        sa.Column(
            "pr_url",
            sa.String(500),
            nullable=False,
            comment="Full GitHub PR URL",
        ),
        sa.Column(
            "commit_sha",
            sa.String(40),
            nullable=False,
            comment="Git commit SHA of the PR",
        ),
        sa.Column(
            "branch_name",
            sa.String(255),
            nullable=False,
            comment="Branch name (draft/<draft_id> format)",
        ),
        sa.Column(
            "pr_created_by",
            sa.String(255),
            nullable=False,
            comment="GitHub username who created the PR",
        ),
        sa.Column(
            "pr_created_at",
            sa.DateTime,
            nullable=False,
            comment="Timestamp when PR was created",
        ),
        sa.Column(
            "conflict_detected",
            sa.Boolean,
            nullable=False,
            default=False,
            comment="Whether merge conflict detected during creation (FR-C-1)",
        ),
        sa.Column(
            "conflict_resolved",
            sa.Boolean,
            nullable=False,
            default=False,
            comment="Whether conflict was resolved (if detected per FR-C-2)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="Timestamp when this record was created",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pr_metadata"),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name="fk_pr_metadata_draft_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "draft_id",
            name="uq_pr_metadata_draft_id",
        ),
    )


def downgrade() -> None:
    """Drop pr_metadata table."""

    op.drop_table("pr_metadata")

