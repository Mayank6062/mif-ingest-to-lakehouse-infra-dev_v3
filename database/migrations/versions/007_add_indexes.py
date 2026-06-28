"""Migration 007: add performance indexes.

Revision ID: 007_add_indexes
Revises: 006_add_pr_metadata
Create Date: Database phase 2.3 implementation

Purpose: Create indexes to optimize query performance across all tables.

Indexes created:
  - users: (github_username) — for user lookups by username
  - sessions: (user_id, environment) — already UNIQUE from migration 002
  - sessions: (expires_at) — for session expiry cleanup queries
  - drafts: (session_id, created_at DESC) — for draft listing by session
  - drafts: (environment) — filter drafts by environment
  - draft_files: (draft_id, file_path) — already UNIQUE from migration 003
  - draft_glue_jobs: (draft_id, job_key) — already UNIQUE from migration 003
  - snapshots: (draft_id, created_at DESC) — time-series query optimization
  - validation_reports: (draft_id, validation_type, status) — query optimization
  - pr_metadata: (draft_id) — already UNIQUE from migration 006

Performance goals:
  - User session lookups: < 1ms
  - Draft listing: < 100ms
  - Snapshot retrieval: < 50ms
  - Validation history queries: < 100ms
  - Cleanup queries (expired sessions): < 500ms

Reference: Backend Module Architecture §2.8 (Models table spec - INDEX comment)
          Database layer optimization (Phase 2.3)
"""

from alembic import op
import sqlalchemy as sa

revision = "007_add_indexes"
down_revision = "006_add_pr_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create performance indexes."""

    # users table: lookup by GitHub username
    op.create_index(
        "ix_users_github_username",
        "users",
        ["github_username"],
        unique=False,
    )

    # sessions table: expiry cleanup queries
    op.create_index(
        "ix_sessions_expires_at",
        "sessions",
        ["expires_at"],
        unique=False,
    )

    # sessions table: current_draft_id for draft linking
    op.create_index(
        "ix_sessions_current_draft_id",
        "sessions",
        ["current_draft_id"],
        unique=False,
    )

    # drafts table: list drafts by session
    op.create_index(
        "ix_drafts_session_id_created_at",
        "drafts",
        ["session_id", sa.desc("created_at")],
        unique=False,
    )

    # drafts table: filter by environment
    op.create_index(
        "ix_drafts_environment",
        "drafts",
        ["environment"],
        unique=False,
    )

    # drafts table: filter by status
    op.create_index(
        "ix_drafts_status",
        "drafts",
        ["status"],
        unique=False,
    )

    # snapshots table: time-series queries (draft's snapshots ordered by time)
    op.create_index(
        "ix_snapshots_draft_id_created_at",
        "snapshots",
        ["draft_id", sa.desc("created_at")],
        unique=False,
    )

    # validation_reports table: query validation by type and status
    op.create_index(
        "ix_validation_reports_draft_id_type_status",
        "validation_reports",
        ["draft_id", "validation_type", "status"],
        unique=False,
    )

    # validation_reports table: latest validations for draft
    op.create_index(
        "ix_validation_reports_draft_id_created_at",
        "validation_reports",
        ["draft_id", sa.desc("created_at")],
        unique=False,
    )


def downgrade() -> None:
    """Drop all indexes."""

    op.drop_index("ix_validation_reports_draft_id_created_at", table_name="validation_reports")
    op.drop_index("ix_validation_reports_draft_id_type_status", table_name="validation_reports")
    op.drop_index("ix_snapshots_draft_id_created_at", table_name="snapshots")
    op.drop_index("ix_drafts_status", table_name="drafts")
    op.drop_index("ix_drafts_environment", table_name="drafts")
    op.drop_index("ix_drafts_session_id_created_at", table_name="drafts")
    op.drop_index("ix_sessions_current_draft_id", table_name="sessions")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_users_github_username", table_name="users")

