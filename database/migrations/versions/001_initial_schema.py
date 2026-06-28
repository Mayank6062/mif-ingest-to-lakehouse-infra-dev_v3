"""Migration 001: initial schema — users table.

Revision ID: 001
Revises: None (initial)
Create Date: Database phase 2.3 implementation

Purpose: Create the users table as the foundational entity.
All other tables reference users (directly or transitively).

Table: users
  - id (UUID, primary key)
  - github_id (int, unique GitHub user ID)
  - github_username (str, unique, NOT NULL)
  - email (str, nullable)
  - created_at (timestamp)
  - deleted_at (timestamp, nullable — soft delete indicator)

Reference: Backend Module Architecture §2.8 (Models table spec)
          Repository Master Structure §1.7 (Core Tables)
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create users table (initial schema).

    Attributes:
        id: UUID primary key (immutable identifier)
        github_id: GitHub numeric ID (for API lookups)
        github_username: GitHub username (unique, human-readable)
        email: Optional email address
        created_at: Record creation timestamp (UTC)
        deleted_at: Soft-delete timestamp (None = active, populated = deleted)

    Constraints:
        - Primary key: id
        - Unique: github_id, github_username
        - Not null: github_username, created_at
    """

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.String(36),
            nullable=False,
            comment="UUID primary key (immutable identifier)",
        ),
        sa.Column(
            "github_id",
            sa.Integer,
            unique=True,
            comment="GitHub numeric ID for API lookups",
        ),
        sa.Column(
            "github_username",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="GitHub username (unique, human-readable)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=True,
            comment="Optional email address",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            comment="Record creation timestamp (UTC)",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime,
            nullable=True,
            comment="Soft-delete timestamp (None = active, populated = deleted)",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("github_id", name="uq_users_github_id"),
        sa.UniqueConstraint("github_username", name="uq_users_github_username"),
    )


def downgrade() -> None:
    """Drop users table (reverse initial schema)."""

    op.drop_table("users")

