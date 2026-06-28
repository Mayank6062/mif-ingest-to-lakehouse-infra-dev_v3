"""Migration 003: add drafts, draft_files, draft_glue_jobs tables.

Revision ID: 003_add_draft_tables
Revises: 002_add_session_tables
Create Date: Database phase 2.3 implementation

Purpose: Create core draft workspace tables.

Tables:
  1. drafts: Draft workspace state (OPEN/REVIEW/PR_CREATED/ABANDONED)
  2. draft_files: Files to be modified in PR (operation: ADD/MODIFY/DELETE)
  3. draft_glue_jobs: Glue job configurations to be created/modified

Constraints:
  - drafts.session_id → sessions.id (FK)
  - drafts.current_draft_id deferred from sessions (resolved in migration 002)
  - draft_files.draft_id → drafts.id (FK, UNIQUE per file_path)
  - draft_glue_jobs.draft_id → drafts.id (FK, UNIQUE per job_key)
  - Optimistic locking on drafts.version for concurrent updates

Reference: Backend Module Architecture §2.8 (Models table spec)
"""

from alembic import op
import sqlalchemy as sa

revision = "003_add_draft_tables"
down_revision = "002_add_session_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create drafts, draft_files, draft_glue_jobs tables."""

    # Create drafts table
    op.create_table(
        "drafts",
        sa.Column(
            "id",
            sa.String(36),
            nullable=False,
            comment="UUID primary key (draft identifier)",
        ),
        sa.Column(
            "session_id",
            sa.String(36),
            nullable=False,
            comment="Foreign key to sessions.id (session owner)",
        ),
        sa.Column(
            "environment",
            sa.String(20),
            nullable=False,
            comment="Environment (dev/staging/prod)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="Status: OPEN/REVIEW/PR_CREATED/ABANDONED (CQ-06 preserves Backend-v1 naming)",
        ),
        sa.Column(
            "pr_number",
            sa.Integer,
            nullable=True,
            comment="GitHub PR number if created; None initially",
        ),
        sa.Column(
            "pr_url",
            sa.String(500),
            nullable=True,
            comment="Full GitHub PR URL if created",
        ),
        sa.Column(
            "pr_branch",
            sa.String(255),
            nullable=True,
            comment="Git branch name (draft/<draft_id> pattern)",
        ),
        sa.Column(
            "is_frozen",
            sa.Boolean,
            nullable=False,
            default=False,
            comment="Frozen draft cannot be edited (FR-W-6/7)",
        ),
        sa.Column(
            "change_count",
            sa.Integer,
            nullable=False,
            default=0,
            comment="Number of file changes + job additions",
        ),
        sa.Column(
            "job_count",
            sa.Integer,
            nullable=False,
            default=0,
            comment="Number of Glue jobs in draft",
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=False,
            comment="GitHub username who created draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="Draft creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            comment="Last modification timestamp",
        ),
        sa.Column(
            "commit_sha",
            sa.String(40),
            nullable=True,
            comment="Git commit SHA if PR created",
        ),
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            default=0,
            comment="Optimistic lock counter for concurrent updates",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_drafts"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name="fk_drafts_session_id",
            ondelete="CASCADE",
        ),
    )

    # Create draft_files table (files to be modified in PR)
    op.create_table(
        "draft_files",
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
            comment="Foreign key to drafts.id",
        ),
        sa.Column(
            "file_path",
            sa.String(500),
            nullable=False,
            comment="Relative path in repository (e.g., saptcc/glue.tf)",
        ),
        sa.Column(
            "content",
            sa.Text,
            nullable=False,
            comment="File content (HCL/JSON/YAML)",
        ),
        sa.Column(
            "operation",
            sa.String(20),
            nullable=False,
            comment="Operation: ADD/MODIFY/DELETE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="When this change was added to draft",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_draft_files"),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name="fk_draft_files_draft_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "draft_id",
            "file_path",
            name="uq_draft_files_draft_path",
        ),
    )

    # Create draft_glue_jobs table (Glue job configurations in draft)
    op.create_table(
        "draft_glue_jobs",
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
            comment="Foreign key to drafts.id",
        ),
        sa.Column(
            "job_key",
            sa.String(255),
            nullable=False,
            comment="Unique identifier within draft (source-grain format)",
        ),
        sa.Column(
            "environment",
            sa.String(20),
            nullable=False,
            comment="Environment (dev/staging/prod)",
        ),
        sa.Column(
            "source_system",
            sa.String(50),
            nullable=False,
            comment="Source system (saptcc, saptce, etc.)",
        ),
        sa.Column(
            "schema_grain",
            sa.String(100),
            nullable=False,
            comment="Schema/topic grain identifier",
        ),
        sa.Column(
            "topic_name",
            sa.String(255),
            nullable=False,
            comment="Kafka topic name",
        ),
        sa.Column(
            "kafka_secret_name",
            sa.String(255),
            nullable=False,
            comment="AWS Secrets Manager key for Kafka credentials",
        ),
        sa.Column(
            "glue_job_name",
            sa.String(255),
            nullable=False,
            comment="AWS Glue job name",
        ),
        sa.Column(
            "iam_role",
            sa.String(500),
            nullable=False,
            comment="IAM role ARN for Glue job",
        ),
        sa.Column(
            "worker_type",
            sa.String(20),
            nullable=False,
            comment="Worker type: G.1X/G.2X/G.4X",
        ),
        sa.Column(
            "glue_version",
            sa.String(20),
            nullable=False,
            comment="Glue version (5.1 frozen for Phase-1)",
        ),
        sa.Column(
            "number_of_workers",
            sa.Integer,
            nullable=False,
            comment="Number of workers (CQ-04 unresolved: default 1 vs 4)",
        ),
        sa.Column(
            "scheduling_mode",
            sa.String(20),
            nullable=False,
            comment="Scheduling mode (CQ-05 unresolved: Manual vs daily 1AM)",
        ),
        sa.Column(
            "job_type",
            sa.String(20),
            nullable=False,
            comment="Job type (unified frozen for Phase-1)",
        ),
        sa.Column(
            "job_version",
            sa.String(20),
            nullable=False,
            comment="Job version (0.3.0 frozen for Phase-1)",
        ),
        sa.Column(
            "enterprise_function",
            sa.String(100),
            nullable=False,
            comment="Enterprise function (CQ-03 unresolved: SPEC vs CORP)",
        ),
        sa.Column(
            "subgroup",
            sa.String(50),
            nullable=False,
            comment="Subgroup: APAC/NA/LATAM (frozen)",
        ),
        sa.Column(
            "lh_database",
            sa.String(255),
            nullable=False,
            comment="Lakehouse database name (CQ-A1 unresolved: pattern)",
        ),
        sa.Column(
            "s3_warehouse",
            sa.String(500),
            nullable=False,
            comment="S3 warehouse path (CQ-A1 unresolved: pattern)",
        ),
        sa.Column(
            "s3_checkpoint",
            sa.String(500),
            nullable=False,
            comment="S3 checkpoint path for streaming state",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="When this job was added to draft",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_draft_glue_jobs"),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name="fk_draft_glue_jobs_draft_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "draft_id",
            "job_key",
            name="uq_draft_glue_jobs_draft_key",
        ),
    )


def downgrade() -> None:
    """Drop draft tables in reverse order."""

    op.drop_table("draft_glue_jobs")
    op.drop_table("draft_files")
    op.drop_table("drafts")

