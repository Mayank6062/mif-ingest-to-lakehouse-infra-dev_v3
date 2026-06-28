"""Migration 002: add sessions table.

Revision ID: 002_add_session_tables
Revises: 001_initial_schema
Create Date: Database phase 2.3 implementation

Purpose: Create the sessions table for user session management.

Table: sessions
  - id (UUID, primary key)
  - user_id (UUID, foreign key to users.id)
  - environment (str: dev, staging, prod)
  - current_draft_id (UUID, nullable foreign key to drafts.id)
  - github_token_ref (str, reference to secret store)
  - created_at, updated_at, expires_at (timestamps)
  - version (int, optimistic locking counter)

Constraints:
  - Foreign key: user_id → users.id
  - Unique: user_id + environment (one session per env per user)
  - Deferred: current_draft_id (added in migration 003)
  - Version: Optimistic locking for concurrent access

Reference: Backend Module Architecture §2.8 (Models table spec)
"""

from alembic import op
import sqlalchemy as sa

revision = "002_add_session_tables"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sessions table.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users (NOT NULL)
        environment: Environment enum (dev/staging/prod)
        current_draft_id: Optional reference to active draft (deferred FK)
        github_token_ref: Reference to token stored in secret manager
        created_at: Session creation timestamp
        updated_at: Last activity timestamp
        expires_at: Session expiration time
        version: Optimistic lock counter (starts at 0)

    Constraints:
        - Primary key: id
        - Foreign key: user_id → users.id (ON DELETE CASCADE)
        - Unique: (user_id, environment) — one active session per env
        - Not null: user_id, environment, created_at, updated_at, version
    """

    op.create_table(
        "sessions",
        sa.Column(
            "id",
            sa.String(36),
            nullable=False,
            comment="UUID primary key",
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            nullable=False,
            comment="Foreign key to users.id (session owner)",
        ),
        sa.Column(
            "environment",
            sa.String(20),
            nullable=False,
            comment="Environment (dev/staging/prod)",
        ),
        sa.Column(
            "current_draft_id",
            sa.String(36),
            nullable=True,
            comment="Current active draft ID (deferred FK to drafts.id)",
        ),
        sa.Column(
            "github_token_ref",
            sa.String(255),
            nullable=False,
            comment="Reference to GitHub token in secret store",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="Session creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            comment="Last activity timestamp",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime,
            nullable=True,
            comment="Session expiration time",
        ),
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            default=0,
            comment="Optimistic lock counter for concurrent updates",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sessions_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "environment",
            name="uq_sessions_user_environment",
        ),
    )


def downgrade() -> None:
    """Drop sessions table."""

    op.drop_table("sessions")

